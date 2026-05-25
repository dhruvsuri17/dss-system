# ML-Based Fault Identification and Localization on the IEEE 123-Bus Distribution Feeder

**Duration**: One day (8 hours)
**Submission**: Code repository + technical report (maximum 3 pages)
**Debrief**: 45-minute technical interview the following morning

---

## Objective

Build a machine learning model that can identify and localize faults on the IEEE 123-Bus distribution feeder from sparse sensor measurements. You are provided with a working electrical simulation environment and a configurable fault generation engine. Your task is to design, train, and evaluate an ML architecture (e.g., graph neural network, transformer, or other) that takes voltage and current measurements from 8 monitor buses and predicts:

1. **Fault detection**: whether the system is in a healthy or faulted state
2. **Fault classification**: the type of fault (SLG, LL, LLG, LLL, LLLG)
3. **Fault localization**: which line section is faulted (123 possible sections)

---

## Background

Distribution-level fault location remains a substantially harder problem than transmission-level fault location. The primary reasons are: (1) radial or weakly-meshed topology with high lateral branching, (2) sparse and asynchronous sensor coverage, (3) unbalanced three-phase loading that complicates impedance-based methods, and (4) the presence of switching devices and voltage regulators that alter apparent source impedance. High-impedance faults (HIFs) compound this further -- they do not produce sufficient fault current to trip conventional overcurrent protection and must be detected from subtle waveform signatures.

This task uses the IEEE 123-bus test feeder, which is a standard EPRI benchmark for unbalanced three-phase distribution system analysis. The feeder includes overhead line segments with realistic R/X ratios, single-phase and three-phase laterals, switched capacitor banks, and voltage regulators.

---

## System Description

| Property | Value |
|---|---|
| Nominal voltage | 4.16 kV |
| Number of buses | 123 |
| Number of line sections | 123 (plus 7 normally-open tie lines) |
| Switching devices | 9 sectionalizing switches |
| Capacitor banks | 4 (switched) |
| Voltage regulators | 4 |
| Load configuration | Spot and distributed, single- and three-phase, wye and delta |
| Feeder type | Overhead, unbalanced three-phase |
| Monitor buses | 8 (buses 1, 13, 35, 52, 67, 83, 101, 113) |

The feeder topology is radial from substation bus 150. Laterals branch off the main trunk at multiple points, several of which are single-phase. This branching structure is the primary source of difficulty in lateral disambiguation during fault localization.

---

## What You Are Given

### 1. Network Model (`data/ieee123/`)

Complete electrical model of the IEEE 123-bus feeder:

- `IEEE123Master.dss` -- OpenDSS master file with full circuit definition
- `IEEELineCodes.dss` -- Line impedance configurations (R, X matrices, ampacity ratings)
- `IEEE123Loads.dss` -- Load definitions (spot loads, wye/delta, single/three-phase)
- `IEEE123Generators.dss` -- Generator definitions (empty in base case)
- `topology.json` -- Machine-readable adjacency list with all line parameters (R, X in ohms/km, length in km, phases, ampacity)

### 2. Fault Simulation Engine (`src/fault_simulator.py`)

A modular Python class that simulates fault conditions anywhere on the network and returns the resulting measurements at all monitor buses. Configurable parameters:

| Parameter | Range | Description |
|---|---|---|
| Location | Any of 123 line sections | Which segment is faulted |
| Fault type | SLG, LL, LLG, LLL, LLLG | Classification of fault |
| Faulted phase(s) | A, B, C, AB, BC, AC, ABC | Which conductors are involved |
| Fault resistance | 0 to 2000+ ohms | 0 = bolted, >200 = high-impedance |
| Position along section | 0.0 to 1.0 | Fractional distance from upstream bus |
| Measurement noise | Configurable std | Simulates metering error |

### 3. Dataset Generator (`src/generate_dataset.py`)

A command-line tool that uses the fault simulator to produce labeled development, training, and test datasets in NumPy format. You control:

- Number of samples
- Fault type distribution
- Whether to include high-impedance faults
- Noise levels
- Fraction of healthy (no-fault) samples
- Random seed for reproducibility

### 4. GNN-Ready Graph Export (`src/network.py`)

