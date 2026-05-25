"""
Verification script for the fault simulation engine.

Runs a small set of fault simulations and validates that the outputs are
physically reasonable. Use this to confirm the simulation is working before
generating large training datasets.

Usage:
    python src/verify_simulation.py
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fault_simulator import FaultSimulator, FaultSpec, FaultType
from network import export_graph_for_gnn


def main():
    topology_path = "data/ieee123/topology.json"

    print("=" * 60)
    print("IEEE 123-Bus Fault Simulation -- Verification")
    print("=" * 60)

    # Initialize simulator
    sim = FaultSimulator(topology_path, noise_std_voltage=0.0, noise_std_current=0.0)
    print(f"\nNetwork loaded:")
    print(f"  Buses:    {sim.n_buses}")
    print(f"  Sections: {sim.n_lines}")
    print(f"  Monitors: {sim.monitor_buses}")

    # Test healthy state
    print("\n--- Healthy State ---")
    v, i = sim.simulate_healthy()
    print(f"  Voltage range: [{v.min():.4f}, {v.max():.4f}] pu")
    print(f"  Current range: [{i.min():.2f}, {i.max():.2f}] A")

    # Test each fault type
    test_section = ("12", "13")  # main trunk near monitor bus 13
    fault_configs = [
        FaultSpec(*test_section, FaultType.SLG, "A", 0.1, 0.5),
        FaultSpec(*test_section, FaultType.LL, "AB", 0.1, 0.5),
        FaultSpec(*test_section, FaultType.LLL, "ABC", 0.0, 0.5),
        FaultSpec(*test_section, FaultType.SLG, "A", 500.0, 0.5),  # HIF
    ]

    for spec in fault_configs:
        response = sim.simulate_fault(spec)
        v_min = response.voltages_pu.min()
        i_max = response.currents_a.max()
        print(f"\n--- {spec.fault_type.value} on {spec.section_bus1}-{spec.section_bus2} "
              f"(Rf={spec.fault_resistance_ohms} ohm, phase={spec.faulted_phases}) ---")
        print(f"  V_min: {v_min:.4f} pu  |  I_max: {i_max:.2f} A")

        # Per-monitor summary
        for idx, bus in enumerate(sim.monitor_buses):
            v_phase = response.voltages_pu[idx]
            i_phase = response.currents_a[idx]
            print(f"    Bus {bus:>3s}: V=[{v_phase[0]:.3f}, {v_phase[1]:.3f}, {v_phase[2]:.3f}] "
                  f"I=[{i_phase[0]:.1f}, {i_phase[1]:.1f}, {i_phase[2]:.1f}]")

    # Test a fault on a remote lateral
    print("\n--- SLG on remote single-phase lateral (bus 84-85) ---")
    remote_spec = FaultSpec("84", "85", FaultType.SLG, "A", 5.0, 0.5)
    response = sim.simulate_fault(remote_spec)
    for idx, bus in enumerate(sim.monitor_buses):
        v_phase = response.voltages_pu[idx]
        print(f"    Bus {bus:>3s}: V=[{v_phase[0]:.3f}, {v_phase[1]:.3f}, {v_phase[2]:.3f}]")

    # Verify GNN export
    print("\n--- GNN Graph Export ---")
    gnn_data = export_graph_for_gnn(topology_path)
    print(f"  Nodes:         {gnn_data['n_nodes']}")
    print(f"  Edges:         {gnn_data['n_edges']} (directed)")
    print(f"  Edge features: {len(gnn_data['edge_feature_names'])} "
          f"({', '.join(gnn_data['edge_feature_names'])})")
    print(f"  Node features: {len(gnn_data['node_feature_names'])} "
          f"({', '.join(gnn_data['node_feature_names'])})")
    print(f"  Monitor nodes: {gnn_data['monitor_mask'].sum()}")

    # Quick sanity checks
    assert v.shape == (8, 3), f"Unexpected voltage shape: {v.shape}"
    assert i.shape == (8, 3), f"Unexpected current shape: {i.shape}"
    assert 0.8 < v.mean() < 1.1, f"Voltage mean out of range: {v.mean()}"
    assert gnn_data["n_nodes"] > 100, f"Too few nodes: {gnn_data['n_nodes']}"
    assert gnn_data["monitor_mask"].sum() == 8, "Monitor count mismatch"

    print("\n" + "=" * 60)
    print("All checks passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
