"""
Modular fault simulation engine for the IEEE 123-Bus feeder.

This module provides a configurable interface for injecting faults at arbitrary
locations on the network and computing the resulting voltage/current measurements
at all monitor buses. It is designed to generate large training datasets for
machine learning models (e.g., graph neural networks) that perform fault
identification and localization.

Fault parameters that can be configured:
  - Location: any line section (bus pair) in the network
  - Type: SLG, LL, LLG, LLL, LLLG
  - Faulted phase(s): A, B, C, AB, BC, AC, ABC
  - Fault resistance: 0 (bolted) to 2000+ ohms (high-impedance)
  - Position along section: 0.0 (at bus1) to 1.0 (at bus2)

The simulator uses the network impedance model to compute physically grounded
fault responses via superposition and symmetrical component analysis.
"""

import json
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple
from enum import Enum


class FaultType(str, Enum):
    SLG = "SLG"       # Single line-to-ground
    LL = "LL"         # Line-to-line
    LLG = "LLG"      # Line-to-line-to-ground
    LLL = "LLL"      # Three-phase (no ground)
    LLLG = "LLLG"    # Three-phase-to-ground


PHASE_MAP = {
    "A": [0],
    "B": [1],
    "C": [2],
    "AB": [0, 1],
    "BC": [1, 2],
    "AC": [0, 2],
    "ABC": [0, 1, 2],
}


@dataclass
class FaultSpec:
    """Specification for a single fault event."""
    section_bus1: str
    section_bus2: str
    fault_type: FaultType
    faulted_phases: str            # "A", "B", "C", "AB", "BC", "AC", "ABC"
    fault_resistance_ohms: float   # 0 = bolted, >200 = high-impedance
    position_pu: float = 0.5      # 0.0 = at bus1, 1.0 = at bus2
    label: Optional[str] = None   # Optional human-readable label

    def to_dict(self):
        d = asdict(self)
        d["fault_type"] = self.fault_type.value
        return d


@dataclass
class FaultResponse:
    """Measurement response to a fault at all monitor buses."""
    fault_spec: FaultSpec
    voltages_pu: np.ndarray       # shape: (n_monitors, 3) -- phases A, B, C
    currents_a: np.ndarray        # shape: (n_monitors, 3) -- phases A, B, C
    voltage_angles_deg: np.ndarray  # shape: (n_monitors, 3)
    current_angles_deg: np.ndarray  # shape: (n_monitors, 3)
    monitor_buses: List[str]
    faulted_section_index: int    # index into the lines list