The `export_graph_for_gnn()` function produces:

- `edge_index`: (2, N_edges) directed edge array
- `edge_attr`: per-edge features (R, X, Z, length, phases, ampacity, is_tie)
- `node_features`: per-node features (is_monitor, is_substation, has_load, has_capacitor, has_regulator, degree)
- `monitor_mask`: boolean mask for nodes with sensors
- `section_to_edge_idx`: mapping from fault labels to graph edges

---

## Quick Start

Use a tiny generated dataset for fast development, then scale up to larger generated train/test datasets once the pipeline works. All of these datasets use the same IEEE 123-bus topology; only the number of simulated samples and sampling conditions change.

```bash
# Install dependencies
pip install -r requirements.txt

# Verify the simulation engine works
python src/verify_simulation.py

# Generate a tiny development dataset for fast iteration
python src/generate_dataset.py --n_samples 200 --output data/generated/dev.npz --seed 7

# Generate larger training and test datasets for final runs
python src/generate_dataset.py --n_samples 5000 --output data/generated/train.npz --seed 42

python src/generate_dataset.py --n_samples 1000 --output data/generated/test.npz --seed 99

# Optional: generate a dataset without high-impedance faults (easier subset)
python src/generate_dataset.py --n_samples 3000 --output data/generated/train_no_hif.npz --no_hif

# Optional: generate a large dataset with heavy noise
python src/generate_dataset.py --n_samples 10000 --output data/generated/train_noisy.npz \
    --noise_voltage 0.03 --noise_current 0.04
```

### Loading Generated Data

```python
import numpy as np
from src.generate_dataset import load_dataset

# Use dev.npz while building/debugging; switch to train.npz/test.npz for final runs.
data = load_dataset("data/generated/dev.npz")

# Measurements: shape (n_samples, 8_monitors, 3_phases)
X_voltage = data["voltages"]       # per-unit
X_current = data["currents"]       # amperes

# Labels
y_section = data["labels_section"]     # int, -1 = healthy, 0..122 = section index
y_type = data["labels_type"]           # int, 0=healthy, 1=SLG, 2=LL, 3=LLG, 4=LLL, 5=LLLG
y_phase = data["labels_phase"]         # str, "A", "B", "AB", "ABC", "none"
y_resistance = data["labels_resistance"]  # float, ohms (-1 for healthy)
```

### Using the Graph Structure

```python
from src.network import export_graph_for_gnn

graph = export_graph_for_gnn("data/ieee123/topology.json")

# For PyTorch Geometric:
# edge_index = torch.tensor(graph["edge_index"], dtype=torch.long)
# edge_attr = torch.tensor(graph["edge_attr"], dtype=torch.float)
# x = torch.tensor(graph["node_features"], dtype=torch.float)
```

---

## ML Prediction Tasks

The generated labels support three related prediction tasks:

| Task | Target | Label source | Meaning |
|---|---|---|---|
| Fault detection | Binary classification | `labels_type == 0` or `labels_section == -1` | Predict healthy vs. faulted |
| Fault classification | Multiclass classification | `labels_type` | Predict fault type: healthy, SLG, LL, LLG, LLL, or LLLG |
| Fault localization | Multiclass section classification | `labels_section` | Predict the faulted line section; `-1` means healthy, `0..122` index into `topology.json["lines"]` |

`labels_phase` and `labels_resistance` provide additional fault metadata. They can be used for analysis, filtering, or optional auxiliary targets, but the core localization target is the line-section index, not a binary value.

Target a solution that attempts all three prediction tasks, but this is a one-day exercise. It is acceptable if the final implementation is strongest on a subset, as long as the tradeoffs and remaining work are clear.

The task specification below describes how to generate data, design a model, evaluate these predictions, and discuss the results.

---

## Task Specification

### Part 1: Data Generation Strategy

Document your decisions around training data generation, e.g.:

- Did you develop on a tiny `dev.npz` dataset before scaling to larger `train.npz` and held-out `test.npz` datasets?
- How many samples did you generate, and why?
- What fault type distribution did you use? Did you oversample rare or difficult cases?
- How did you handle the noise level? Did you train on multiple noise conditions?
- Did you augment the data in any way beyond what the simulator provides?

