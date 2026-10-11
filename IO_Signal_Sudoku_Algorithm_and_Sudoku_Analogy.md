🧩 How the "Sudoku" Analogy Prepares the Algorithm The analogy works
because both problems are constraint-satisfaction problems (CSPs): you
must fill empty slots such that every local rule is satisfied, no slot
is used twice, and---ideally--- the result is compact and stable. The PS
itself says no DCS background is needed and explicitly frames it as a
constraint-packing puzzle. \[1\]

1.  Sudoku ↔ IO Allocation Mapping 🔄 Sudoku concept IO Signal Sudoku
    equivalent

              9 × 9 grid                     Cabinets → CIOCs → baseplates → 12 CHARM slots

              Cell                           One CHARM slot

              Digit 1–9                      One field signal

              Row/column/box constraints     Capacity, grouping, A/B segregation, cable continuity

              “No repeated digit in a row”   “No two signals in one CHARM slot”

              “No repeated digit in a box”   “A and B signals cannot share a CIOC”; group/cable placement rules

              Pre-filled clues               Already-known signals, fixed cables, customer rules

              Empty cells                    Available CHARM slots

              Solver backtracking            CP-SAT search

              Sudoku solution                Complete allocation: signal → cabinet → CIOC → baseplate → CHARM

In this PS, the physical capacity is fixed: 12 CHARMs per baseplate, 8
baseplates per CIOC, and 4 CIOCs per cabinet. So a cabinet is like a
large Sudoku board with CHARM slots. \[1\]

2.  Why Plain Sudoku Logic Is Not Enough ⚠️ Normal Sudoku places one
    independent digit per cell. Here, signals arrive in cables, and
    cables must stay together: A 24-pair cable fills exactly two
    baseplates: 22 signals plus 2 wired spare pairs. \[1\] A 12-pair
    cable occupies one full baseplate. 6- and 2-pair cables occupy
    smaller contiguous blocks. Pair order must be preserved.

------------------------------------------------------------------------

So the real unit being placed is often not one signal, but a cable
block. Think of it as Sudoku where some numbers are glued together into
tetromino-like blocks and must occupy adjacent cells in order.

Example A 24-pair cable is like a rigid block:

Baseplate 1: pairs 1--12 Baseplate 2: pairs 13--22 + 2 wired spares

You cannot place pair 1 in one cabinet and pair 12 in another; the whole
cable block must be placed contiguously. \[1\]

3.  The Rules Become Constraints 📏 Each Sudoku rule becomes a formal
    constraint:

            Project rule             Constraint type                               Algorithmic meaning

One signal per CHARM All-different Each CHARM slot has at most one
signal

12 CHARMs/baseplate Capacity A baseplate can accept at most 12 signal
slots

8 baseplates/CIOC, 4 Hierarchy capacity Limits how many blocks fit in a
container CIOCs/cabinet

                                                          Signals with the same Grp should occupy the same cabinet and

Same IO group stays together Grouping remain in sequence

A and B never share a CIOC Segregation If signal has A, no B signal may
be assigned to that CIOC

                                                          A cable block occupies adjacent CHARM slots/baseplates in pair

Cable stays together Contiguity order

Leave spare room Reservation Keep some baseplates/slots empty per
cabinet

                                                          An AI signal can only use an AI-compatible CHARM; DO-SOV needs

Correct CHARM/TB Domain restriction isolated fused CHARM, etc.

                                 Deterministic

Naming patterns After allocation, generate names from templates
generation

The PS defines these as user-editable rules, including grouping, A/B
separation, capacity, cable continuity, spare percentage,
CHARM/terminal-block mapping, and naming. \[1\]

4.  Algorithm Choice: Constraint Programming 🧠 Use Google OR-Tools
    CP-SAT, not a greedy algorithm and not an LLM.

------------------------------------------------------------------------

