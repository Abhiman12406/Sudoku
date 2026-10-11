# SIH Problem Statement Analysis: IO Signal Sudoku

**Domain:** Industrial Automation · Constraint Optimization · Engineering Software  
**Verdict:** 🟢 Green Light — strong hackathon opportunity, provided the team focuses on allocation correctness.

> **Problem in one sentence:** Build an intelligent tool that converts industrial instrument signals from Excel into a valid, optimized DeltaV DCS I/O allocation, following configurable engineering rules and automatically reporting conflicts and revision changes.

## Executive Summary

The workflow is:

1. **Input:** Customer I/O master database (MDB) and required Excel output template.
2. **Process:** Allocate signals to cabinets, CIOCs, baseplates and CHARM slots while respecting capacity, segregation, cable grouping, hardware selection and spare requirements.
3. **Output:** Completed Excel allocation, rule-check report, technical query (TQ) list, cabinet utilization and revision comparison.

The key is not simply assigning the next free slot. One assignment can affect cable continuity, segregation, hardware compatibility, capacity, future expansion and previous allocations.

### Initial feasibility

| Dimension | Assessment |
|---|---|
| Working hackathon prototype | Feasible |
| Allocate a sample database automatically | Feasible |
| Enforce all user-defined rules | Requires careful design |
| Minimize revision changes | Optimization challenge |
| Production-ready industrial deployment | Beyond MVP |
| AI/ML required for core allocation | No; deterministic constraints are preferable |

**Recommendation:** Build a deterministic constraint-solving engine with a clear interface. Use AI to assist with Excel column mapping, draft rule interpretation and explanations—not to make final allocation decisions without validation.

---

## 1. 🔎 Pain Points & Core Understanding

### What exactly is the problem?

Industrial plants contain instruments such as pressure transmitters, temperature sensors, switches, control valves and alarms. Their signals must be mapped to physical locations in the control-system architecture:

**Field instruments/signals → Marshalling cabinet → CIOC → Baseplate → CHARM slot → Validated Excel allocation**

Each signal may carry a tag, signal type, cable, pair, group and segregation requirements.

### Root causes and pain points

| Pain point | Why it matters | What the tool should do |
|---|---|---|
| Manual Excel allocation | Thousands of signals are tedious to allocate and verify | Automatically allocate signals |
| Interdependent rules | A locally valid assignment may break another rule | Validate the complete allocation |
| Customer revisions | One change can trigger extensive rework | Preserve unchanged allocations and minimize moves |
| Missing/conflicting data | Some signals cannot be allocated safely | Generate actionable TQs |
| Incorrect hardware selection | Signals may require specific CHARM or terminal hardware | Use a configurable hardware rule table |
| Poor capacity planning | Cabinets may be overfilled or lack spares | Calculate utilization, spare slots and cabinet needs |
| Inconsistent naming | Projects use different naming conventions | Generate names using editable patterns |

The brief identifies manual processing of 10,000+ signals, customer revisions, configurable rules and unresolved data conflicts as central concerns.

### Stakeholders

- **Instrumentation and control engineers:** primary users who need correct allocation, hardware mapping and validation.
- **DCS and panel engineers:** need implementable cabinet, CIOC/baseplate and marshalling details.
- **EPC contractors and project managers:** need less rework, traceable changes and predictable delivery.
- **Commissioning and maintenance teams:** benefit from accurate documentation and easier troubleshooting.

### Important distinctions

- **Wired spare:** A pair reserved as spare within a cable.
- **Free slot:** A slot not currently assigned.
- **Reserved capacity:** Space intentionally held for future growth.
- **Unallocated signal:** A signal that has not received a valid slot.

These must not be treated as interchangeable. The brief's 24-pair cable example shows 22 signals and two wired spare pairs; wired spares are not the same as unused hardware slots.

---

## 2. ⚙️ Feasibility of Execution

### Can it be built in a hackathon?

Yes, if the team prioritizes a complete end-to-end workflow rather than advanced AI features.

### Recommended stack

