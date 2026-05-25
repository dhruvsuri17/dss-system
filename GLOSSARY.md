# Power Systems Glossary: Key Terms and Definitions

This document provides definitions for fundamental power systems concepts relevant to the IEEE 123-Bus FLISR task. It is intended for readers who are new to distribution system engineering.

---

## Network Topology and Structure

### Bus
A bus is a node in the electrical network where one or more circuit elements (lines, loads, generators, transformers) connect. In distribution systems, a bus typically corresponds to a physical junction point such as a pole, pad-mounted transformer, or switching cabinet. Buses are identified by unique integer labels.

### Feeder
A feeder is a distribution circuit that carries power from a substation to downstream loads. A feeder typically operates at medium voltage (4 to 35 kV) and serves hundreds to thousands of customers. The IEEE 123-bus system represents one such feeder.

### Radial Topology
A radial network is one in which there exists exactly one path from the source (substation) to any load. Distribution systems are predominantly radial, unlike transmission systems which are meshed. Radiality simplifies protection coordination but makes service restoration after faults more constrained.

### Lateral
A lateral is a branch circuit that taps off the main feeder trunk to serve a subset of loads. Laterals may be three-phase or single-phase. Single-phase laterals are common in rural areas and serve lighter loads.

### Main Trunk
The main trunk (or backbone) is the primary three-phase path from the substation to the end of the feeder. It carries the aggregate current for all downstream loads and laterals.

### Substation
A substation is the facility where the transmission system (high voltage, typically 69 to 500 kV) steps down to distribution voltage levels (4 to 35 kV). The substation bus is the electrical source for the feeder.

---

## Electrical Quantities

### Voltage (V)
The electric potential difference between two points in a circuit, measured in volts (V) or kilovolts (kV). In three-phase systems, voltage is specified either line-to-line (between phases) or line-to-neutral (phase to ground).

### Per-Unit (pu) System
A normalization system where quantities are expressed as a fraction of a defined base value. For voltage, 1.0 pu equals the nominal voltage. A measurement of 0.95 pu indicates the voltage is 5% below nominal. The per-unit system simplifies calculations across different voltage levels.

### Current (I)
The flow of electric charge through a conductor, measured in amperes (A). In distribution systems, current magnitude indicates the power being delivered and is the primary quantity used for overcurrent protection.

### Impedance (Z = R + jX)
The opposition to alternating current flow in a circuit element, with units of ohms. Impedance has a real component (resistance, R) representing energy dissipation as heat, and an imaginary component (reactance, X) representing energy storage in magnetic or electric fields.

### Resistance (R)
The component of impedance that dissipates energy. For a distribution line, resistance depends on conductor material, cross-section, and temperature. Units: ohms per kilometer (ohms/km).

### Reactance (X)
The component of impedance due to inductance (magnetic field) or capacitance (electric field). For overhead distribution lines, inductive reactance dominates. Units: ohms per kilometer (ohms/km).

### Ampacity
The maximum continuous current-carrying capacity of a conductor before it exceeds its thermal rating. Exceeding ampacity causes conductor heating that may result in sag, insulation damage, or failure. Units: amperes (A).

### Power Factor
The ratio of real power (watts) to apparent power (volt-amperes) in an AC circuit. A power factor less than 1.0 indicates that current and voltage are not perfectly in phase, resulting in additional current flow to deliver the same real power.

### Real Power (P)
The time-averaged power that performs useful work, measured in watts (W) or kilowatts (kW).

### Reactive Power (Q)
The oscillating component of power that transfers energy between source and load inductance/capacitance without performing net work. Measured in volt-amperes reactive (var) or kilovolt-amperes reactive (kvar). Reactive power affects voltage levels and must be managed.

---

## Three-Phase Systems

### Three-Phase Power
An AC system using three conductors carrying sinusoidal voltages displaced by 120 degrees from each other. Three-phase systems are more efficient for power transmission than single-phase and produce a constant instantaneous power when balanced.

### Phase (A, B, C)
Each of the three conductors in a three-phase system. In balanced operation, all three phases carry equal current at equal voltage with 120-degree phase separation.