### Part 2: Model Architecture

Design and implement an ML model for fault identification and localization. Your model should:

- Accept the sparse measurements as input
- Produce predictions for detection, classification, and localization
- Incorporate the network topology in a principled way. This can be through:
  - Graph neural networks operating on the feeder graph
  - Physics-informed features derived from the impedance model
  - Attention mechanisms weighted by electrical distance
  - Or another approach that demonstrably leverages the network structure

### Part 3: Evaluation

Evaluate your model on a held-out test set, such as `data/generated/test.npz`, and report:

- **Detection accuracy**: healthy vs. faulted classification
- **Classification accuracy**: fault type (conditioned on correct detection)
- **Localization accuracy**: section-level (exact match) and zone-level (within N hops of true section)
- **Performance on high-impedance faults specifically** -- these are the hardest cases
- **Confusion patterns**: which fault types or locations are most commonly misclassified, and why?

Provide calibration analysis: are your model's confidence scores meaningful?

### Part 4: Analysis and Discussion

If time permits, it would be useful to answer the following:

1. **Observability limits**: For which sections is localization fundamentally difficult given limited monitors? Characterize the structural properties (graph distance from monitors, lateral branching) that predict high localization error.

2. **Sensor placement**: If you could add 3 additional monitors anywhere on the feeder, where would you place them? Quantify the improvement using your model.

3. **High-impedance faults**: At what fault resistance does your model's localization performance degrade below acceptable levels? Is there a principled threshold?

4. **Generalization**: How sensitive is your model to the noise level at inference time vs. training time? What happens if the load profile changes?

---

## Evaluation Criteria

| Dimension | Weight | Description |
|---|---|---|
| Model architecture quality | 25% | Principled use of topology, appropriate complexity |
| Localization accuracy | 25% | Section-level and zone-level performance |
| Analysis depth | 20% | Understanding of failure modes and physical grounding |
| HIF handling | 15% | Attempt and documented reasoning for hard cases |
| Code quality and reproducibility | 15% | Clean, documented, runnable end-to-end |

---

## Constraints

- **Runtime**: Full training + evaluation must complete in under 30 minutes on a standard laptop CPU. If you use GPU training, provide a CPU inference path.
- **No external pretrained models**: You may use standard ML frameworks (PyTorch, TensorFlow, scikit-learn) but the model must be trained from scratch on the generated data.
- **Reproducibility**: Set random seeds. Your results must be reproducible from a single entry-point script.

---

## Submission Requirements

**Code**: A self-contained repository. All dependencies declared in `requirements.txt`. Results reproducible from:
```bash
python src/generate_dataset.py [your args]
python src/train.py
python src/evaluate.py
```

Use `dev.npz` for debugging and iteration. Report final metrics on a held-out `test.npz` generated with a different seed from training.

**Report**: Maximum 3 pages (excluding figures and references). Structure: (1) data generation and architecture, (2) results, (3) analysis and discussion.

---

## Repository Structure

```
ieee123-flisr/
  README.md                          # This file
  GLOSSARY.md                        # Key terms and definitions for power systems
  requirements.txt                   # Python dependencies
  .gitignore

  data/
    ieee123/                         # Network model (static)
      IEEE123Master.dss
      IEEELineCodes.dss
      IEEE123Loads.dss
      IEEE123Generators.dss
      topology.json

    generated/                       # Generated data
      dev.npz                        # Tiny development set for iteration
      train.npz                      # Larger training set
      test.npz                       # Held-out evaluation set

  src/
    fault_simulator.py               # Core simulation engine
    generate_dataset.py              # CLI tool for dataset generation
    network.py                       # Graph utilities and GNN export
    verify_simulation.py             # Simulation verification script
    train.py                         # [You implement] Model training
    evaluate.py                      # [You implement] Model evaluation
```

---

## Dependencies

```
numpy, scipy, pandas, networkx, matplotlib
```

For your ML model, you will likely also need:

```
torch, torch_geometric     # if using PyTorch + GNN
# or
tensorflow, spektral       # if using TensorFlow + GNN
# or
scikit-learn               # if using classical ML with graph features
```

Add whatever you need to `requirements.txt`.