| Layer | Suggested tools | Purpose |
|---|---|---|
| Excel ingestion/export | Python, pandas, openpyxl | Read source files, map columns, preserve output template |
| Allocation engine | Google OR-Tools CP-SAT | Model constraints and optimize allocation |
| UI | Streamlit for speed; or React + FastAPI | Upload, rule editing, visualization and results |
| Validation/testing | pytest and an independent rule checker | Verify hard constraints and regression cases |

References:
- [Google OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver/)
- [OR-Tools constraint programming](https://developers.google.com/optimization/cp)

### Architecture principle

Separate the system into three layers:

1. **Hard constraints:** Conditions that must never be violated, such as capacity, signal uniqueness and A/B segregation.
2. **Optimization objectives:** Preferences such as keeping cables together, preserving existing placements and minimizing cabinets.
3. **Independent validator:** A separate pass that checks the proposed allocation before export.

### Main blockers and mitigations

| Blocker | Mitigation |
|---|---|
| Complex rule combinations | Start with core constraints and set solver time limits |
| Ambiguous engineering rules | Flag conflicts and generate TQs |
| Variable Excel headers | Provide column mapping and preview |
| Cable continuity/pair order | Model physical placement explicitly, not as simple bin packing |
| Revision optimization | Preserve feasible placements; move only what is necessary |
| Hidden test | Test changed headers, new signals and revisions—not just the sample |

### Recommended MVP

1. Upload customer MDB and output template.
2. Configure, enable and disable rules.
3. Allocate signals and export the required Excel template.
4. Generate rule-check report and TQs.
5. Compare Rev A and Rev B, including changed allocations and impacted cabinets.

A dashboard alone is insufficient. The exported workbook, reports, naming, hardware compatibility and revision workflow are core deliverables.

---

## 3. 🌍 Impact & Relevance

| Beneficiary | Potential benefit |
|---|---|
| Instrumentation engineers | Less repetitive allocation and checking |
| EPC companies | Faster engineering and revision handling |
| Plant owners | More consistent engineering documentation |
| Commissioning teams | Easier identification of discrepancies |
| Project managers | Better visibility into cabinets, spare capacity and scope changes |

### How to measure impact

Do not claim a savings percentage without a manual baseline. Measure:

- Time to process the sample MDB.
- Percentage of signals allocated or explained by TQ.
- Hard-rule violations after validation.
- Number of TQs raised.
- Number of signals moved between revisions.
- Cabinets and spare slots required.

The direct impact is industrial productivity and reliability. Reduced rework or hardware waste is plausible, but should be measured rather than assumed.

### Scalability path

- **Stage 1 — Hackathon:** Sample Excel files, one DeltaV workflow, editable rules and reports.
- **Stage 2 — Engineering pilot:** Larger datasets, version history, reusable project profiles, audit logs and engineer approval.
- **Stage 3 — Enterprise:** Multi-project access, controlled templates, configuration management, integrations and additional supported hardware platforms.

The strongest path is to prove the tool on a realistic project before expanding across organizations or platforms.

---

## 4. 💡 Innovation & Competitor Analysis

The comparison below covers relevant adjacent technologies. It does **not** establish that no direct competitor exists; a commercial product matching every requirement has not been verified in this analysis.

### Relevant products and tools

| Product/tool | Strength | Opportunity for this solution |
|---|---|---|
| [Emerson DeltaV](https://www.emerson.com/en-us/automation-systems) | Target DCS ecosystem and hardware concepts | Build an upstream allocation assistant; do not imply official integration |
| [AutoCAD Electrical](https://www.autodesk.com/products/autocad/included-toolsets/autocad-electrical) | Electrical design and documentation | Differentiate through signal-to-slot constraints, TQs and revision-aware placement |
| [EPLAN](https://www.eplan.com/) | Electrical engineering documentation | Focus on configurable allocation rules and explainable conflicts |
| [Google OR-Tools](https://developers.google.com/optimization) | Open-source combinatorial optimization toolkit | Use as the solver foundation; it is not a ready-made DeltaV allocation application |

### Research and standards

- [OR-Tools constraint programming](https://developers.google.com/optimization/cp): relevant to modelling constraints and objectives.
- [ISA-5 standards series](https://www.isa.org/standards-and-publications/isa-standards/isa-5-standard): background for instrumentation identification and documentation. It does not replace project-specific rules.

### Differentiating features

1. **Configurable rule engine:** Engineers add, modify, enable and disable rules without changing source code.
2. **Revision-aware optimization:** Minimize unnecessary moves while respecting mandatory constraints.
3. **Explainable TQs:** Identify the affected signal, missing field/conflicting rule and required clarification.
4. **Cabinet/baseplate visualizer:** Show occupied slots, cable positions, wired spares, reserved capacity and free slots.
5. **AI-assisted data preparation:** Suggest column mappings and draft structured rules from plain language, with user approval and validation.

**Strongest recommendation:** Prioritize revision-aware optimization and explainable TQs. Blockchain, AR/VR or unrelated ML features are unlikely to address the central challenge as directly.

---

## 5. 🧩 Clarity of the Problem Statement

### Deliverables

| Deliverable | What should be verifiable |
|---|---|
| Working tool | Upload one or multiple Excel files |
| Configurable rules | Add, edit, enable and disable rules |
| Allocation export | Generate the required template end-to-end |
| Reports and TQs | Show violations, unresolved signals and data issues |
| Revision comparison | Compare Rev A and Rev B |
| Demo and source code | Demonstrate workflow and explain implementation |

The brief's definition of done expects every input signal to have a valid slot or a TQ explaining why it could not be allocated, zero violations of configured rules, correct hardware/names and revision stability.

### Common misinterpretations

- **“It is just Excel automation.”** Excel is the input/output format; constraint-based allocation is the core.
- **“AI should choose every slot.”** Deterministic rules and a solver should make allocation decisions.
- **“Every signal must be assigned regardless of feasibility.”** Impossible allocations should produce TQs, not fabricated slots.
- **“A dashboard proves correctness.”** The workbook, independent validation and revision comparison are the evidence.

### Recommended product framing

> **IO Signal Sudoku** is a rule-driven industrial I/O allocation and revision management tool. It converts customer Excel databases into validated DeltaV I/O allocation templates using configurable engineering constraints and hardware mappings. It independently checks the allocation, generates actionable technical queries for unresolved conflicts, and minimizes unnecessary changes between project revisions.

---

## 6. 🎯 Evaluator's Perspective

The exact scoring rubric is not included in the problem statement. These priorities are reasoned from the stated requirements, not an official SIH marking scheme.

### Likely evaluation priorities

1. **Correctness:** Hard constraints are satisfied.
2. **Complete engineering output:** Excel template, names, hardware assignments, TQs and utilization reports.
3. **Revision handling:** Preserve feasible existing placements and minimize unnecessary changes.
4. **Flexibility:** Different databases and rules work without code changes.
5. **Usability and explanation:** Team can demonstrate and explain the algorithm.

### Red flags

- Hard-coded rules hidden behind a configurable-looking UI.
- Reporting full allocation despite violations.
- Reallocating everything on every revision.
- Logic that only works for sample column names.
- LLM-generated hardware/slot assignments without deterministic checks.
- Exporting a new spreadsheet instead of filling the required template.
- No demonstration of a conflict or failure case.

### Strong demo scenario

Introduce a conflict—for example, two signals that must remain segregated but have incompatible placement restrictions. Show the conflict detection, explanation, TQ, correction and successful reallocation. This demonstrates engineering-aware failure handling, not just the happy path.

---

## 7. 👥 Team Fit & Execution Strategy

### Suggested six-person team

| Role | Responsibility |
|---|---|
| 1. Optimization lead | Constraint model, capacity, segregation, revision objectives |
| 2. Data/Excel engineer | Parsing, column mapping, template export, data validation |
| 3. Frontend/UI engineer | Upload flow, rule editor, visualization, results |
| 4. Backend engineer | APIs, orchestration, revision diffs and reports |
| 5. Testing/validation engineer | Independent checker, edge cases and regression tests |
| 6. Integration/domain/pitch lead | Rule interpretation, integration and evaluator Q&A |

For smaller teams, combine roles. Keep allocation modelling and independent validation as distinct responsibilities wherever possible.

### Illustrative 24-hour sprint

| Time | Phase |
|---|---|
| 0–2 h | Inspect data, rules, template and output requirements |
| 2–5 h | Build Excel ingestion and normalized data model |
| 5–11 h | Implement allocation constraints |
| 11–15 h | Export template, reports, TQs and utilization |
| 15–19 h | Add revision comparison and stability objectives |
| 19–22 h | Test new tags, changed headers, contradictions and capacity shortages |
| 22–24 h | Integrate, freeze, rehearse demo and prepare Q&A |

This is an illustrative plan, not an official hackathon duration. Inspect the real files before committing to a model.

---

## 8. 🤖 AI-Buildability Split (20/80)

The split is a planning heuristic, not a measured statistic.

### The 20% AI can accelerate

- Generate UI screens, forms, tables and visualization scaffolding.
- Draft pandas parsing, Excel export utilities and API endpoints.
- Generate test skeletons, documentation and error messages.

### The 80% the team must understand

| Responsibility | Why human understanding matters |
|---|---|
| Formalize engineering rules | Ambiguous rules can become incorrect constraints |
| Model cable continuity and pair order | Valid signal assignments must also reflect physical wiring |
| Separate hard constraints from preferences | Mandatory compliance cannot be traded for convenience |
| Diagnose infeasibility | Bad data, conflicting rules and insufficient capacity differ |
| Optimize revisions | Old placements may conflict with new requirements |
| Validate export | Solver success does not prove all requirements were modelled |
| Explain decisions | Engineers need traceable placements and TQs |

### Live-change challenge

A judge asks: “Add a rule that all signals in Group G3 must remain in the same cabinet, then rerun allocation without rewriting your code.”

A good architecture lets the user add a structured rule, converts it to a solver constraint, reruns allocation and validates the result. If the new rule makes the model infeasible, the system must report that rather than silently ignoring it.

A second challenge is uploading Rev B with 50 new signals and asking the tool to preserve feasible existing placements while reporting affected cabinets.

---

## 9. 📊 Data & Resource Availability

The problem statement says a sample I/O MDB and output template are provided for hackathon use and says not to share the sample data. Use organizer-provided files as the primary source. Do not upload them to public repositories or external AI services unless explicitly permitted.

| Resource | Status/action |
|---|---|
| Sample I/O MDB | Stated to be provided; inspect locally |
| Output Excel template | Stated to be provided; test exact structure early |
| Rule definitions | Partly specified; encode project-specific settings as configurable data |
| DeltaV hardware mapping | Partly specified; use supplied mapping and clarify ambiguity |
| Additional industrial datasets | Not established; do not depend on finding them |
| OR-Tools | Publicly available; test locally |
| External AI services | Optional; avoid core dependency |

### Suggested normalized signal record

- **Identity:** tag, source file, revision.
- **Electrical data:** I/O type, cable ID, pair number.
- **Grouping:** group, segment, A/B segregation.
- **Hardware:** required CHARM and terminal block.
- **Allocation:** cabinet, CIOC, baseplate and slot.
- **Revision tracking:** previous placement and change status.

Adapt these fields to the actual files. Missing required values should be flagged, not invented.

### Backup if provided data is unavailable

Create clearly labelled synthetic data containing:

- AI/AO/DI/DO signals, including high-current output cases.
- Cables of 24, 12, 6 and 2 pairs.
- Groups G1/G2/G3 and A/B segregation pairs.
- Wired spares, free slots and reserved capacity.
- One missing required field and one conflicting rule.
- Rev B additions, deletions and changed signal properties.

Keep synthetic data separate from the organizer's sample. It supports development but does not prove passing the official hidden test.

---

## 10. 🎤 Judge Q&A Stress-Test

### Q1. How do you guarantee allocation validity?

**Answer:** Mandatory requirements are hard constraints, including capacity, unique slot assignment, compatibility and segregation. After solving, an independent validator checks the allocation. A signal is marked allocated only if its placement passes validation; otherwise, the issue is reported through a TQ or failed-validation result.

**Follow-up:** What if a rule was omitted from the model?  
**Response:** The independent checker and tests cover each specified constraint. No system can enforce an unspecified requirement, so rule completeness is reviewed explicitly.

### Q2. How do you prevent unnecessary movement in Rev B?

**Answer:** We match signals using stable identifiers and treat previous placements as preferences. The objective minimizes changed placements while satisfying new hard constraints. If capacity or new requirements make an old placement invalid, we move only what is necessary and report the impact.

**Follow-up:** How do you prove that?  
**Response:** Show counts of moved, added, deleted and unchanged signals. Stable identity matching is separate from feasibility constraints.

### Q3. What if rules contradict each other or capacity is insufficient?

**Answer:** We distinguish input-validation failures from allocation infeasibility. Missing I/O type produces a data TQ; incompatible hardware produces a compatibility issue; insufficient capacity produces a capacity issue. We identify affected records where possible and never fabricate an allocation.

**Follow-up:** Can you identify the exact minimal conflicting rule set?  
**Response:** Claim this only if implemented. Otherwise, report the conflict category and affected records honestly.

### Q4. Why use a constraint solver instead of a greedy algorithm?

**Answer:** Greedy placement can block a later, more constrained signal. A constraint solver models interdependent rules and optimizes objectives such as cabinet count or revision stability. We will benchmark runtime and validate results on the actual sample rather than promise performance without measurements.

**Follow-up:** Can it handle 10,000+ signals?  
**Response:** Show measured runtime, completeness and validation results. If the full model is too slow, explain the fallback and prioritization of objectives.

### Q5. What is innovative if commercial engineering tools already exist?

**Answer:** Our contribution is an integrated workflow for configurable allocation rules, template generation, actionable TQs and revision-aware placement optimization. We do not claim to replace a complete electrical design suite. We will demonstrate the workflow and compare it with a measured baseline.

**Follow-up:** How do you prove superiority?  
**Response:** Measure processing time, rule violations, TQ detection and signals moved. Do not claim superiority without a fair benchmark.

### Weakest point a sharp judge may target

**Does the engine enforce real physical constraints—especially cable continuity and pair ordering—or does it merely fill free slots?**

Demonstrate:
1. A cable with multiple pairs.
2. Assigned baseplates and consecutive slot positions.
3. Signal pairs versus wired spare pairs.
4. A constraint that prevents the original placement.
5. A valid reallocation or a TQ when no valid placement exists.

A working demonstration is stronger than a promise.

---

## 🏁 Final Verdict

> 🟢 **GREEN LIGHT — Strong hackathon opportunity.**
>
> **Single biggest reason:** The problem has defined inputs, engineering constraints and measurable outputs, so a team can demonstrate a real, testable solution rather than just an AI concept.

### What will make or break the submission?

1. Get the allocation engine right: capacity, compatibility, continuity and segregation.
2. Complete the workflow: Excel in, validated allocation out, with TQs and reports.
3. Make revision handling a differentiator: preserve feasible placements and explain necessary moves.
4. Prove it with supplied and difficult synthetic test cases.
5. Use AI strategically without compromising deterministic correctness.

### Immediate next step

Inspect the actual sample MDB and output template. Write a formal rule checklist, then build a small Python prototype that allocates a few cables correctly, validates the result and exports the required format. Scale it to the full dataset before investing heavily in the UI.

**Final caution:** The green light applies to the opportunity, not the technical readiness of an implementation. The hardest part is turning written rules into a correct allocation model—and that is where the team should focus first.

---

## References

- [Emerson Automation Systems / DeltaV](https://www.emerson.com/en-us/automation-systems)
- [AutoCAD Electrical](https://www.autodesk.com/products/autocad/included-toolsets/autocad-electrical)
- [EPLAN](https://www.eplan.com/)
- [Google OR-Tools](https://developers.google.com/optimization)
- [OR-Tools CP-SAT documentation](https://developers.google.com/optimization/cp/cp_solver/)
- [ISA-5 standards series](https://www.isa.org/standards-and-publications/isa-standards/isa-5-standard)

**Evidence note:** The organizer's problem statement is the basis for the described requirements and deliverables. Competitor descriptions and implementation recommendations are contextual analysis, not claims that the listed vendors provide or lack a particular exact feature.
