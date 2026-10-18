# CIVITAS v0 architecture

Read `../AIM.md` first. This is a research substrate for the Unseen Object Test,
not an implementation of that milestone's Engineer or a claim of invention.
Python standard library only; no rendering, network, model calls, or executable
generated code. The architecture precedes the implementation.

## Authority and flow

Intent → Plan → Action → validation → staged transition → Event → observation
→ knowledge update. Only `World.submit(Action)` commits authoritative changes.
An action is a closed, schema-checked request, never an arbitrary state patch.
An accepted action produces one atomic event with its effects and evaluations.
A rejected action produces a rejection event, consuming attempt budget but no
physical resources. Time, effort, inventory, physical outcomes, beliefs, recorded
designs and experimental results are all kernel-owned. Genesis is the only
initialization exception and must be validated before use.

The kernel stages transitions on a copy, then commits only after validation.
Public researcher snapshots and event histories are detached copies. Solvers
receive a restricted port exposing only their own view and action submission.
This is an API boundary, not a Python sandbox: hostile in-process code can inspect
private attributes. Future untrusted integrations must run outside the kernel
process and use the same data protocol. Research tools may inspect truth; a
solver may not receive that inspection capability.

## Small ontology

| Abstraction | Represents / owned state | Must not own | Interactions | Domain |
| --- | --- | --- | --- | --- |
| Universe | Immutable gravity, ground/friction conventions, observation radius, rule version | Agents, designs, per-object success | Parameterizes physical evaluations | Truth |
| World | Kernel-controlled entities, resources, relations, clock and history | A reasoning model or solution catalog | Validates actions and commits events | Truth, including records of beliefs |
| Entity | Persistent UUID identity | Technology classification | Identifies objects, agents, relations and records | Both via references |
| Material | ID, label and numerical density, tensile/compressive strength, friction, shape cost | Recipes, permitted inventions | Object geometry and material properties derive capacity | Truth; observations can reveal it |
| PhysicalObject | Material reference, mass, position, length, section, radius; finite energy/power/force boundary conditions if supplied at genesis | Named artifact behavior, solver-asserted strength | Exposes derived affordances; participates in relations | Truth |
| Property | Named, unit-documented scalar measure | Arbitrary feature switches or executable rules | Inputs to constraints and affordances | Both: measured truth or attributed claim |
| Affordance | Kernel operation specification, compatibility/preconditions, costs | An invention recipe, guaranteed success | Maps a request to validation and a primitive transition | Truth; an agent can learn its availability |
| Relation | Endpoints and generic mechanical role: force, rotation, support, containment | A hidden complete machine | Composes objects; constrains paths and loads | Truth; observable |
| Constraint | Category, measured quantity, comparator, threshold | Arbitrary code or state mutation | Returns satisfied/unsatisfied/unknown with evidence and blockers | Both: hypotheses can contain constraints |
| Action | Actor, primitive operation and bounded structured arguments | Authoritative outcomes or patches | Only input to the transition boundary | Proposal, then truth as historical request |
| Event | Stable ID, causal action, evaluations, effects, state digest | A solver's assertion of success | Append-only audit; replay checks kernel-derived effects | Truth |
| Agent | Identity, location, finite effort energy, material stocks | Omniscient state access | Acts through its port and receives permitted observations | Truth |
| Knowledge | Per-agent claims, provenance, confidence and evidence references | Global facts implicitly known by everyone | Observe/record actions add records; conflicting claims may coexist | Subjective records stored authoritatively |
| Idea | Purpose, author, assumptions, references and lineage | Physical capability or correctness | Persisted by a validated record action; motivates designs | Subjective |
| Design | Components, relations, property requirements, intended functions, constraints, steps, assumptions, failures, evidence, parent/version | A new object class or automatic construction/success | Data-only hypothesis; construction steps become ordinary actions | Subjective; existence of record is truth |
| Experiment | Question, optional design reference, evaluable constraints and evidence/results | A bypass around construction or synthetic success | Test action evaluates current truth and records scoped evidence | Both: question subjective, measured outcome objective |
| Plan | Intent and ordered proposed primitive actions | Mutable world references or privileges | Baseline or future reasoner submits steps independently | Subjective |

Components and entity IDs refer to records; assemblies are relation graphs, not
dedicated artifact classes. Designs persist as knowledge even when false.
Recording a design never validates its intended physical behavior. Physical
construction is explicit and may fail partway through a plan.

## Physical scope and units

