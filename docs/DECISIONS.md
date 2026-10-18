# Decisions and trade-offs

The numbered foundation decisions below describe 0.1. The Milestone 2 addendum
at the end supersedes deferred scheduling, client and project capabilities for
new 0.2 laboratory worlds; old 0.1 run semantics remain reproducible.

Read [AIM.md](../AIM.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for the governing
principles. These are v0 choices, not permanent commitments.

## Authority, persistence and representations

1. **One atomic kernel.** Copy state, validate a closed action, stage effects,
   check global postconditions, commit once and append an event. Snapshots/views
   are copies. There is no public patch/apply-event endpoint. Research genesis
   construction is trusted and validated. Python internals are not a security
   boundary; an external reasoner will need process isolation.
2. **Actions and events are both retained.** Replay re-executes actions rather
   than trusting patches, checks complete events and final hashes, and binds the
   saved task/genesis to scenario content. Effects carry before/after records for
   causal inspection. This is an event journal with deterministic reconstruction,
   not a separate event-only projection framework. It deliberately duplicates
   observations and state in large events; optimize storage only after semantics
   stabilize. No checkpoints, migrations, signatures or concurrent writers.
3. **UUIDv5 identities.** World namespace is a hash-derived UUID of scenario and
   seed; event and entity IDs derive from that namespace and attempt sequence.
   Replay retains identity. A different scenario/seed is a separate logical
   world; two identical runs refer to the same logical world. Catalog material
   IDs identify shared definitions. There is no automatic run/fork identity
   independent of scenario content yet; a new fork needs a new namespace.
4. **JSON data and standard library.** Frozen request/IR dataclasses plus detached
   dictionaries keep serialization inspectable. Numeric input is finite; JSON
   normalization happens before validation. No generated code, plugin evaluator,
   third-party schema/physics library, database, rendering or network service.
   `pyproject.toml` describes optional packaging; running from the repo needs no
   installation. Floating point is deterministic within the recorded rule/runtime
   assumptions, not guaranteed across every platform or future interpreter.
5. **Designs are hypotheses.** Their structure and references are checked, but
   requirements do not imply feasibility. Recording ideas/designs and version
   lineage creates agent knowledge, not physical objects. Construction steps
   have primitive action envelopes; symbol binding, scheduling, execution of a
   whole design, and automated diagnosis/revision are deferred. Plans are simple
   intent plus action sequences. The baseline proposes actions, not design prose.

## Explicit physical shortcuts

6. **Two-dimensional point positions and uniform stock segments.** Section equals
   mass/density/length. Radius is an effective motion arm chosen during shaping;
   it is not derived from volumetric geometry. No spatial meshes, collision,
   occupancy, surface orientation or detailed attachment points. Arbitrarily
   chosen lengths/radii remain an exploit surface for richer future benchmarks.
7. **Illustrative properties.** Ten familiar material labels have configurable
   numeric density, strength, friction and shaping energy. These are approximate
   synthetic research values, not engineering data. No phase behavior, chemistry,
   temperature or damage; even fluid stock is only a mass/property record.
8. **Quasistatic displacement.** Work is friction × horizontal travel plus positive
   gravitational potential gain. Required scalar force includes controlled
   lowering. No acceleration, momentum, timestep integration, free fall, terrain
   height profile, rolling/contact changes or vector force balance. Horizontal
   friction is charged even for elevated loads. Lowering dissipates energy;
   there is no regenerative recovery.
9. **Scalar transmission graphs.** Force paths transmit at 1:1 displacement;
   rotation paths share angle and map input/output force through effective radii.
   Each edge loses a fixed fraction of work. Capacity is tensile section capacity
   (or capacity × minimum radius for torque). This is an abstract kinematic port
   relation, not derived contact mechanics or a hidden artifact recipe. The last
   node's displacement is coupled to rotation through its radius; intermediate
   nodes rotate in place. Direction, reaction forces and branch power splitting
   are not modeled. Only an explicitly selected simple path participates;
   adjacent transmission edges do not impose rigid-body kinematics. Mixed modes
   are rejected. V0 paths are capped at 16 distinct nodes.
10. **Environmental work is already mechanical boundary power.** Sources are
    finite, anchored energy reservoirs with power/force bounds supplied at genesis.
    No harvesting or conversion from fields/flows is claimed. They cannot be
    created by shaping or replenished by assertion. This is the largest gap
    between the mechanical benchmark and the eventual Unseen Object Test.
11. **Coarse support.** Grounded anchors provide compressive-section capacity
    derated by `1 + (span / length)^2`. Total supported weight must fit the most
    conservative capacity of the anchor's relations. No bending, buckling,
    load distribution, contact topology, fatigue or safety factors. One bearing
    relation per load, no nested supports, no moving loaded anchors. Elevated
    objects must remain supported; failed motion is rejected instead of collapsing
    or damaging the structure. At genesis everything starts grounded.
12. **Coarse containment.** Host material volume serves as available capacity, and
    summed contents must fit it and the load limit. No actual cavity geometry or
    fluid behavior. It constrains relationships, not dynamic container transport.
13. **Fixed construction costs.** Shaping consumes stock and property-derived
    J/kg; connection consumes 5 J and 1 s but no connector stock. No tooling,
    manufacturing tolerances, waste, joining process, repair, destruction,
    disconnection or stock recovery. No explicit suspend/cut/heat operation is
    advertised because those transitions have not been modeled.

## Explicit epistemic, experimental and evaluation shortcuts

14. **Local perfect observation.** A radius grants full numerical inspection of
    local objects and property-derived affordances. Observations persist and can
    become stale. No noise, occlusion, travel, specialized instruments or uncertain
    measurement distributions. Agents remain at their initial positions in v0.
15. **Minimal knowledge gate.** Initial per-material shaping claims attest to
    procedural capability; they are not a technology tree. An asserted belief
    cannot grant that capability. Experiments currently create measured evidence,
    not new manufacturing skills. Claims may conflict; no inference, forgetting,
    teaching, communication or confidence revision is implemented.
16. **Measurement-only experiments.** Construction and motion happen through
    preceding actions; `experiment` evaluates constraints, spends 1 J/1 s, and
    records results/evidence. A failed hypothesis is a successful measurement
    action. Results describe the state just before measurement cost is paid, so
    final resource evaluation can differ by that cost. No autonomous trial loop,
    resetting worlds, noise model, diagnostic engine or design attribution of
    measured performance yet.
17. **No social authority model.** Inventories and knowledge are per-agent and
    private through the port; object ownership, transfer, prices, organizations,
    institutions and permissions are absent. Manufacturing constraints beyond
    the shaping gate, and economic/social/institutional constraints return
    `unknown`. Five agents exist, but only one baseline acts.
18. **Small constraint language.** A conjunction of registered scalar measures
    with exact comparisons. Unknown values fail goals. No arbitrary expressions,
    quantification, temporal logic, tolerances, probabilistic success or new
    user-defined evaluators. `known` tests possession, not truth. Crossings count
    complete intervals with reset; work totals alone do not prove useful cycles.
19. **Weak, nonadaptive baseline.** Samples two available known materials with
    one fixed geometry, tries shuffled pairwise relations, single-step movement
    and single-edge environmental work, then measures. It does not consume
    failure feedback to revise plans, remove obstructive relations, search
    sequences, generate persistent designs or attempt repeated cycles. UUID
    ordering affects candidate order, so scenario metadata edits can change its
    score by changing the logical-world namespace. Seed 42 is a single reference
    run, not a statistical claim.
20. **Simple budgets and journal.** Every JSON attempt counts, including rejected
    actions/experiments; rejection advances only the journal, not simulated time.
    Invalid non-JSON inputs fail at the transport boundary and are not replayed.
    No wall-clock/compute budget, automatic scheduler or asynchronous simulation.
    CLI run paths overwrite on repeat. Run files are local and unauthenticated.

## Unresolved architectural questions

- Which minimal geometry/contact and environmental field interactions would let
  an agent discover an energy-conversion arrangement rather than receive usable
  power as a boundary condition? Establish general primitives with independent
  controls before adding them for any particular outcome.
- Should assembly motion propagate constraints across the full relation graph,
  and how should reaction forces, branching power and unsupported loads behave?
  Current independent path semantics are too permissive for realistic mechanisms
  and too restrictive for moving assemblies.
- When should a failed physical attempt consume resources or cause damage rather
  than reject atomically? Keep invalid requests distinct from valid risky trials.
- How should measured evidence become procedural know-how? What distinguishes
  an agent believing a method from actually being capable of executing it?
- What is the smallest safe binding from design component symbols to constructed
  identities, including partial construction, reuse and revised lineage?
- How should experiment evidence attribute a performance claim to a particular
  design version, rather than merely a world state? How will quantified outcome
  constraints recognize arbitrary novel assemblies without granting success by name?
- Which identity, numeric and rule-migration policies are needed for independent
  forks, long-lived runs and cross-version replay?

## Proposed next experiment at foundation review

Run a **held-out, unnamed three-component composition** test after review. Freeze
the kernel; give a tiny deterministic search only legitimate observations, a
force/work objective and a bounded geometry/material parameter space. Include a
feasible calibration and a capacity-limited impossible control. Require it to
record a design, bind its primitive steps, measure failure/success, and persist a
revised version with causal evidence. Change one strength or gravity parameter
for transfer. This isolates the design → construction → evidence binding gap
before an Engineer integration. Do not add scenario-specific rules if it fails.

The user subsequently authorized starting this experiment. The implemented
first slice uses three supplied bodies, online relation search, direct persistent
ID bindings and measured design revisions. It keeps the kernel frozen and adds
an energy-limited control plus gravity transfer. It is public calibration, not a
genuine held-out study or geometry/manufacturing search. See
[COMPOSITION_EXPERIMENT.md](COMPOSITION_EXPERIMENT.md) for results and restrictions.

## Milestone 2 addendum

21. **Kernel-owned projects.** Intent, structured artifacts, queues, finite
    budgets, failed attempts and results are explicit action/event transitions.
    A nested physical operation can fail while the wrapper successfully records
    the failure and spends an attempt. Neither providers nor the client can
    patch project status, physics or knowledge. Unknown measurements fail goals.
22. **Versioned additive rules.** Laboratory worlds use semantic 0.2; foundation
    benchmarks retain 0.1 hashes. In 0.2, experiment results include measurement
    cost, and work refreshes the actor's observations of the whole participating
    path. Added resource inspection and generic disconnection are kernel actions;
    removing an indispensable support is rejected atomically. Disconnection costs
    2 J/1 s and does not recover stock. No new artifact-specific physical rule.
23. **Free local inference only.** The user's no-payment constraint supersedes
    the milestone's paid-provider examples. The runtime supports installed local
    Ollama models on loopback, offline search and response replay. Cloud models
    are rejected; no API keys, automatic download or paid-provider SDK exists.
    Local reasoning receives bounded-planner advice. Adopting that advice is an
    explicit model output, not an invisible fallback. Invalid outputs stop the
    project honestly. This assisted policy is not evidence of unaided invention.
    Explicit ChatML raw transport is available for compatible models when native
    template/thinking behavior prevents public JSON output; other models can use
    native chat transport. It changes prompt formatting, never world semantics.
24. **Restricted language and search.** Offline interpretation handles selected
    objects, positive numeric lift/translation and at most eight repeated lifts.
    Defaults are shown. It searches paths of two or three observed bodies, two
    transmission modes and one optional support; shapes one candidate stock body
    with geometry derived from the target separation. Material selection uses
    strength/cost properties. Candidate paths are tested online, failed connections
    prune later proposals, and no world clone provides feasibility to the policy.
25. **Scoped discovery and transfer.** A passed project experiment records its
    design, evidence, measured path/mode and gravity. This is a measured-instance
    principle, not an abstract law inferred by a model. Reuse substitutes another
    observed endpoint and requires new validation. Warm/cold transfer starts from
    identical completed-world checkpoints, retaining physical construction in
    both; the cold provider cannot see previous designs/discoveries/experiments.
    Construction facts remain observable in both, so cold is not a blank mind.
26. **Playable client.** Optional Pygame draws generic bodies and relation graphs.
    Four agents are passive; the Engineer acts within the existing interaction
    radius. No gathering, agent travel, collision, fluid or autonomous cycling is
    disguised by animation. Shape/connect/work are visible, separately timed
    steps. Action commits are discrete, with dispatch paced by simulation-time
    costs and speed controls; model wall time is separate.
27. **Bounded asynchronous reasoning.** One worker processes copied context; the
    UI thread alone commits proposals. Pausing delays response application. Stop
    discards pending responses. An active HTTP request cannot be forcibly killed
    by Python's thread API; it has a finite timeout. Local providers report token
    counts when available, but no compute-energy or electricity-cost estimate.
28. **Measurement caveats.** Goals are conjunctions over known persistent IDs,
    with cumulative work/crossing totals. A project can satisfy an imperfect
    interpretation; benchmark evaluation independently uses the requested numeric
    outcome. It does not yet causally isolate a design from earlier activity.
    The conservation certificate is deliberately narrow: if all objects have
    been observed and total remaining source energy cannot reach the required
    environmental work, the task is known infeasible under this closed kernel.
    Otherwise a search failure is unknown/currently unrealizable, not impossible.

Remaining physical shortcuts 6–12 above still apply. In particular, repeated
`work` actions are externally scheduled controls, not an invented autonomous
machine. No hidden target class, recipe, alias or named-invention prompt is used.

Next review should select a small independent holdout and compare local model
outputs with and without planner advice, including invalid output rate and goal
interpretation fidelity. General geometry/contact and energy harvesting remain
separate physics research questions; do not solve them with a target-specific
object class.

## 2026-10-19 — Task understanding: honest outcomes and enforced commitments

- **Effort limits are kernel preconditions.** A project goal `effort_spent <= cap`
  rejects any step or measurement that would exceed it (`effort_limit`), leaving
  state unchanged. A final failed check is not evidence the limit was respected.
- **Energy impossibility is a conservation bound.** After a failed experiment the
  kernel compares the minimum work for the remaining displacement/repetitions
  (lowering free, straight paths) with all energy in the permitted channels.
  Only then is `known_infeasible` reported; planner exhaustion stays `not_found`.
- **Tiered language.** Grammar first; the local model only for grammar gaps,
  returning the outcome IR, checked against the literal request, ≤2 repairs.
  Model refusals are labelled as its judgement, not world facts.
- Foundation (0.1) replay hashes are unaffected; the 0.2 project protocol had
  no released saves, so it was changed in place rather than versioned.

## 2026-10-19 — Free cloud language backends; models translate, the grammar compiles

- **Free cloud inference is allowed; paid inference is not.** The user lifted
  the local-only rule. Presets cover verified/reported free tiers (keyless
  OVHcloud, Groq, Gemini, OpenRouter `:free` only, Cerebras, Ollama Cloud).
  Keys come from environment variables and are never stored in worlds.
- **The model's output language is the grammar.** Instead of emitting goals, a
  model returns outcome steps that are rendered as canonical grammar sentences
  and must round-trip through `parse_offline`. One deterministic compiler, a
  human-readable plan, and no new trust in model output.
- **Literal guards over model trust.** Stated distances, direction words,
  destination cues and restriction cues (energy, effort, repetition) must agree
  with the request; disagreements become bounded repair prompts.
- **Multi-step requests are Ideas.** The plan is a kernel Idea (`civitas-task-1`)
  and each step a normal project; the agenda is rebuilt from the journal on
  load, and stops at the first failed step instead of skipping it.
- The per-project `InterpreterProvider` was removed in favour of this path.
