# Outcome-based invention tests

The four JSON files in `benchmarks/` are public research tasks, not authored
solutions. `civitas.benchmarks.instantiate` builds a validated genesis; `outcome`
evaluates all goal constraints against kernel truth. Solver code never sees the
genesis or evaluator. The baseline receives only a public task plus `AgentPort`.

## Scenario contract

Each scenario defines `id`, `description`, `seed`, `universe`, `stocks`, `objects`,
`agent`, `goals`, `allowed_actions`, `max_actions` and `max_experiments`. Optional
`materials` replaces the catalog with property records keyed by UUID. Material
labels in scenario input are resolved to IDs at initialization; laws do not branch
on those labels. Positions are `[x, z]` in metres; initial objects must be grounded.
Five agents are initialized, with stock and initial shaping knowledge given only
to the focal agent. Other agents have no active policy in v0.

An object's data is `material`, `mass` (kg), `length` (m), `radius` (effective motion
radius, m) and `position`. An optional anchored `source` has `energy` (J), `power`
(W) and `max_force` (N). This is an environmental boundary condition, not an
energy-harvesting mechanism. Do not claim that v0 derives energy conversion from
an unmodeled environment.

Goals are a nonempty conjunction of records:

```json
{"category":"physical", "subject":"load", "measure":"z", "op":">=", "value":2}
```

`subject` is an initial object symbol or `agent`; initialization resolves it to a
UUID. Comparators are `>=`, `<=`, `==`. Physical measures include `x`, `z`, `mass`,
`length`, `radius`, `section`, `volume`, `tension_capacity`, `compression_capacity`,
`friction`, `angle`, `human_work`, `environment_work`, `bearing_span`,
`supported_span`, `supported_load` and `crossings`. Span/load measurements count
actually elevated supported loads, not unused connections. `crossings` takes
`parameters: {"lower": 0, "upper": 2}` and counts completed upward traversals
with a return to the lower boundary required to rearm. Small upward increments
cannot inflate repetition counts.

Resource measures include agent `energy`, total `effort_spent`, source `energy`
and `stock_mass` with `parameters: {"material": "<UUID>"}`. Material UUIDs are
stable catalog definition IDs. Knowledge `known` takes `parameters: {"claim":
"..."}` and measures whether the agent holds a claim, not whether it is true.
Unimplemented measures/categories return `unknown`; they never satisfy a goal.
Category placeholders are manufacturing, economic, social and institutional.

Success means **every goal satisfied and both budgets respected**. Each submitted
JSON action consumes an attempt even if rejected. Rejected experiments also
consume the experiment budget. Physical rejection consumes no world time/energy.
Malformed non-JSON input is rejected before an action exists. Direct trusted
researcher submissions may exceed budgets, but the evaluator then fails the run.

## Public categories

| Scenario | Desired measured outcome | Generalization pressure |
| --- | --- | --- |
| mechanical | Two complete load raises powered by environmental work | Repetition, support, force and energy |
| transportation | Heavy load displacement under a total effort budget | Friction, bounded work and efficient construction |
| structural | Elevated load with a measured horizontal bearing span | Strength, reach and limited stock |
| novel_environment | Elevated load under altered gravity and an effort bound | Consequences of changed universe rules |

These are semantic calibration tasks, not adequate evidence for open-ended
invention by themselves. The environmental tasks start with mechanical boundary
power already available; uniform terrain and scalar paths are simplifications.
Different action graphs/material choices can satisfy the same measurements.
Unit tests demonstrate two distinct ways to satisfy a separate displacement
calibration goal without providing a solution to these research tasks.

## Add a public or hidden test

1. Specify the outcome numerically and list permitted observations and resources.
   Avoid prescribed components, relation graphs, steps or expected answer labels.
2. Copy only the scenario schema, not a solution. Change properties, stocks,
   geometry, knowledge and environmental parameters to test transfer.
3. Check units and genesis validation. For a new measure, implement a general
   measurement with positive and negative calibration tests outside the scenario.
4. Verify all constraints start with the intended status. Include an impossible
   control, and check that resource overrun or `unknown` cannot pass.
5. Save a complete run and replay the saved file. Inspect failures and energy
   accounting before drawing conclusions from a success count.
6. For hidden tests, keep scenario data outside the solver's source/context and
   call `instantiate` from a trusted evaluator. Give the solver the public task
   only. Future hostile/untrusted solvers require a separate process; Python
   encapsulation and withholding a reference are not access-control security.
7. Freeze the rule version and baseline before revealing a held-out task. If a
   missing primitive is discovered, justify it with unrelated tasks and designate
   a fresh holdout. Do not keep calling a revealed scenario hidden.

The current evaluator supports conjunctions over identified subjects; it does
not yet support quantified goals over arbitrary new assemblies. Use a named
initial load as the outcome subject, without constraining the artifact that acts
on it. This restriction should be revisited before richer invention benchmarks.

## Reproduce the baseline

```console
python -m benchmarks.run_baseline --seed 42
python -m civitas replay runs/baseline-42/mechanical.json
```

Runs contain genesis, full scenario, seed, public task, all actions and events,
final digest and evaluator outcome. They are researcher artifacts and can contain
truth unavailable to the actor. Never feed a whole run back into a reasoning
model; use its restricted observations and submitted-action feedback instead.
