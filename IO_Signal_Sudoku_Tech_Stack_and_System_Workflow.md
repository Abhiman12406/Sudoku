🛠️Tech Stack & System Workflow --- IO Signal Sudoku Build a Python web
application with a deterministic CP-SAT allocation core, Excel-native
input/output, configurable rules, and revision-aware impact analysis.
The PS requires Excel in → rules applied → Excel out, with no
hand-editing and no code change for new rules or unseen IO MDBs. \[1\]

1.  Recommended Tech Stack ⚙️

Core stack Layer Technology Why Explicitly preferred by the PS; strong
Excel, data, and optimization Language Python 3.11+ ecosystem. \[1\]

UI Streamlit Fastest route to upload, rule panel, results, and live demo

Data processing pandas, Polars Read, validate, transform, and compare
large signal tables

Excel I/O openpyxl, xlsxwriter Preserve/fill the provided allocation
template and generate reports

Constraint Ideal for capacity, no-overlap, grouping, segregation, and
placement Google OR-Tools CP-SAT engine constraints

Rule storage JSON/YAML Portable, editable project rule sets; supports
save/reuse per project

                                                   Strong schema validation for signals, rules, and generated

Validation Pydantic allocations

                    Plotly or Streamlit native

Visualization Cabinet fill, spare capacity, revision impact charts

                    OpenAI / Gemini API or local   Column mapping suggestions, rule drafting, TQ explanations—not

Optional AI LLM allocation

                    Docker +

Packaging Reproducible demo and easy evaluator setup requirements.txt

Google OR-Tools CP-SAT is designed for integer and
constraint-programming problems and is a strong fit for this
slot-packing optimization. \[2\]

------------------------------------------------------------------------

Why not an LLM for allocation? Use AI only around the edges. The core
must be deterministic because the definition of done demands zero
violations, correct CHARM/terminal-block selection, and complete
allocation or an explanatory TQ. \[1\]

2.  System Architecture 🏗️

┌─────────────────────────────────────────────────────────────┐ │
Streamlit Web UI │ │ Upload │ Column Mapping │ Rule Panel │ Run │
Reports │ Rev │
└───────────────────────────┬─────────────────────────────────┘ │
┌───────────────────────────▼─────────────────────────────────┐ │
Application API Layer │ │ FastAPI routes / service orchestration │
└───────┬───────────────┬───────────────┬─────────────────────┘ │ │ │
┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼──────────────┐ │ Ingestion & │
│ Rule Engine │ │ Allocation Engine │ │ Validation │ │ Config Store │ │
OR-Tools CP-SAT │ └───────┬──────┘ └──────┬───────┘
└─────┬──────────────┘ │ │ │ └───────────────┼───────────────┘ │
┌───────────────────────▼─────────────────────────────────────┐ │
Results & Compliance Layer │ │ Allocation Store │ TQ Generator │ Rule
Checker │ Reports │
└───────────────────────┬─────────────────────────────────────┘ │
┌───────────────────────▼─────────────────────────────────────┐ │ Export
Layer │ │ Filled Excel Template │ TQ Report │ Cabinet Summary │ Diff │
└──────────────────────────────────────────────────────────────┘

3.  Data Model 📦

Input entities Entity Key fields Purpose

                      tag, io_type, cable_id, pair_no, io_group,

Signal One row = one signal segregation, description

                      cable_id, pair_count (24/12/6/2),            Cable must remain contiguous

Cable signal_ids and in pair order

                                                                   Logical grouping must stay within

IOGroup group_id, signal_ids cabinets/in sequence

SegregationClass A, B, or none A and B must not share a CIOC

------------------------------------------------------------------------

           Entity                         Key fields                             Purpose

Cabinet cabinet_id, cioc_ids, spare_policy Physical capacity container

CIOC cioc_id, baseplate_ids Max 4 CIOCs per cabinet

Baseplate baseplate_id, charm_slots\[\^12\] Max 8 baseplates per CIOC

                        slot_no, charm_type, terminal_block,

CHARM One signal per CHARM assigned_signal

                        rule_id, type, parameters, enabled,

Rule User-defined and reusable priority

                        tq_id, signal/cable/group, issue_type,       Unresolvable data or constraint

TQ message, severity conflict

The PS defines the physical hierarchy as: 12 CHARMs per baseplate, 8
baseplates per CIOC, 4 CIOCs per cabinet, with cables arriving as 24-,
12-, 6-, or 2-pair blocks. \[1\]

4.  Rule Engine Design 🧠

Rule schema example

