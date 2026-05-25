"""
Network model utilities for the IEEE 123-Bus feeder.

Provides:
  - Loading and parsing of the topology JSON
  - NetworkX graph construction
  - Export of graph structure for GNN frameworks (edge_index, node features, etc.)
  - Path and distance computations
"""

import json
import numpy as np
import networkx as nx
from typing import Tuple


def load_network_model(topology_path: str) -> dict:
    """Load the feeder topology from JSON and build a NetworkX graph.

    Returns a dictionary containing:
      - graph: NetworkX Graph with line parameters as edge attributes
      - monitor_buses: list of monitored bus IDs
      - switches: dict of switch data
      - tie_lines: dict of normally-open tie line data
      - regulators: dict of voltage regulator data
      - capacitors: dict of capacitor bank data
      - n_buses: number of buses
      - n_lines: number of line sections
      - lines: raw line data from topology JSON
    """
    with open(topology_path, "r") as f:
        topo = json.load(f)

    G = nx.Graph()

    for line in topo["lines"]:
        G.add_edge(
            line["bus1"],
            line["bus2"],
            line_id=line["id"],
            phases=line["phases"],
            linecode=line["linecode"],
            length_km=line["length"],
            R_per_km=line["R"],
            X_per_km=line["X"],
            ampacity=line["ampacity"],
            R_total=line["R"] * line["length"],
            X_total=line["X"] * line["length"],
            Z_total=np.sqrt((line["R"] * line["length"])**2 + (line["X"] * line["length"])**2),
        )

    for tie_id, tie_data in topo["tie_lines"].items():
        G.add_edge(
            tie_data["bus1"],
            tie_data["bus2"],
            line_id=tie_id,
            phases=tie_data["phases"],
            length_km=tie_data["length"],
            normally_open=True,
            is_tie=True,
        )

    return {
        "graph": G,
        "monitor_buses": topo["monitor_buses"],
        "switches": topo["switches"],
        "tie_lines": topo["tie_lines"],
        "regulators": topo["voltage_regulators"],
        "capacitors": topo["capacitor_banks"],
        "substation_bus": topo["substation_bus"],
        "nominal_voltage_kv": topo["nominal_voltage_kv"],
        "n_buses": G.number_of_nodes(),
        "n_lines": len(topo["lines"]),
        "lines": topo["lines"],
    }


def get_radial_graph(network: dict) -> nx.Graph:
    """Return a copy of the graph with tie lines removed (radial topology only)."""
    G = network["graph"].copy()
    tie_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("is_tie", False)]
    G.remove_edges_from(tie_edges)
    return G