Why CP-SAT? It naturally handles integer/binary assignment variables. It
enforces hard constraints exactly. It can optimize secondary goals, such
as fewer cabinets, less fragmentation, or fewer revision moves. It can
prove infeasibility and help generate a meaningful TQ. CP-SAT is
designed for integer programming and constraint problems, making it
appropriate for this slot-packing task. \[2\] A greedy "first-fit"
approach may allocate the first few cables quickly but can later make
A/B segregation or spare-capacity rules impossible. CP-SAT looks
globally for a feasible assignment.

5.  Core Algorithm 🧮

High-level algorithm

INPUT: IO MDB Excel file(s) IO allocation Excel template User-defined
rule set

OUTPUT: Filled allocation Excel TQ list Rule-check report Cabinet/CIOC
utilization report Revision impact report, if Rev B is provided

Step-by-step

1.  INGEST DATA
    a.  Read every Excel row as one Signal.
    b.  Auto-map columns: Tag, IO, Cable, Pair, Grp, Seg.
    c.  Normalize IO types, cable IDs, pair numbers, groups, and
        segregation labels.
    d.  Build Signal, Cable, IOGroup, and SegregationClass objects.
2.  VALIDATE INPUT
    a.  Check missing tag / IO type / cable / pair.
    b.  Check duplicate tag or duplicate cable-pair.
    c.  Check pair number against cable size.
    d.  Check whether a cable has more signals than its declared pair
        count.
    e.  Check invalid IO type or invalid A/B value.
    f.  Create a TQ for every unresolvable issue.
3.  BUILD CABLE BLOCKS
    a.  Group signals by Cable ID.
    b.  Sort each cable by Pair number.
    c.  Create a CableBlock for each cable.

------------------------------------------------------------------------

d.  Calculate block size: 24-pair cable → 2 full baseplates 12-pair
    cable → 1 full baseplate 6-pair cable → half baseplate 2-pair cable
    → one-sixth baseplate
e.  Preserve pair order inside every block.

```{=html}
<!-- -->
```
4.  LOAD RULES
    a.  Read enabled rules from JSON/YAML.
    b.  Extract:
        -   grouping scope
        -   A/B separation level
        -   spare policy
        -   CHARM/TB mapping
        -   naming templates
        -   revision stability weight, if applicable
    c.  Validate rule conflicts.
5.  CREATE DECISION VARIABLES For every CableBlock B:
    assign\[B\]\[cabinet\]\[cioc\]\[baseplate_start\] ∈ {0,1}

For every Signal S: signal_slot\[S\]\[charm_slot\] ∈ {0,1}

The cable-block variable decides where the whole cable lands; signal
variables then inherit positions from that block.

6.  ADD HARD CONSTRAINTS
    a.  Each CableBlock is assigned exactly once.
    b.  A baseplate cannot exceed 12 CHARM slots.
    c.  A CIOC cannot exceed 8 baseplates.
    d.  A cabinet cannot exceed 4 CIOCs.
    e.  Cable pairs remain contiguous and ordered.
    f.  A and B blocks cannot be placed under the same CIOC.
    g.  Same IO group remains in the same cabinet; preferably in
        sequence.
    h.  CHARM type and terminal block must match signal IO type.
    i.  Reserve spare baseplates/slots according to the spare rule.
7.  ADD SOFT OBJECTIVES Minimize: α × number_of_cabinets_used
    -   β × fragmentation
    -   γ × revision_movement
    -   δ × group_sequence_penalty

For a fresh allocation: prioritize fewer cabinets and clean grouping.

For a revision: heavily penalize moving unchanged signals.

8.  SOLVE Run CP-SAT with a time limit. If feasible: extract every
    signal's cabinet, CIOC, baseplate, and CHARM.

------------------------------------------------------------------------

     If infeasible:
         identify the smallest conflicting set and raise TQs.

9.  POST-PROCESS

    a.  Generate cabinet, CIOC, baseplate, and CHARM names.
    b.  Assign CHARM and terminal-block types.
    c.  Run an independent rule checker.
    d.  Calculate cabinet fill percentage and spare capacity.
    e.  Export the provided Excel template.

