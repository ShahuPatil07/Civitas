# Unnamed composition experiment

## What the task is

**Raise a 10 kg load by at least 1 metre, using environmental energy, with zero
direct human work on the load and no more than 100 J of total human effort.**

There are three unconnected physical bodies, described only by their material
properties, mass, position, dimensions and affordances. One exposes an anchored,
finite environmental power supply. Nothing is a named invention. The scenario
does not specify a relation graph, construction procedure or expected answer.
The source and load are separated enough that directly connecting them cannot
meet the kernel's reach limit.

This is a small assembly calibration: can an agent search for relationships,
encounter failure, revise a candidate, do useful work and persist evidence?
Manufacturing the supplied components is outside this particular task. The
kernel, materials, physics, affordances and original four benchmarks are frozen.

## Experimental design

Three cases use the same solver and outcome constraints:

| Case | Difference from calibration | Purpose |
| --- | --- | --- |
| Feasible | Gravity 9.81 m/s², source energy 1000 J | Find a functional composition |
| Insufficient-energy control | Source energy reduced to 50 J | Check that search cannot invent energy or declare success |
| Gravity transfer | Gravity increased to 12 m/s² | Test the same policy with changed physical requirements |

The negative control is impossible within this model: at least 98.1 J must reach
the load, its only environmental reservoir holds 50 J, transmission cannot create
energy, and direct human work on the load must remain zero. This argument is
independent of the solver's failure. The solver itself does not claim to prove
impossibility when its bounded search finishes.

These scenarios are public and were implemented alongside the solver. They are
**not independent hidden tests**. Transfer reruns the policy with fresh
observations; it does not yet reuse a design learned in another world.

## Solver and authority

`civitas/composition.py` receives only `view()` and `submit()` plus public numeric
goals and budgets. It has no world snapshot, private evaluator, physics oracle,
world clone or reset operation. It enumerates property-compatible paths of two
or three observed objects using force or rotation relations. Its first positional
goal determines the requested displacement. All candidates are tested through
ordinary authoritative actions.

When a work attempt returns `unsupported_load`, it enumerates observed objects
offering support and revises the candidate with a load-bearing relation. This is
an explicit generic planning heuristic, not a discovered physical law. There is
no scenario-name, material-label or specific component-ID branch.

Before a trial, the solver records a structured Design containing components,
relationships, constraints and proposed primitive actions. Component keys bind
directly to observed persistent IDs. It submits the missing connections and
motion, then measures the task constraints with an Experiment referencing that
design. A child Design records measured evidence and accumulated failure modes.
Existing successful connections are retained across trials and omitted from
resubmission; all spent resources remain spent. The persisted full procedure
includes those connections so the assembled state can be inspected.

Records are still hypotheses. Failure descriptions are solver interpretations;
the causal action journal and kernel-produced experiment measurements provide
the authoritative evidence. This does not add a universal design compiler or
automatic attribution of performance to a graph.

## Reproduce and inspect

```console
python -m benchmarks.composition.run --seed 42
python -m civitas replay runs/composition/feasible-composition.json
python -m unittest discover -v
```

The runner compares the original baseline and new composition solver for all
three cases. It saves complete replayable runs, human-readable traces and a
summary under `runs/composition/`. `--output` selects another folder. The original
four-benchmark suite is unchanged. The general CLI also accepts `--solver
composition` on those benchmarks, but this experiment makes no claim to solve
all four.

## Seed-42 results

| Case | Original baseline | Composition search | Search actions | Experiments | Design versions |
| --- | --- | --- | ---: | ---: | ---: |
| Feasible | Failed | Passed | 20 | 4 | 8 |
| Insufficient energy | Failed | Correctly failed | 21 | 4 | 8 |
| Gravity transfer | Failed | Passed | 24 | 5 | 10 |

All six saved runs replay exactly. The feasible trace shows rejected direct
connections, a rejected unsupported motion, a revised composition, and finally
a successful raise. It delivers 98.1 J while debiting approximately 121.111 J
from the source (two transmission losses). Human effort totals 20 J for
connections, actuation and measurements; direct human work on the load is 0 J.
The higher-gravity case delivers 120 J instead. The insufficient-energy control
leaves the load at ground level and never receives a successful experiment.

The full correctness suite passes **51 tests** (42 existing and 9 added for this
experiment). Original seed-42 benchmark state hashes remain identical, confirming
that the new search did not improve its scores by changing physical rules or the
old baseline.

Reference results are in
[`benchmarks/composition/results/summary.json`](../benchmarks/composition/results/summary.json).
Full JSON runs remain local because the event journal stores verbose state
effects. Tests also check replay, design lineage, scoped evidence, budgets,
renamed inputs, and unchanged hashes for all original baseline reference runs.

## Limits and next question

The search is bounded and deliberately biased toward transmission paths and
support for a positional goal. It uses a fixed 10 s motion duration, only the
first eligible positional goal, already-made bodies, and paths of at most three
objects. It does not search arbitrary programs, geometry, manufacturing,
disassembly, repeated cycles or parallel load sharing. Persistent ID bindings
are local to one world; portable design parameterization and copying remain
unimplemented. Accepted connections can constrain later trials because there is
no undo. The environmental supply is already mechanical power.

This result establishes a small **propose → construct → fail → revise → measure
→ persist** loop using existing primitives. It is not evidence of general
invention or a completed Unseen Object Test. The next question is whether a
frozen policy can reuse a parameterized design on independently prepared tasks
without privileged observations. That work is not started by this experiment.