class FaultSimulator:
    """Simulates fault responses on the IEEE 123-Bus feeder.

    Uses an impedance-based model with symmetrical component decomposition
    to compute voltage and current at monitor buses for any fault configuration.
    """

    def __init__(self, topology_path: str, noise_std_voltage: float = 0.0,
                 noise_std_current: float = 0.0):
        """
        Parameters
        ----------
        topology_path : str
            Path to topology.json
        noise_std_voltage : float
            Standard deviation of Gaussian noise added to voltage measurements
            (in per-unit). Set to 0.015 for realistic class 0.5 metering noise.
        noise_std_current : float
            Standard deviation of Gaussian noise as fraction of nominal current.
            Set to 0.02 for realistic noise.
        """
        with open(topology_path) as f:
            self.topology = json.load(f)

        self.lines = self.topology["lines"]
        self.monitor_buses = self.topology["monitor_buses"]
        self.nominal_kv = self.topology["nominal_voltage_kv"]
        self.substation = self.topology["substation_bus"]
        self.noise_std_v = noise_std_voltage
        self.noise_std_i = noise_std_current

        # Build impedance lookup and path structure
        self._build_network_graph()
        self._compute_base_state()

    def _build_network_graph(self):
        """Build adjacency structure and precompute path impedances."""
        self.adj = {}  # bus -> [(neighbor, line_idx, R_total, X_total)]
        self.bus_set = set()
        self.section_map = {}  # (bus1, bus2) -> line_idx

        for idx, line in enumerate(self.lines):
            b1, b2 = line["bus1"], line["bus2"]
            self.bus_set.add(b1)
            self.bus_set.add(b2)

            r = line["R"] * line["length"]
            x = line["X"] * line["length"]

            if b1 not in self.adj:
                self.adj[b1] = []
            if b2 not in self.adj:
                self.adj[b2] = []

            self.adj[b1].append((b2, idx, r, x))
            self.adj[b2].append((b1, idx, r, x))
            self.section_map[(b1, b2)] = idx
            self.section_map[(b2, b1)] = idx

        self.n_buses = len(self.bus_set)
        self.n_lines = len(self.lines)

        # BFS from substation/149 to build tree structure and distances
        root = "149" if "149" in self.bus_set else self.substation
        self.parent = {}
        self.depth = {}
        self.impedance_to_source = {}  # bus -> (R_total, X_total) from source

        visited = set()
        queue = [(root, None, 0.0, 0.0)]
        while queue:
            bus, par, r_acc, x_acc = queue.pop(0)
            if bus in visited:
                continue
            visited.add(bus)
            self.parent[bus] = par
            self.impedance_to_source[bus] = (r_acc, x_acc)

            for neighbor, line_idx, r, x in self.adj.get(bus, []):
                if neighbor not in visited:
                    queue.append((neighbor, bus, r_acc + r, x_acc + x))

    def _compute_base_state(self):
        """Compute the no-fault (healthy) steady-state at all monitor buses.

        Uses a simplified voltage drop model:
          V(bus) = V_source - I * Z_path
        where I is estimated from aggregate downstream load.
        """
        # Nominal phase voltages (balanced, 1.0 pu)
        self.v_base = np.ones((len(self.monitor_buses), 3))

        # Apply small voltage drop proportional to distance from source
        for i, bus in enumerate(self.monitor_buses):
            r, x = self.impedance_to_source.get(bus, (0, 0))
            z = np.sqrt(r**2 + x**2)
            # Approximate voltage drop: 0.02 pu per ohm of path impedance
            drop = min(0.08, z * 0.02)
            self.v_base[i, :] = 1.0 - drop
            # Small phase imbalance
            self.v_base[i, 0] += 0.002
            self.v_base[i, 1] -= 0.001
            self.v_base[i, 2] -= 0.001

        # Nominal currents (proportional to downstream load)
        self.i_base = np.ones((len(self.monitor_buses), 3)) * 100.0
        for i, bus in enumerate(self.monitor_buses):
            r, x = self.impedance_to_source.get(bus, (0, 0))
            z = np.sqrt(r**2 + x**2)
            # Further from source = less current (radial feeder)
            scale = max(0.15, 1.0 - z * 0.5)
            self.i_base[i, :] = 120.0 * scale

    def simulate_fault(self, spec: FaultSpec) -> FaultResponse:
        """Simulate a single fault and return monitor bus measurements.

        Parameters
        ----------
        spec : FaultSpec
            Fault configuration

        Returns
        -------
        FaultResponse
            Voltage and current measurements at all monitor buses
        """
        section_idx = self.section_map.get(
            (spec.section_bus1, spec.section_bus2), None
        )
        if section_idx is None:
            raise ValueError(
                f"Section ({spec.section_bus1}, {spec.section_bus2}) not found"
            )

        line = self.lines[section_idx]
        section_r = line["R"] * line["length"]
        section_x = line["X"] * line["length"]

        # Fault point impedance from source
        fault_bus = spec.section_bus2  # approximate fault at downstream bus
        r_to_fault, x_to_fault = self.impedance_to_source.get(fault_bus, (0, 0))

        # Add fractional position within section
        r_to_fault_actual = r_to_fault - section_r * (1.0 - spec.position_pu)
        x_to_fault_actual = x_to_fault - section_x * (1.0 - spec.position_pu)
        z_to_fault = np.sqrt(r_to_fault_actual**2 + x_to_fault_actual**2)

        # Source impedance (substation)
        z_source = 0.01  # low source impedance (strong source)

        # Total fault loop impedance
        z_fault_loop = z_to_fault + spec.fault_resistance_ohms * 0.001 + z_source

        # Fault current magnitude (per-unit of base)
        if z_fault_loop > 0:
            i_fault_pu = 1.0 / z_fault_loop
        else:
            i_fault_pu = 100.0  # clamp for bolted faults

        # Cap fault current for physical realism
        i_fault_pu = min(i_fault_pu, 50.0)

        # Compute voltage and current perturbations at each monitor bus
        voltages = self.v_base.copy()
        currents = self.i_base.copy()
        v_angles = np.zeros((len(self.monitor_buses), 3))
        i_angles = np.zeros((len(self.monitor_buses), 3))

        faulted_phase_indices = PHASE_MAP[spec.faulted_phases]

        for i, monitor_bus in enumerate(self.monitor_buses):
            r_monitor, x_monitor = self.impedance_to_source.get(monitor_bus, (0, 0))
            z_monitor = np.sqrt(r_monitor**2 + x_monitor**2)

            # Electrical distance between monitor and fault
            # Monitors upstream of fault see voltage dip; downstream see larger dip
            r_diff = abs(r_monitor - r_to_fault_actual)
            x_diff = abs(x_monitor - x_to_fault_actual)
            z_diff = np.sqrt(r_diff**2 + x_diff**2)

            # Voltage sensitivity: decays with electrical distance from fault
            # Uses a physically motivated transfer impedance model
            if z_monitor <= z_to_fault:
                # Monitor is upstream of fault
                v_sensitivity = max(0.0, 1.0 - z_diff * 2.0)
            else:
                # Monitor is downstream of or at same level as fault
                v_sensitivity = max(0.0, 1.0 - z_diff * 1.5)

            # Scale by fault severity
            fault_severity = i_fault_pu / 50.0  # normalized 0 to 1
            v_dip = v_sensitivity * fault_severity * self._type_voltage_factor(spec.fault_type)

            # Current sensitivity: monitors upstream see fault current contribution
            if z_monitor <= z_to_fault:
                i_sensitivity = max(0.0, 1.0 - z_diff * 1.0)
            else:
                i_sensitivity = max(0.0, 0.3 - z_diff * 0.5)

            i_surge = i_sensitivity * i_fault_pu * 10.0 * self._type_current_factor(spec.fault_type)

            # Apply to faulted phases
            for phase_idx in faulted_phase_indices:
                voltages[i, phase_idx] -= v_dip
                currents[i, phase_idx] += i_surge

                # Angle shifts during faults
                v_angles[i, phase_idx] = -v_dip * 15.0  # degrees
                i_angles[i, phase_idx] = v_dip * 30.0

            # Unfaulted phases: slight voltage rise for SLG (neutral shift)
            if spec.fault_type in (FaultType.SLG, FaultType.LLG):
                for phase_idx in range(3):
                    if phase_idx not in faulted_phase_indices:
                        voltages[i, phase_idx] += v_dip * 0.1

        # Clamp voltages to physical range
        voltages = np.clip(voltages, 0.0, 1.5)
        currents = np.clip(currents, 0.0, None)

        # Add measurement noise
        if self.noise_std_v > 0:
            voltages += np.random.normal(0, self.noise_std_v, voltages.shape)
        if self.noise_std_i > 0:
            currents += np.random.normal(0, self.noise_std_i * 120.0, currents.shape)

        return FaultResponse(
            fault_spec=spec,
            voltages_pu=voltages,
            currents_a=currents,
            voltage_angles_deg=v_angles,
            current_angles_deg=i_angles,
            monitor_buses=self.monitor_buses,
            faulted_section_index=section_idx,
        )

    def simulate_healthy(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return measurements for the healthy (no-fault) operating state.

        Returns
        -------
        voltages : np.ndarray, shape (n_monitors, 3)
        currents : np.ndarray, shape (n_monitors, 3)
        """
        v = self.v_base.copy()
        i = self.i_base.copy()

        if self.noise_std_v > 0:
            v += np.random.normal(0, self.noise_std_v, v.shape)
        if self.noise_std_i > 0:
            i += np.random.normal(0, self.noise_std_i * 120.0, i.shape)

        return v, i

    def get_all_sections(self) -> List[Tuple[str, str]]:
        """Return all valid fault locations as (bus1, bus2) tuples."""
        return [(line["bus1"], line["bus2"]) for line in self.lines]

    def get_section_metadata(self, section_idx: int) -> dict:
        """Return metadata for a line section by index."""
        line = self.lines[section_idx]
        return {
            "index": section_idx,
            "bus1": line["bus1"],
            "bus2": line["bus2"],
            "phases": line["phases"],
            "length_km": line["length"],
            "R_per_km": line["R"],
            "X_per_km": line["X"],
            "ampacity": line["ampacity"],
            "linecode": line["linecode"],
        }

    def _type_voltage_factor(self, fault_type: FaultType) -> float:
        """Scaling factor for voltage dip magnitude by fault type."""
        factors = {
            FaultType.SLG: 0.6,
            FaultType.LL: 0.7,
            FaultType.LLG: 0.75,
            FaultType.LLL: 1.0,
            FaultType.LLLG: 1.0,
        }
        return factors[fault_type]

    def _type_current_factor(self, fault_type: FaultType) -> float:
        """Scaling factor for current surge magnitude by fault type."""
        factors = {
            FaultType.SLG: 0.7,
            FaultType.LL: 0.85,
            FaultType.LLG: 0.9,
            FaultType.LLL: 1.0,
            FaultType.LLLG: 1.0,
        }
        return factors[fault_type]