### Unbalanced Operation
A condition where the three phases do not carry equal currents or have equal voltages. Distribution systems are inherently unbalanced because loads are not equally distributed across phases and single-phase laterals create asymmetric loading.

### Wye (Star) Connection
A load or transformer winding configuration where one terminal of each phase winding connects to a common neutral point. The line-to-neutral voltage is the line-to-line voltage divided by the square root of 3.

### Delta Connection
A load or transformer winding configuration where phase windings are connected in series to form a closed triangle. Delta connections have no neutral and see full line-to-line voltage.

### Sequence Components (Positive, Negative, Zero)
A mathematical decomposition of unbalanced three-phase quantities into three balanced sets: positive-sequence (normal rotation), negative-sequence (reverse rotation), and zero-sequence (in-phase). Sequence analysis is the primary tool for analyzing asymmetric faults.

---

## Faults

### Fault
An unintended connection between conductors or between a conductor and ground, resulting in abnormal current flow. Faults may be caused by lightning, equipment failure, vegetation contact, animal contact, or insulation degradation.

### Short Circuit
A fault with very low impedance at the fault point, resulting in very high fault current. The current magnitude is limited primarily by the source impedance and the impedance of the path between the source and the fault location.

### Single Line-to-Ground Fault (SLG)
A fault involving one phase conductor and the earth/ground. SLG faults are the most common fault type in distribution systems (approximately 70 to 80% of all faults). They produce zero-sequence current.

### Line-to-Line Fault (LL)
A fault involving two phase conductors. LL faults produce negative-sequence current but no zero-sequence current (unless also involving ground).

### Three-Phase Fault (LLL or LLLG)
A fault involving all three phase conductors simultaneously (with or without ground). Three-phase faults are the most severe in terms of fault current magnitude but are the rarest type (less than 5% of distribution faults).

### Bolted Fault
A fault with zero impedance at the fault point, representing the worst-case maximum fault current condition. Named after the practice of literally bolting conductors together during testing.

### High-Impedance Fault (HIF)
A fault where the fault path has substantial resistance (typically 200 to 2000+ ohms), resulting in fault current that may be comparable to or less than normal load current. HIFs are caused by downed conductors on high-resistance surfaces (dry earth, asphalt, concrete) or through vegetation. They are extremely difficult to detect with conventional overcurrent protection.

### Fault Resistance
The resistance at the point of fault. Low-resistance faults (less than 1 ohm) produce large fault currents. High-resistance faults (hundreds of ohms) produce small fault currents that may not trigger protection devices.

### Fault Current
The abnormally high current that flows through the faulted path. Fault current magnitude depends on the source strength, the impedance between the source and the fault, and the fault resistance.

---

## Protection and Switching

### Overcurrent Relay
A protective device that operates (trips) when the current through it exceeds a preset threshold (pickup value) for a specified time duration. Overcurrent relays are the primary protection mechanism in radial distribution systems.

### Pickup Current
The minimum current magnitude at which a relay begins its timing sequence. If current remains above pickup for longer than the relay's time delay setting, the relay issues a trip command.

### Trip
The action of opening a circuit breaker or switch to disconnect a faulted section from the energized network. A trip de-energizes all loads downstream of the opening device.

### Recloser
An automatic circuit-interrupting device that opens on fault current, waits a preset time, then recloses. If the fault has cleared (a temporary fault), service is restored automatically. If the fault persists, the recloser locks out after a set number of attempts.

### Sectionalizing Switch
A switching device that can open or close a circuit section, but typically has no fault-interrupting capability. Sectionalizing switches are used to isolate faulted sections and reconfigure the network during restoration.

### Fuse
A one-time protective device that melts and permanently opens when current exceeds its rating. Fuses are inexpensive and common on distribution laterals, but require physical replacement after operation.

### Protection Coordination
The engineering of relay settings such that the device nearest to a fault operates first, minimizing the number of customers affected by the outage. Coordination relies on time-current curve relationships between upstream and downstream devices.

### Normally Open (NO) Tie Switch
A switch on a line connecting two normally independent feeders, kept open during normal operation. When a fault isolates a section of one feeder, a tie switch can be closed to supply the isolated section from an alternate source while maintaining radial topology.

