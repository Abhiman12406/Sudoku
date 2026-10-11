# Bounded Context: IO Signal Sudoku

Core domain model, architecture principles, and glossary for the Emerson DeltaV Electronic Marshalling automated allocation and revision management system.

## 1. Domain Vocabulary & Ubiquitous Language

- **Signal (Channel):** A single field instrument loop (e.g., pressure transmitter, solenoid valve) requiring I/O processing. Identified by a unique `Tag` (e.g., `10-FT-101A`).
- **Trunk Cable (Cable Block):** A multi-conductor bundle containing 2, 6, 12, or 24 pairs. All pairs within a cable must land contiguously on physical baseplates in pair order.
- **CHARM (Characterization Module):** A single-channel modular hardware component providing A/D or D/A conversion, galvanic isolation, current limiting, and loop health diagnostics.
- **Terminal Block (TB):** Snaps onto the baseplate beneath the CHARM (Standard, CJC for thermocouples, Relay Output Form C, or Fused Injected-Power for 1.0A continuous Solenoid Valves).
- **CHARM Baseplate:** Physical DIN-rail unit housing exactly **12 physical slots** and an address plug (1–8).
- **CHARM I/O Carrier (CIOC):** Hardware card controlling up to **8 Baseplates** ($8 \times 12 = 96$ channels).
- **Marshalling Cabinet:** Enclosure housing up to **4 CIOC pairs** ($4 \times 96 = 384$ channels single-sided).
- **Duty/Standby Segregation (A/B Redundancy):** Safety-critical separation rule requiring that Train A and Train B signals never reside on the same CIOC.
- **Wired Spare:** An unallocated physical pair inside a multi-conductor trunk cable reserved for future field growth.
- **Reserved Capacity / Spare Margin:** Percentage or fixed count of baseplates/slots intentionally left unassigned in a cabinet for expansion.
- **Technical Query (TQ):** A formal engineering clarification document (e.g. `TQ-INST-001`) generated whenever input data is contradictory, corrupt, or exceeds physical capacity.
- **Revision Perturbation Metric:** A quantitative measure of labor displacement between Rev A and Rev B allocations ($\min \Delta = 10000 \cdot \Delta_{\text{cabinet}} + 1000 \cdot \Delta_{\text{CIOC}} + \dots$).

## 2. Core Architectural Invariants

1. **Deterministic Constraint Optimization:** The core allocation engine relies strictly on mathematical constraint programming (Google OR-Tools CP-SAT), never probabilistic LLMs.
2. **Two-Stage Hierarchical Packing:** Grouping signals into rigid cable blocks (Stage 1) prevents $10^8$ variable combinatorial explosion; in-baseplate slot assignment (Stage 2) enforces strict ascending pair order.
3. **Linearized Indicator Redundancy Cuts:** Segregation constraints are enforced using CIOC-level indicators ($U_c^A + U_c^B \le 1$) rather than pairwise exclusion.
4. **Independent Post-Solve Verification:** An independent audit pass validates 100% of hard physical rules before exporting any Excel file.
5. **Exact Template Fidelity:** The generated workbook preserves customer template standards and produces formal multi-sheet engineering deliverables.