10. REVISION MODE a. Load Rev A allocation snapshot. b. Match Rev B
    signals to Rev A using: tag + cable + pair + IO type c. Mark signals
    as unchanged, added, deleted, or modified. d. Freeze valid unchanged
    allocations. e. Re-run CP-SAT only for added/modified/displaced
    signals. f. Produce impact report: added, deleted, moved, affected
    cabinets, new TQs.

11. Mathematical Formulation 📐

Decision variable For each cable block , candidate starting baseplate ,
and cabinet :

means cable block starts at baseplate inside cabinet .

Basic assignment constraint Every cable must be placed exactly once:

Capacity constraint For every baseplate :

Where indicates that cable block occupies baseplate .

------------------------------------------------------------------------

A/B segregation constraint For every CIOC :

More precisely, if any A-class cable block is assigned to CIOC , then no
B-class cable block may be assigned to , and vice versa.

Objective

For a revision, should dominate so unchanged signals remain in place, as
required by the PS. \[1\]

7.  Simplified Pseudocode 💻

    def allocate_io_signals(io_rows, rules, previous_allocation=None):
    \# 1. Validate signals = normalize_signals(io_rows) tq_list =
    validate_signals(signals, rules)

          # 2. Build cable blocks
          cables = group_by_cable(signals)
          cable_blocks = []
          for cable_id, cable_signals in cables.items():
              cable_signals.sort(key=lambda s: s.pair_no)
              block = CableBlock(
                  cable_id=cable_id,
                  signals=cable_signals,
                  size=len(cable_signals),
                  required_baseplates=calculate_baseplates(cable_signals)
              )
              cable_blocks.append(block)

          # 3. Create CP-SAT model
          model = cp_model.CpModel()

          # x[(block, cabinet, cioc, baseplate_start)] = 1 if block starts there
          x = {}
          for block in cable_blocks:
              for cabinet in available_cabinets:
                  for cioc in cabinet.ciocs:
                      for baseplate in cioc.baseplates:
                          if fits(block, baseplate, rules):
                              x[block.id, cabinet.id, cioc.id, baseplate.id] = model.NewBoo
                                  f"x_{block.id}_{cabinet.id}_{cioc.id}_{baseplate.id}"
                              )

           # 4. Each block placed exactly once
           for block in cable_blocks:
               model.AddExactlyOne(

------------------------------------------------------------------------

       v for key, v in x.items() if key[^0] == block.id

)

# 5. Capacity: max 12 CHARM slots per baseplate

for baseplate in all_baseplates: occupied = \[\] for block in
cable_blocks: for key, var in x.items(): if key\[\^3\] == baseplate.id
and overlaps(key\[\^3\], block, baseplate): occupied.append(var \*
block.size) model.Add(sum(occupied) \<= 12)

# 6. A/B segregation at CIOC level

for cioc in all_ciocs: a_blocks = blocks_with_segregation("A") b_blocks
= blocks_with_segregation("B")

    for a in a_blocks:
        for b in b_blocks:
            a_here = get_assignment_var(x, a, cioc)
            b_here = get_assignment_var(x, b, cioc)
            model.Add(a_here + b_here <= 1)

# 7. Group cohesion

for group_id, blocks in group_blocks_by_io_group(blocks):
enforce_same_cabinet(model, x, blocks, rules)
enforce_sequence_preference(model, x, blocks)

# 8. Spare capacity

for cabinet in available_cabinets: model.Add( used_baseplates(cabinet)
\<= max_baseplates(cabinet) - rules.spare_baseplates )

# 9. Revision stability

if previous_allocation: for block in cable_blocks: old_location =
previous_allocation.get(block.cable_id) if old_location and
block.is_unchanged: move_penalty =
model.NewBoolVar(f"moved\_{block.id}") model.Add(move_penalty ==
0).OnlyEnforceIf( stays_at_old_location(x, block, old_location) )
model.Add(move_penalty == 1).OnlyEnforceIf( moves_from_old_location(x,
block, old_location) ) objective_terms.append(rules.revision_weight \*
move_penalty)

# 10. Objective

model.Minimize(sum(objective_terms))

# 11. Solve