Use metres, kilograms, seconds, newtons, pascals, joules and radians. Objects are
uniform stock segments with volume = mass / density and section = volume / length.
Shaping consumes stock, effort and time. Generic relation capacities derive from
material strengths and section, never names. Support uses a deliberately coarse
span derating; containment uses finite volume and carried load. Ground objects
remain at z=0. Unconstrained elevated objects are disallowed at genesis and must
be supported at the end of an action.

Work is a quasistatic displacement request. Required force includes gravity for
raising and Coulomb ground friction for horizontal movement. A connected path
transmits force or rotation with explicit losses. Rotation uses radius to map
linear travel to angle and force to torque; no gear catalog or named machinery.
Environmental sources are finite reservoirs with power and maximum force limits,
provided as boundary conditions in genesis. Energy cannot be generated by
claiming a connection. Human effort is charged separately from environmental
work. Lowering dissipates energy in v0. Loads must remain supported; transient
motion is atomic rather than a timestep dynamics simulation.

This model intentionally omits collision, bending geometry, inertia, free fall,
fluid dynamics, heating, cutting tools, chemistry and automatic motion. These
are restrictions, not implicit successful behavior. Reject unsupported relation
or action types. Do not create placeholder affordances that claim to work.

## Constraints, observations, experiments

Physical/resource constraints read registered measurable quantities (position,
mass, capacity, span, energy, effort and recorded work). Knowledge constraints
read an identified agent's claims. Missing measurements yield `unknown`, which
never passes a goal. Manufacturing, economic, social and institutional categories
are reserved interfaces returning `unknown` until modeled. No evaluator may run
user-supplied Python. Experiment targets must be observable to the actor.
Knowledge preconditions use evidence-backed observations, not self-asserted
claims, so a belief action cannot grant material or physical permissions. Initial
shaping capabilities are explicit trusted genesis knowledge, not discoveries.

Agent views contain their own resources and accumulated observations only.
Observation is local, explicit and event-sourced; stale observations remain stale
until another observation. Other agents' inventories and knowledge are private.
Failure feedback reports validation relevant to the attempted operation without
dumping hidden state. A future communication system must propagate records
through actions rather than share a global knowledge dictionary.

## Determinism and persistence

Genesis, universe/material rules, seed, action attempts (including rejections),
events and final digest are stored in a versioned JSON run. UUIDv5 identifiers
derive from a logical-world namespace and event sequence. A replay is the same
logical world, so identities remain stable. Separate universes/forks require a
different namespace. Benchmark namespaces are derived from scenario content and
seed. JSON uses sorted keys, finite numbers and stable traversal order. v0 has
no stochastic physics; seed controls baseline candidate order and is recorded.
Determinism is guaranteed for the same rules and Python numeric environment,
not promised bit-for-bit across future engine versions/platforms.

Replay reconstructs genesis and revalidates every action, compares complete
events and the final state hash. It never trusts serialized patches. This detects
tampering/divergence, not maliciously re-authored complete histories. A rule
version mismatch must fail explicitly. State hashes exclude the history to avoid
recursive hashing; events carry the resulting state hash.

## Benchmarks and baseline

Scenario data owns genesis, permitted operations, initial knowledge, goal
constraints, seed and action/experiment budgets. Evaluators use world truth and
event-derived measurements; solvers receive only the public task and agent port.
Goals describe outcomes, never component layouts or construction procedures.
The baseline enumerates a small bounded set of primitive requests from observed
objects and property-compatible stock. It is deliberately weak, keeps no hidden
solution plans, and may fail every research benchmark. A separate calibration
test establishes that legitimate success is recognizable. Record failures as
results rather than adding special-case rules to improve scores.

## Module boundaries

`model` holds data-only action/design/experiment/plan schemas and serialization;
`materials` holds configurable property records; `constraints` evaluates measures;
`physics` derives capacities and work requirements; `affordances` describes
property-compatible operations, preconditions and costs; `world` owns the
transition authority; `benchmarks` loads scenarios and evaluates outcomes;
`simulation` holds the restricted solver port, weak baseline, run storage/replay;
`__main__` provides CLI inspection. Separate packages for every noun would add
indirection without strengthening this small system.

The subsequent `composition` solver adds bounded online relation search through
the same restricted port. It records candidate designs and evidence-bearing
revisions, without changing physical rules or obtaining a privileged trial world.
See [COMPOSITION_EXPERIMENT.md](COMPOSITION_EXPERIMENT.md) for its narrow scope.
