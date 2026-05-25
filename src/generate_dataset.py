"""
Training dataset generator for ML-based fault identification and localization.

This script generates labeled datasets by simulating faults across the IEEE 123-Bus
feeder using the FaultSimulator. The output is suitable for training graph neural
networks or other ML architectures.

Usage:
    python src/generate_dataset.py --n_samples 5000 --output data/train.npz
    python src/generate_dataset.py --n_samples 1000 --output data/test.npz --seed 99

Configuration is controlled via command-line arguments or by modifying the
FaultSamplingConfig dataclass below.
"""

import argparse
import json
import os
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fault_simulator import FaultSimulator, FaultSpec, FaultType, PHASE_MAP


@dataclass
class FaultSamplingConfig:
    """Configuration for random fault sampling.

    Each field defines the distribution from which fault parameters are drawn.
    Modify these to control the composition of your training set.
    """
    # Fault types and their sampling probabilities
    fault_type_weights: dict = None

    # Fault resistance range (ohms)
    resistance_min: float = 0.0
    resistance_max: float = 2000.0

    # Whether to include high-impedance faults (Rf > 200 ohms)
    include_hif: bool = True
    hif_fraction: float = 0.15  # fraction of samples that are HIF

    # Whether to include healthy (no-fault) samples
    include_healthy: bool = True
    healthy_fraction: float = 0.10  # fraction of samples with no fault

    # Measurement noise
    noise_std_voltage: float = 0.015  # 1.5% of nominal
    noise_std_current: float = 0.02   # 2% of nominal

    # Position along section: uniform [0, 1] or fixed
    position_mode: str = "uniform"  # "uniform" or "fixed"
    fixed_position: float = 0.5

    # Phase selection mode
    phase_mode: str = "random"  # "random" or "realistic"

    def __post_init__(self):
        if self.fault_type_weights is None:
            self.fault_type_weights = {
                "SLG": 0.45,   # most common in distribution
                "LL": 0.15,
                "LLG": 0.10,
                "LLL": 0.05,
                "LLLG": 0.05,
            }


def sample_fault_spec(config: FaultSamplingConfig, sections: list,
                      rng: np.random.Generator) -> Optional[FaultSpec]:
    """Sample a random fault specification from the configured distributions.

    Parameters
    ----------
    config : FaultSamplingConfig
    sections : list of (bus1, bus2) tuples
    rng : numpy random generator

    Returns
    -------
    FaultSpec or None (if this sample should be a healthy/no-fault case)
    """
    # Decide if this is a healthy sample
    if config.include_healthy and rng.random() < config.healthy_fraction:
        return None

    # Sample fault location (uniform over all sections)
    section_idx = rng.integers(0, len(sections))
    bus1, bus2 = sections[section_idx]

    # Sample fault type
    types = list(config.fault_type_weights.keys())
    weights = np.array([config.fault_type_weights[t] for t in types])
    weights /= weights.sum()
    fault_type_str = rng.choice(types, p=weights)
    fault_type = FaultType(fault_type_str)

    # Sample faulted phases (consistent with fault type)
    faulted_phases = _sample_phases(fault_type, rng)

    # Sample fault resistance
    if config.include_hif and rng.random() < config.hif_fraction:
        # High-impedance fault
        resistance = rng.uniform(200.0, config.resistance_max)
    else:
        # Low-to-moderate impedance
        resistance = rng.uniform(config.resistance_min, 50.0)

    # Sample position along section
    if config.position_mode == "uniform":
        position = rng.uniform(0.1, 0.9)
    else:
        position = config.fixed_position

    return FaultSpec(
        section_bus1=bus1,
        section_bus2=bus2,
        fault_type=fault_type,
        faulted_phases=faulted_phases,
        fault_resistance_ohms=resistance,
        position_pu=position,
    )


def _sample_phases(fault_type: FaultType, rng: np.random.Generator) -> str:
    """Sample faulted phases consistent with the fault type."""
    if fault_type in (FaultType.LLL, FaultType.LLLG):
        return "ABC"
    elif fault_type in (FaultType.LL, FaultType.LLG):
        return rng.choice(["AB", "BC", "AC"])
    else:  # SLG
        return rng.choice(["A", "B", "C"])