def export_graph_for_gnn(topology_path: str) -> dict:
    """Export the network graph in a format ready for GNN frameworks.

    Returns arrays that can be directly used with PyTorch Geometric or DGL:
      - edge_index: (2, n_edges) array of directed edges (both directions)
      - edge_attr: (n_edges, n_edge_features) array of edge features
      - node_features: (n_nodes, n_node_features) array of node features
      - bus_to_idx: mapping from bus ID string to integer node index
      - idx_to_bus: mapping from integer node index to bus ID string
      - monitor_mask: boolean array indicating which nodes are monitor buses

    Edge features (per edge):
      [R_total, X_total, Z_total, length_km, phases, ampacity, is_tie]

    Node features (per node):
      [is_monitor, is_substation, has_load, has_capacitor, has_regulator, degree]
    """
    with open(topology_path) as f:
        topo = json.load(f)

    # Collect all unique buses
    bus_set = set()
    for line in topo["lines"]:
        bus_set.add(line["bus1"])
        bus_set.add(line["bus2"])
    for tie_data in topo["tie_lines"].values():
        bus_set.add(tie_data["bus1"])
        bus_set.add(tie_data["bus2"])

    bus_list = sorted(bus_set, key=lambda x: (len(x), x))
    bus_to_idx = {bus: i for i, bus in enumerate(bus_list)}
    idx_to_bus = {i: bus for bus, i in bus_to_idx.items()}
    n_nodes = len(bus_list)

    # Build edge index (undirected -> two directed edges per line)
    edge_sources = []
    edge_targets = []
    edge_features = []

    for line in topo["lines"]:
        i = bus_to_idx[line["bus1"]]
        j = bus_to_idx[line["bus2"]]
        r = line["R"] * line["length"]
        x = line["X"] * line["length"]
        z = np.sqrt(r**2 + x**2)
        feat = [r, x, z, line["length"], float(line["phases"]), float(line["ampacity"]), 0.0]

        # Both directions
        edge_sources.extend([i, j])
        edge_targets.extend([j, i])
        edge_features.extend([feat, feat])

    for tie_data in topo["tie_lines"].values():
        i = bus_to_idx[tie_data["bus1"]]
        j = bus_to_idx[tie_data["bus2"]]
        feat = [0.0, 0.0, 0.0, tie_data["length"], float(tie_data["phases"]), 0.0, 1.0]

        edge_sources.extend([i, j])
        edge_targets.extend([j, i])
        edge_features.extend([feat, feat])

    edge_index = np.array([edge_sources, edge_targets], dtype=np.int64)
    edge_attr = np.array(edge_features, dtype=np.float32)

    # Build node features
    monitor_set = set(topo["monitor_buses"])
    cap_buses = set(cap["bus"] for cap in topo["capacitor_banks"].values())
    reg_buses = set(reg["bus"] for reg in topo["voltage_regulators"].values())

    # Determine which buses have loads (from lines -- approximate by downstream buses)
    load_buses = bus_set  # simplification: most buses have loads

    node_features = np.zeros((n_nodes, 6), dtype=np.float32)
    monitor_mask = np.zeros(n_nodes, dtype=bool)

    G = nx.Graph()
    for line in topo["lines"]:
        G.add_edge(bus_to_idx[line["bus1"]], bus_to_idx[line["bus2"]])

    for idx, bus in enumerate(bus_list):
        node_features[idx, 0] = 1.0 if bus in monitor_set else 0.0
        node_features[idx, 1] = 1.0 if bus == topo["substation_bus"] else 0.0
        node_features[idx, 2] = 1.0 if bus in load_buses else 0.0
        node_features[idx, 3] = 1.0 if bus in cap_buses else 0.0
        node_features[idx, 4] = 1.0 if bus in reg_buses else 0.0
        node_features[idx, 5] = float(G.degree(idx)) if idx in G else 0.0

        if bus in monitor_set:
            monitor_mask[idx] = True

    # Section-to-edge mapping (for label alignment)
    section_to_edge_idx = {}
    for sec_idx, line in enumerate(topo["lines"]):
        i = bus_to_idx[line["bus1"]]
        j = bus_to_idx[line["bus2"]]
        section_to_edge_idx[sec_idx] = (i, j)

    return {
        "edge_index": edge_index,
        "edge_attr": edge_attr,
        "node_features": node_features,
        "monitor_mask": monitor_mask,
        "bus_to_idx": bus_to_idx,
        "idx_to_bus": idx_to_bus,
        "section_to_edge_idx": section_to_edge_idx,
        "n_nodes": n_nodes,
        "n_edges": edge_index.shape[1],
        "n_sections": len(topo["lines"]),
        "edge_feature_names": ["R_total", "X_total", "Z_total", "length_km", "phases", "ampacity", "is_tie"],
        "node_feature_names": ["is_monitor", "is_substation", "has_load", "has_capacitor", "has_regulator", "degree"],
    }


def get_path_impedance(G: nx.Graph, bus_a: str, bus_b: str) -> Tuple[float, float, float]:
    """Compute total impedance along the path between two buses."""
    try:
        path = nx.shortest_path(G, bus_a, bus_b)
    except nx.NetworkXNoPath:
        return None, None, None

    R_total = 0.0
    X_total = 0.0
    for i in range(len(path) - 1):
        edge_data = G[path[i]][path[i + 1]]
        R_total += edge_data.get("R_total", 0.0)
        X_total += edge_data.get("X_total", 0.0)

    Z_total = np.sqrt(R_total**2 + X_total**2)
    return R_total, X_total, Z_total