solver = cp_model.CpSolver() solver.parameters.max_time_in_seconds = 60
status = solver.Solve(model)

------------------------------------------------------------------------

      if status not in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
          return generate_infeasibility_tqs(model, cable_blocks, rules)

      # 12. Extract allocation
      allocation = extract_allocation(solver, x, cable_blocks)
      allocation = apply_naming_rules(allocation, rules)
      allocation = assign_charm_and_terminal_blocks(allocation, rules)

      # 13. Final compliance check
      violations, final_tqs = check_all_rules(allocation, rules)
      tq_list.extend(final_tqs)

      return allocation, tq_list, violations

8.  Important Implementation Detail: Allocate Cables, Not Signals ⚡ If
    you create a separate variable for every one of 10,000+ signals, the
    model becomes unnecessarily large and may become slow. Instead:

Cable block → assigned to baseplate range ↓ Signals inherit slots from
cable block ↓ CHARM/TB type assigned per signal IO type

This preserves cable continuity automatically and dramatically reduces
the search space.

Example

CBL-101: 24-pair cable

Placement decision: CBL-101 → Cabinet MC-01 → CIOC-1 → Baseplates CBP-1
and CBP-2

Derived assignments: Pair 1 → CBP-1 / CHARM 1 Pair 2 → CBP-1 / CHARM 2
... Pair 12 → CBP-1 / CHARM 12 Pair 13 → CBP-2 / CHARM 1 ... Pair 22 →
CBP-2 / CHARM 10 Pair 23 → wired spare Pair 24 → wired spare

This matches the PS example where a 24-pair cable fills two baseplates,
with 22 signal pairs and two wired spare pairs. \[1\]

------------------------------------------------------------------------

9.  Handling Infeasibility and TQs 🚨 Sudoku has a clean answer or no
    answer. Industrial allocation needs a useful partial answer. When
    CP-SAT cannot place something:

                    Issue                                                        TQ generated

    Missing cable ID or pair number "Signal X cannot be allocated:
    missing cable/pair data."

Duplicate tag "Duplicate tag detected; confirm whether this is a
revision or data error."

A and B must share one CIOC due to "A/B segregation cannot be satisfied
with current cabinet/spare policy." capacity

Cable larger than available contiguous "Cable CBL-105 cannot be placed
contiguously; increase cabinet capacity or revise space spare policy."

IO type has no compatible CHARM "No CHARM mapping defined for IO type
X."

Group too large for one cabinet "IO group G1 exceeds cabinet capacity
under current rules."

The PS requires a TQ for anything the tool cannot place, plus a
rule-check report and capacity/conflict reporting. \[1\]

10. Revision Mode: Sudoku With Memory 🔁 A normal Sudoku restarts from
    scratch. Your revision solver should not.

Rev A: Signal S1 → MC-01 / CIOC-1 / CBP-1 / CHARM-3

Rev B: S1 still exists, same cable/pair/IO type.

Decision: Keep S1 exactly where it is, unless doing so violates a new
rule or makes the revised allocation infeasible.

Algorithm:

1.  Load Rev A allocation.
2.  Match Rev B signals to Rev A.
3.  Keep unchanged signals fixed.
4.  Remove deleted signals and free their slots.
5.  Allocate added/modified signals.
6.  If fixed placements create infeasibility: progressively unfreeze the
    minimum number of signals.
7.  Report every forced move.

This directly implements the PS requirement that unchanged signals stay
in place with the fewest moves. \[1\]

------------------------------------------------------------------------

✅ Key Takeaway

Treat the problem as: A constrained block-packing Sudoku, where cable
blocks---not individual signals---are the main pieces, CIOCs act as
segregation zones, baseplates act as capacity rows, and CHARM slots are
the individual cells. Use CP-SAT to enforce the hard engineering rules
and optimize cabinet usage, fragmentation, and revision movement. Use
greedy placement only as a fast heuristic or fallback---not as the final
allocation engine. \[2\] ⁂

1.  ilovepdf_merged.pdf
2.  https://developers.google.com/optimization/cp/cp_solver

------------------------------------------------------------------------