def generate_dataset(n_samples: int, config: FaultSamplingConfig,
                     topology_path: str, seed: int = 42) -> dict:
    """Generate a labeled dataset of fault measurements.

    Parameters
    ----------
    n_samples : int
        Total number of samples to generate
    config : FaultSamplingConfig
        Sampling configuration
    topology_path : str
        Path to topology.json
    seed : int
        Random seed for reproducibility

    Returns
    -------
    dict with keys:
        - voltages: np.ndarray, shape (n_samples, n_monitors, 3)
        - currents: np.ndarray, shape (n_samples, n_monitors, 3)
        - voltage_angles: np.ndarray, shape (n_samples, n_monitors, 3)
        - current_angles: np.ndarray, shape (n_samples, n_monitors, 3)
        - labels_section: np.ndarray, shape (n_samples,) -- section index, -1 = healthy
        - labels_type: np.ndarray, shape (n_samples,) -- fault type encoded as int
        - labels_phase: list of str -- faulted phase string per sample
        - labels_resistance: np.ndarray, shape (n_samples,) -- fault resistance
        - metadata: dict of generation parameters
    """
    rng = np.random.default_rng(seed)

    sim = FaultSimulator(
        topology_path=topology_path,
        noise_std_voltage=config.noise_std_voltage,
        noise_std_current=config.noise_std_current,
    )

    sections = sim.get_all_sections()
    n_monitors = len(sim.monitor_buses)

    # Pre-allocate arrays
    voltages = np.zeros((n_samples, n_monitors, 3), dtype=np.float32)
    currents = np.zeros((n_samples, n_monitors, 3), dtype=np.float32)
    v_angles = np.zeros((n_samples, n_monitors, 3), dtype=np.float32)
    i_angles = np.zeros((n_samples, n_monitors, 3), dtype=np.float32)
    labels_section = np.full(n_samples, -1, dtype=np.int32)
    labels_type = np.zeros(n_samples, dtype=np.int32)
    labels_phase = []
    labels_resistance = np.zeros(n_samples, dtype=np.float32)

    # Fault type encoding: 0=healthy, 1=SLG, 2=LL, 3=LLG, 4=LLL, 5=LLLG
    type_encoding = {"healthy": 0, "SLG": 1, "LL": 2, "LLG": 3, "LLL": 4, "LLLG": 5}

    for i in range(n_samples):
        spec = sample_fault_spec(config, sections, rng)

        if spec is None:
            # Healthy sample
            v, c = sim.simulate_healthy()
            voltages[i] = v
            currents[i] = c
            labels_section[i] = -1
            labels_type[i] = 0
            labels_phase.append("none")
            labels_resistance[i] = -1.0
        else:
            response = sim.simulate_fault(spec)
            voltages[i] = response.voltages_pu
            currents[i] = response.currents_a
            v_angles[i] = response.voltage_angles_deg
            i_angles[i] = response.current_angles_deg
            labels_section[i] = response.faulted_section_index
            labels_type[i] = type_encoding[spec.fault_type.value]
            labels_phase.append(spec.faulted_phases)
            labels_resistance[i] = spec.fault_resistance_ohms

    metadata = {
        "n_samples": n_samples,
        "n_monitors": n_monitors,
        "n_sections": len(sections),
        "monitor_buses": sim.monitor_buses,
        "seed": seed,
        "config": asdict(config),
    }

    return {
        "voltages": voltages,
        "currents": currents,
        "voltage_angles": v_angles,
        "current_angles": i_angles,
        "labels_section": labels_section,
        "labels_type": labels_type,
        "labels_phase": labels_phase,
        "labels_resistance": labels_resistance,
        "metadata": metadata,
    }