### Normally Closed (NC) Switch
A sectionalizing switch that is closed during normal operation, allowing power to flow through it. It can be opened to isolate a faulted section.

---

## FLISR (Fault Location, Isolation, and Service Restoration)

### Fault Location
The process of determining where on the network a fault has occurred. Methods include impedance-based estimation, traveling-wave analysis, and pattern matching of voltage/current measurements against a network model.

### Fault Isolation
The process of opening the minimum number of switching devices to disconnect the faulted section from all energized parts of the network, preventing continued fault current flow and protecting equipment.

### Service Restoration
The process of reconfiguring the network topology (opening and closing switches) to re-energize as many de-energized load buses as possible through alternate supply paths, while maintaining all operating constraints (radiality, thermal limits, voltage limits).

### FLISR
An automated or semi-automated system that performs Fault Location, Isolation, and Service Restoration as an integrated sequence. Modern distribution automation (DA) systems implement FLISR to reduce outage duration.

---

## Distribution System Equipment

### Voltage Regulator
An autotransformer with adjustable tap positions that maintains voltage within a specified band at its output terminal. As load increases and voltage drops along the feeder, regulators boost voltage to maintain it within acceptable limits (typically +/- 5% of nominal).

### Tap Position
The discrete setting of a voltage regulator that determines the voltage boost or buck ratio. Each tap step typically corresponds to 0.625% voltage change. Regulators have a finite range (e.g., +/- 10% in 32 steps).

### Bandwidth (Regulator)
The dead band around the voltage set point within which the regulator does not change taps. Prevents hunting (rapid tap changes) due to small voltage fluctuations.

### Capacitor Bank
A device that injects reactive power into the system to improve power factor and support voltage. Switched capacitor banks can be controlled to connect or disconnect based on voltage, current, or time-of-day criteria.

### Transformer
A device that transfers electrical energy between circuits through electromagnetic induction, changing the voltage level. Distribution transformers step down medium voltage (4 to 35 kV) to utilization voltage (120/240 V for residential loads).

---

## Measurements and Monitoring

### SCADA (Supervisory Control and Data Acquisition)
A centralized system for monitoring and controlling distribution system operations. SCADA provides real-time measurements (voltage, current, power, switch status) at instrumented points and allows remote switch operation.

### Monitor Bus
A bus equipped with voltage and current transducers that report measurements to the SCADA system. Not all buses are monitored; unmonitored buses must have their state inferred from nearby monitored points and the network model.

### Metering Class
A specification of instrument transformer (potential transformer and current transformer) accuracy. Class 0.5 instruments have a maximum error of 0.5% of the measured value under specified conditions.

### Sampling Interval
The time between successive measurements reported by a monitoring device. A 15-minute interval is typical for SCADA in distribution systems. Higher resolution (sub-second) data from digital fault recorders or phasor measurement units is available only at select locations if at all.

---

## Analysis Methods

### Power Flow (Load Flow)
A computational method that determines the steady-state voltage at every bus and current through every line in the network for a given set of loads and generation. Power flow solves the nonlinear algebraic equations governing the network.

### State Estimation
A statistical method that uses a redundant set of measurements (some with errors) to estimate the most likely operating state (voltages, currents, power flows) of the entire network, including at unmonitored points.

### Impedance-Based Fault Location
A method that uses measured voltages and currents at a monitoring point to estimate the apparent impedance between the monitor and the fault. The estimated impedance is then mapped to a distance (and hence a section) on the feeder. Lateral branching causes multiple candidate locations (ambiguity).

### Bayesian Inference
A probabilistic framework for updating beliefs about unknown quantities (e.g., fault location) given observed evidence (e.g., voltage dips at monitor buses). The posterior probability of each candidate fault location is proportional to the product of the prior probability and the likelihood of the observed measurements given that fault location.

---

## Graph Theory Concepts (Applied to Networks)

### Adjacency List
A representation of a graph where each node maps to a list of its neighboring nodes, optionally with edge attributes (impedance, length, phases). The topology.json file uses this representation.