{ "rule_set_name": "Project_AR1_Default", "rules": \[ { "id":
"R1_GROUP_COHESION", "type": "group_cohesion", "enabled": true,
"params": { "scope": "cabinet", "preserve_sequence": true } }, { "id":
"R2_AB_SEPARATION", "type": "segregation", "enabled": true, "params": {
"classes": \["A", "B"\], "separation_level": "cioc" } }, { "id":
"R3_CABLE_CONTINUITY", "type": "cable_continuity", "enabled": true,
"params": { "maintain_pair_order": true, "allow_split": false } },

------------------------------------------------------------------------

          {
            "id": "R4_SPARE_POLICY",
            "type": "spare_capacity",
            "enabled": true,
            "params": {
              "reserved_baseplates_per_cabinet": 3,
              "mode": "percentage_or_fixed"
            }
          },
          {
            "id": "R5_CHARM_MAPPING",
            "type": "hardware_mapping",
            "enabled": true,
            "params": {
              "AI": {"charm": "AI_HART_RTD", "terminal_block": "standard"},
              "AO": {"charm": "AO", "terminal_block": "standard"},
              "DI": {"charm": "DI", "terminal_block": "standard"},
              "DO-SOV": {"charm": "DO_ISOLATED_FUSED", "terminal_block": "fused_injected_po
              "DO-HORN": {"charm": "DO_ISOLATED_FUSED", "terminal_block": "fused_injected_p
              "DO": {"charm": "DO_HIGH_SIDE", "terminal_block": "standard"},
              "DO-RELAY": {"charm": "DO_HIGH_SIDE", "terminal_block": "relay_output"}
            }
          },
          {
            "id": "R6_NAMING",
            "type": "naming",
            "enabled": true,
            "params": {
              "system_cabinet": "<Area>-DCS-<Unit>-<Seq>",
              "controller": "<Area>CTL<Unit><Seq>",
              "marshalling_cabinet": "<Area>-DCM-<Unit>-<Seq>",
              "cioc": "<Area>CIOC<Unit><Seq>",
              "baseplate": "<CIOC>-CBP-<n>"
            }
          }
      ]

}

The PS specifically requires grouping, A/B separation, capacity, cable
continuity, spare reservation, CHARM/terminal-block mapping, and naming
to be user-editable rather than hard-coded. \[1\]

Rule execution model Rule type Enforcement Group cohesion Hard
constraint or weighted soft constraint

                         A/B segregation    Hard constraint

                         Cable continuity   Hard constraint

                         Capacity           Hard constraint

                         Spare capacity     Hard constraint

------------------------------------------------------------------------

                             Rule type                        Enforcement

                        CHARM/TB mapping       Hard constraint

                        Naming                 Deterministic post-processing

                        Optional preferences   Soft constraints with penalties

5.  End-to-End Workflow 🔄

Stage 1 --- Upload & Ingest 📥 1. User uploads one or more customer IO
MDB Excel files. 2. System detects sheets, headers, and column
candidates. 3. AI/rule-based auto-mapper proposes mappings for Tag, IO,
Cable, Pair, Grp, and Seg. 4. User confirms or corrects the mapping. 5.
System normalizes data into the internal Signal model. Outputs:
normalized signal table, ingestion log, missing-field warnings.

Stage 2 --- Validation & TQ Generation 🚨 Check for: Missing tag, IO
type, cable, or pair number. Duplicate tags or duplicate cable-pair
combinations. Invalid IO types. Pair numbers outside the declared cable
size. Missing group or segregation values where rules require them. A/B
conflicts that make allocation impossible. Output: preliminary TQ list
before allocation begins. The PS requires a TQ for every issue the tool
cannot resolve. \[1\]

Stage 3 --- Rule Configuration 🎛️ 1. User selects or creates a rule set.
2. User enables/disables rules. 3. User edits parameters: spare
percentage, naming patterns, CHARM mapping, grouping scope. 4. System
validates the rule set for conflicts. 5. Rule set is saved as reusable
JSON/YAML.

------------------------------------------------------------------------

Stage 4 --- Allocation 🧩 Run the CP-SAT model: Decision variable

Where signal is assigned to cabinet , baseplate , and CHARM slot . Core
constraints Each signal receives exactly one CHARM slot. Each CHARM slot
receives at most one signal. Cable pairs remain contiguous and ordered.
A and B signals never share a CIOC. Same IO group remains within the
same cabinet and preferably in sequence. Baseplate capacity is 12; CIOC
capacity is 8 baseplates; cabinet capacity is 4 CIOCs. Spare
baseplates/slots respect the project spare policy. CHARM type and
terminal block match the signal's IO type. Objective

For a fresh allocation, prioritize compact cabinet usage and clean
grouping. For a revision, prioritize keeping unchanged signals in their
original slots. \[1\]

Stage 5 --- Post-Processing 🏷️ 1. Generate cabinet, CIOC, baseplate, and
CHARM names from user patterns. 2. Assign CHARM and terminal-block
types. 3. Run an independent rule checker over the final allocation. 4.
Create TQs for any unallocated signal or unresolved conflict. 5. Compute
cabinet count, fill percentage, spare slots, and spare baseplates.

Stage 6 --- Export & Reporting 📤 Generate: Filled IO allocation Excel
template. Rule-check report: zero violations or itemized violations. TQ
workbook/sheet. Cabinet/CIOC utilization and spare summary. Revision
impact report.

------------------------------------------------------------------------

The required output must show every signal's CHARM slot, correct
hardware/naming, zero configured-rule violations, and cabinet fill/spare
details. \[1\]

6.  Revision Workflow 🔁

Rev A allocation (saved JSON) │ ▼ Upload Rev B IO MDB │ ▼ Match signals
by stable key: tag + cable + pair + IO type │ ▼ Classify changes:
┌────────────┬─────────────┬──────────────┬──────────────┐ │ Unchanged │
Added │ Deleted │ Modified │
└────────────┴─────────────┴──────────────┴──────────────┘ │ ▼ Freeze
valid unchanged allocations │ ▼ Re-run CP-SAT only for: added +
modified + displaced signals │ ▼ Generate impact report: added │ deleted
│ moved │ cabinets hit │ new TQs

Revision matching key Use a composite key:

signal_key = normalize(tag) + "\|" + cable_id + "\|" + pair_no + "\|" +
io_type

If the tag changes but cable/pair/IO type remain stable, treat it as a
possible rename and raise a low-severity TQ rather than silently moving
it.

Impact report fields Field Example

                                  Added signals       128

                                  Deleted signals     34

                                  Modified signals    19

                                  Unchanged signals   9,820

------------------------------------------------------------------------

                                              Field                   Example

                                       Signals moved             27

                                       Cabinets affected         6

                                       New TQs                   4

                                       Cabinet fill change       MC-03: 82% → 89%

The PS explicitly expects Rev B comparison, unchanged signals to stay in
place with fewest moves, and an impact report covering added, deleted,
moved, and affected cabinets. \[1\]

7.  Module Breakdown 🧱 Module Responsibility Main libraries

    ingestion/ Excel reading, sheet detection, column mapping,
    normalization pandas, openpyxl

    validation/ Data-quality checks and pre-allocation TQs pandas,
    pydantic

    rules/ Rule schema, validation, persistence, rule evaluation
    pydantic, json/yaml

    allocator/ CP-SAT model, constraints, objective, solver execution
    ortools

    hardware/ CHARM and terminal-block mapping, capacity constants
    Python dataclasses

    naming/ Template-based naming generation jinja2 or custom formatter

    revision/ Rev A/B matching, diffing, movement minimization pandas,
    deepdiff

    reports/ TQs, utilization, compliance, impact reports pandas,
    xlsxwriter

    export/ Fill the exact provided Excel template openpyxl

    ui/ Upload, mapping, rules, run, results, downloads streamlit

8.  API / Service Endpoints 🌐 If using FastAPI behind Streamlit:

                        Endpoint                             Method                         Purpose

                 /api/upload                           POST                     Upload IO MDB and template

                 /api/mapping/suggest                  POST                     Suggest Excel column mappings

                 /api/mapping/confirm                  POST                     Save confirmed mapping

                 /api/rules                            GET/POST/PUT             Create, read, update rule sets

                 /api/validate                         POST                     Run data-quality checks

                 /api/allocate                         POST                     Run CP-SAT allocation

                 /api/report                           GET                      Fetch TQs, utilization, compliance

------------------------------------------------------------------------

                       Endpoint                      Method                           Purpose

              /api/export                      POST                      Generate filled Excel output

              /api/revision/compare            POST                      Compare Rev A and Rev B

              /api/revision/export             POST                      Export revision impact report

For a hackathon, you can initially call these as Python service
functions directly from Streamlit; add FastAPI only if you need a
cleaner demo architecture.

9.  Database & Storage 💾

Hackathon MVP Use file-based storage:

/data /uploads rev_a_io_mdb.xlsx rev_b_io_mdb.xlsx /rules
project_ar1_default.json /allocations rev_a_allocation.json
rev_b_allocation.json /exports rev_b_io_allocation.xlsx
rev_b_tq_report.xlsx rev_b_impact_report.xlsx

If persistence is needed Store Use SQLite Projects, uploaded file
metadata, rule sets, allocation runs

                     JSON files       Full allocation snapshots for fast revision comparison

                     Object storage   Original Excel uploads and generated exports

SQLite is enough for the hackathon; avoid PostgreSQL, Redis, Kafka, or
microservices unless you have spare time.

10. CP-SAT Modeling Strategy 🧮

------------------------------------------------------------------------

Recommended model granularity Do not model each signal independently at
first. Model: 1. Cable blocks as indivisible units. 2. Baseplates as
capacity containers. 3. CIOCs as segregation boundaries. 4. Signals as
assignments within cable blocks. This is crucial because a 24-pair cable
must occupy two full baseplates, while 12-, 6-, and 2-pair cables occupy
proportionally smaller contiguous blocks. \[1\]

Constraint examples Constraint CP-SAT representation

               One signal per CHARM   Sum of assignment variables per slot ≤ 1

               Cable continuity       Cable-block assignment variables, not individual-pair assignments

               A/B separation         For every CIOC, forbid coexistence of A and B

               Group cohesion         Same-group cable blocks share cabinet/CIOC constraints

               Capacity               Fixed slot/baseplate/CIOC/cabinet limits

               Spare reservation      Reserve empty baseplates or slots before optimization

               Revision stability     Penalty variable for changing a previously assigned signal

Solver settings

solver = cp_model.CpSolver() solver.parameters.max_time_in_seconds = 60
solver.parameters.num_search_workers = 8
solver.parameters.log_search_progress = False

Set a time limit and always return either: A complete feasible
allocation, or A partial allocation plus precise TQs. Never return an
unvalidated "best-effort" allocation.

11. UI Workflow 🖥️

------------------------------------------------------------------------

Screen 1 --- Project Setup Create/open project. Upload Rev A and/or Rev
B IO MDB. Upload or select the output template.

Screen 2 --- Column Mapping Show detected headers. Highlight mapped
fields. Allow manual override. Show data-quality warnings.

Screen 3 --- Rule Panel Toggle rules on/off. Edit spare percentage. Edit
naming templates. Edit CHARM/TB mapping. Save rule set.

Screen 4 --- Allocation Dashboard Run button. Solver status and elapsed
time. Signals allocated / TQ'd. Cabinets, CIOCs, baseplates used. Fill
percentage and spare capacity.

Screen 5 --- Results Explorer Filter by cabinet, CIOC, group, cable, IO
type, or TQ. Show signal → cabinet → CIOC → baseplate → CHARM path.
Display reason/TQ for unallocated signals.

Screen 6 --- Revision Impact Side-by-side Rev A vs Rev B. Added,
deleted, modified, moved signals. Cabinets affected. Download impact
report.

------------------------------------------------------------------------

12. Demo Flow for Judges 🎤

13. Upload the provided sample IO MDB.

14. Show automatic column mapping.

15. Open the rule panel and change spare capacity from 10% to 20%.

16. Add or enable a rule, such as SOV signals requiring isolated fused
    CHARMs.

17. Click Allocate.

18. Show the filled Excel template and cabinet utilization.

19. Open the TQ report and explain one unresolved conflict.

20. Upload a Rev B file.

21. Show that most unchanged signals remain in place.

22. Download the revision impact report. This directly demonstrates all
    five required features: upload, rules, allocation, report/TQs, and
    revision comparison. \[1\]

23. Build Order 🚀 Day / Phase Deliverable

                       Phase 1       Excel ingestion, schema, validation, sample-data explorer

                       Phase 2       Rule JSON schema and Streamlit rule panel

                       Phase 3       CP-SAT allocator for small dataset

                       Phase 4       Cable-block modeling, A/B segregation, capacity, spare policy

                       Phase 5       Exact-template Excel export

                       Phase 6       TQ engine and compliance report

                       Phase 7       Revision diff and minimum-movement optimization

                       Phase 8       Cabinet dashboard, polish, synthetic edge-case tests

                       Phase 9       Demo rehearsal with unseen file and live rule change

✅ Key Architecture Decisions

    CP-SAT is the brain; Streamlit is the interface; Excel is the contract.
    Rules are configuration, not code.
    Cables are allocated as blocks, not as independent signals.
    TQs are first-class outputs, not error logs.
    Revision stability is an optimization objective, not an afterthought.
    AI assists mapping and explanation only; it never decides final placement.

------------------------------------------------------------------------

The resulting system will satisfy the PS's core demand: a flexible,
end-to-end tool that allocates thousands of DeltaV signals from
user-defined rules, exports the required Excel output, raises TQs for
conflicts, and handles revisions with minimal movement. \[1\] ⁂

1.  ilovepdf_merged.pdf
2.  https://developers.google.com/optimization/cp/cp_solver
3.  https://www.e2eroshitsolutions.com/ai-cable-scheduling-software-benefits/

------------------------------------------------------------------------
