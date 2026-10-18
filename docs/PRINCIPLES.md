# Implementation checklist

Derived from [AIM.md](../AIM.md). Read that document completely before making
architectural changes.

- [ ] Is this a reusable primitive rather than a named outcome? Can two unrelated
  tasks use it? Would it work for an artifact the developers have never heard of?
- [ ] Does behavior follow numerical properties, relations and constraints rather
  than material labels, invention names, recipes or technology flags?
- [ ] Does every post-genesis change pass through `World.submit`? Include
  knowledge, resource use, experimental evidence and research records.
- [ ] Is proposed data schema-checked? Reject arbitrary fields, nonfinite numbers
  and executable generated code. A design never establishes its own correctness.
- [ ] Does cognition receive only `AgentPort` and the public task? Never pass a
  world snapshot, researcher event effects or hidden evaluator state to a solver.
- [ ] Is the action atomic, with useful structured rejection information? Can
  invalid postconditions leave resources partially spent?
- [ ] Are mass, force, power, energy, time and geometry accounted for in documented
  units? Do shared loads and finite resources obey aggregate limits?
- [ ] Does a change preserve deterministic IDs, traversal order and replay? Change
  the rule version when changing persisted semantics after this initial release.
- [ ] Are unknown and unsatisfied distinguishable? Does unknown fail the benchmark?
- [ ] Is evidence tied to a causal event and a particular agent? Can false or
  conflicting beliefs coexist without changing physical truth?
- [ ] Do tests cover a real invariant, numerical boundary or compositional outcome?
  Include rejection rollback and disk replay when changing transitions.
- [ ] Are benchmark outcomes independent of construction steps and object names?
  Avoid tuning engine rules or baseline sampling to a particular scenario score.
- [ ] Are restrictions and shortcuts written down? Unsupported physics must fail
  visibly rather than silently granting the desired behavior.
- [ ] Is this still a small, headless research environment? Defer society,
  chemistry, rendering, distributed infrastructure and model orchestration.

When a task seems to require an object-specific special case, ask: **What more
general primitive, affordance, relation, constraint or representation is missing?**
Use a separate primitive test and an unrelated transfer task to justify adding it.