### Tree
A connected graph with no cycles. A radial distribution network is a tree rooted at the substation bus.

### Path
A sequence of edges connecting two nodes. In a tree, the path between any two nodes is unique.

### Cut Set
A set of edges whose removal disconnects the graph into two or more components. In fault isolation, opening the switches in a cut set that separates the faulted section from the source achieves isolation.

### Spanning Tree
A subgraph that includes all vertices of the original graph and is a tree. During service restoration with tie switches, the objective is to find a spanning tree of the restorable subgraph that satisfies all constraints.

---

## Units Reference

| Quantity | Symbol | Unit | Abbreviation |
|---|---|---|---|
| Voltage | V | volts | V |
| Voltage (distribution) | V | kilovolts | kV |
| Current | I | amperes | A |
| Resistance | R | ohms | ohm |
| Reactance | X | ohms | ohm |
| Impedance | Z | ohms | ohm |
| Real power | P | kilowatts | kW |
| Reactive power | Q | kilovolt-amperes reactive | kvar |
| Apparent power | S | kilovolt-amperes | kVA |
| Frequency | f | hertz | Hz |
| Length | l | kilometers | km |

---

## Acronyms

| Acronym | Expansion |
|---|---|
| ACSR | Aluminum Conductor Steel Reinforced |
| DA | Distribution Automation |
| DER | Distributed Energy Resource |
| DSS | Distribution System Simulator (OpenDSS) |
| EPRI | Electric Power Research Institute |
| FLISR | Fault Location, Isolation, and Service Restoration |
| GNN | Graph Neural Network |
| HIF | High-Impedance Fault |
| IEEE | Institute of Electrical and Electronics Engineers |
| LL | Line-to-Line (fault type) |
| LLG | Line-to-Line-to-Ground (fault type) |
| LLL | Three-Phase (fault type) |
| LLLG | Three-Phase-to-Ground (fault type) |
| NC | Normally Closed |
| NO | Normally Open |
| OC | Overcurrent |
| SCADA | Supervisory Control and Data Acquisition |
| SLG | Single Line-to-Ground (fault type) |

---

## ML Concepts Applied to Power Systems Fault Analysis

### Graph Neural Network (GNN)
A class of neural networks designed to operate on graph-structured data. In power systems, the feeder topology forms a natural graph where buses are nodes and line sections are edges. GNNs can learn representations that respect the connectivity and electrical relationships between buses, making them well-suited for fault localization where the spatial structure of the network determines how fault signatures propagate.

### Message Passing
The core computation in most GNNs. Each node aggregates information from its neighbors, combines it with its own features, and produces an updated representation. In a power systems context, message passing mimics how voltage and current disturbances propagate along the feeder -- a fault at one location produces observable effects at electrically connected buses, with magnitude decaying with electrical distance.

### Node Classification vs. Edge Classification
In fault localization, the prediction target can be framed as node classification (which bus is nearest the fault?) or edge classification (which line section is faulted?). Edge classification is the more natural framing since faults occur on line segments, not at buses, but both formulations are valid.

### Observability
A system is observable if all state variables can be uniquely determined from available measurements. With only 8 monitor buses on a 123-bus feeder, the system is highly under-observed. This means that multiple fault locations can produce indistinguishable measurement signatures -- a fundamental limit that no model can overcome without additional sensors.

### Transfer Impedance
The voltage observed at bus j due to a unit current injection at bus k. Transfer impedance determines how "visible" a fault at location k is from a sensor at location j. Faults at locations with low transfer impedance to all monitors are inherently difficult to detect and localize.

### Electrical Distance
A measure of the impedance between two points in the network. Unlike topological (hop) distance, electrical distance accounts for the impedance of each line section. Two buses that are many hops apart on low-impedance lines may be electrically closer than two buses separated by a single high-impedance segment.

### Feature Engineering (Power Systems Context)
The process of constructing informative input features from raw measurements. In fault analysis, useful derived features include: voltage magnitude deviation from nominal, current magnitude relative to normal load, negative-sequence voltage (indicator of unbalanced faults), zero-sequence voltage (indicator of ground faults), and rate-of-change of voltage.