def save_dataset(dataset: dict, output_path: str):
    """Save dataset to compressed numpy archive.

    The .npz file contains all arrays and metadata as a JSON string.
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # Convert labels_phase list to numpy array of strings
    labels_phase_arr = np.array(dataset["labels_phase"], dtype="U4")

    # Save metadata separately as JSON string
    metadata_str = json.dumps(dataset["metadata"], indent=2)

    np.savez_compressed(
        output_path,
        voltages=dataset["voltages"],
        currents=dataset["currents"],
        voltage_angles=dataset["voltage_angles"],
        current_angles=dataset["current_angles"],
        labels_section=dataset["labels_section"],
        labels_type=dataset["labels_type"],
        labels_phase=labels_phase_arr,
        labels_resistance=dataset["labels_resistance"],
        metadata=np.array([metadata_str]),
    )


def load_dataset(path: str) -> dict:
    """Load a saved dataset from .npz file."""
    data = np.load(path, allow_pickle=False)
    metadata = json.loads(str(data["metadata"][0]))
    return {
        "voltages": data["voltages"],
        "currents": data["currents"],
        "voltage_angles": data["voltage_angles"],
        "current_angles": data["current_angles"],
        "labels_section": data["labels_section"],
        "labels_type": data["labels_type"],
        "labels_phase": list(data["labels_phase"]),
        "labels_resistance": data["labels_resistance"],
        "metadata": metadata,
    }


def print_dataset_summary(dataset: dict):
    """Print a summary of the generated dataset."""
    n = dataset["metadata"]["n_samples"]
    types = dataset["labels_type"]
    sections = dataset["labels_section"]

    type_names = {0: "Healthy", 1: "SLG", 2: "LL", 3: "LLG", 4: "LLL", 5: "LLLG"}
    print(f"\nDataset Summary")
    print(f"  Total samples:  {n}")
    print(f"  Monitors:       {dataset['metadata']['n_monitors']}")
    print(f"  Sections:       {dataset['metadata']['n_sections']}")
    print(f"\n  Fault Type Distribution:")
    for code, name in type_names.items():
        count = int(np.sum(types == code))
        print(f"    {name:8s}: {count:5d} ({100*count/n:.1f}%)")

    n_unique_sections = len(np.unique(sections[sections >= 0]))
    print(f"\n  Unique faulted sections: {n_unique_sections} / {dataset['metadata']['n_sections']}")

    resistances = dataset["labels_resistance"]
    faulted_mask = resistances >= 0
    if faulted_mask.any():
        r_vals = resistances[faulted_mask]
        print(f"  Fault resistance range:  [{r_vals.min():.1f}, {r_vals.max():.1f}] ohms")
        hif_count = int(np.sum(r_vals > 200))
        print(f"  High-impedance faults:   {hif_count} ({100*hif_count/n:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate training data for ML fault identification"
    )
    parser.add_argument("--n_samples", type=int, default=5000,
                       help="Number of samples to generate")
    parser.add_argument("--output", type=str, default="data/generated/train.npz",
                       help="Output file path (.npz)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed")
    parser.add_argument("--noise_voltage", type=float, default=0.015,
                       help="Voltage measurement noise std (pu)")
    parser.add_argument("--noise_current", type=float, default=0.02,
                       help="Current measurement noise std (fraction)")
    parser.add_argument("--no_hif", action="store_true",
                       help="Exclude high-impedance faults")
    parser.add_argument("--healthy_fraction", type=float, default=0.10,
                       help="Fraction of healthy (no-fault) samples")
    parser.add_argument("--topology", type=str,
                       default="data/ieee123/topology.json",
                       help="Path to topology.json")

    args = parser.parse_args()

    config = FaultSamplingConfig(
        noise_std_voltage=args.noise_voltage,
        noise_std_current=args.noise_current,
        include_hif=not args.no_hif,
        healthy_fraction=args.healthy_fraction,
    )

    print(f"Generating {args.n_samples} samples (seed={args.seed})...")
    dataset = generate_dataset(
        n_samples=args.n_samples,
        config=config,
        topology_path=args.topology,
        seed=args.seed,
    )

    print_dataset_summary(dataset)

    save_dataset(dataset, args.output)
    print(f"\nSaved to: {args.output}")
