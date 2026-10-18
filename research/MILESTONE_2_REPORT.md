# Milestone 2 report

The playable laboratory and persistent invention-loop infrastructure are
implemented. The demonstrated successful runs use the disclosed offline bounded
planner. Free local inference is integrated, but the installed small model has
not demonstrated a reliable complete invention run: it interpreted a goal, then
its next malformed proposal was rejected without physical mutation. **The central open-ended
Unseen Object hypothesis remains unproven.**

Launch: `python -m civitas play`. Installation and controls are in the
[README](../README.md). Measurements and reproduction commands are in
[EXPERIMENTS.md](EXPERIMENTS.md).

## A. Can I launch and play?

Yes. A Pygame world opens with five agents, finite environmental mechanical
energy, material stock and two heavy loads. Selection, camera navigation,
pause/speeds, natural-language input, project/history/knowledge panels, developer
inspection and save/load use the same kernel as headless runs. Only the Engineer
acts; the other four agents are passive. The client is optional and replaceable.

## B. Can I enter a goal that was not hard-coded?

Yes, arbitrary text creates a persistent project. Offline understanding is
limited to selected-object translation/lifting with explicit numeric defaults.
An alternate three-cycle, half-metre request passed without engine changes.
Unsupported language can remain unresolved. Local models can adopt, replace or
decline an advisory proposal; arbitrary text understanding is not guaranteed.

## C. What did the Engineer design?

In the successful offline run, it shaped a 2 kg, 3 m stock body and tested
transmission/support graphs involving the environmental source and 100 kg load.
Five candidates and four construction failures preceded a working arrangement.
The final generic graph transferred force and supported the elevated load.
Candidate generation is deliberately bounded and uses general mechanical prior
knowledge; this is not a claim of unaided creative model reasoning.

## D. Did it physically exist?

Yes, in the semantic simulation. Stock decreased, a new persistent PhysicalObject
appeared through `shape`, and accepted `connect` actions created real relations.
No named composite class, automatic recipe expansion or final-artifact spawn was
introduced. Geometry and physical capacities remain coarse approximations.

## E. Was the experiment visible?

The real window ran the full task at 20x through its text-input handler and
asynchronous scheduler; failure/completed screenshots were captured and inspected.
Its final hash exactly matched the headless feasible run, and its save replayed.
Unknown components draw using the same geometric grammar; relations and proposed
graphs are visibly distinct. Positions and orientation come from observations
updated by kernel actions. Failure does not cause an invented collapse animation.
The UI is a discrete causal viewer, not a continuous dynamics engine. Automated
client checks also exercise text submission and read-only rendering.

## F. Did simulation independently determine the outcome?

Yes. Projects freeze interpreted constraints and test them through kernel
experiments. Models cannot submit a success state or arbitrary world patches.
The research evaluator separately checks the scenario's numerical outcomes; a
test explicitly demonstrates that satisfying an easier mistaken interpretation
does not pass the benchmark. Unknown measurements cannot pass.

## G. Did failure lead to revision?

Yes. Failed reach/support attempts produced structured observations, diagnosis
artifacts and immutable parent-linked revisions. Existing accepted construction
survives a failed plan. A failed primitive is recorded as a failed inner operation
within an accepted project bookkeeping event; inspectors expose that distinction.

## H. Did successful knowledge persist?

Yes. A passed experiment creates a discovery referencing the tested design,
project, experiment, measured constraints and scoped path/mode/gravity principle.
Save/load verifies the complete action/event history and restores that knowledge,
unfinished queues and design lineage. Assertions alone cannot create discoveries.

## I. Did knowledge transfer?

Yes, within this authored calibration. Matched forks of the same completed world
attempted the second load. Cold: 20 actions, 8 experiments, 17 reasoning artifacts,
66 simulated seconds. Knowledge enabled: 6 actions, 1 experiment, 3 reasoning
artifacts, 38 seconds. Both passed the independent evaluator. This demonstrates
measured path reuse, not abstract scientific law induction or statistical proof.

## J. Was solution-specific knowledge encoded?

No named target classes, recipes, aliases, drawing branches or prompt examples
were introduced. There is no string-to-successful-demo route. However, the
offline planner explicitly knows how to enumerate short transmission paths and
try supporting elevated loads. It chooses one stock geometry and two transfer
modes. These are disclosed mechanical search biases, not unrestricted invention.
Local-model assistance exposes those same candidate proposals to the model.

The scenarios were developed with the implementation and are **not blind**.
A separately authored, frozen-engine holdout remains necessary.

## K. Simulation, abstractions and shortcuts

Actual simulation includes material/energy costs, time, reach, capacities,
support, finite-source work, motion evidence, construction, measurements,
failures, project budgets and persistent knowledge. There is one World kernel.

Current shortcuts are explicit:

- Finite mechanical energy is supplied at genesis. River flow, harvesting,
  chemistry and detailed contact mechanics are absent.
- Quasistatic 2D point geometry, effective radii, scalar paths and approximate
  support capacities remain the foundation model. No collision, free fall,
  momentum, moving supported assemblies, damage or branch-power calculation.
- Repeated motion is a sequence of controlled `work` actions. The artifact does
  not autonomously cycle. Human control costs 1 J per work action.
- Shape/connect/disconnect use simplified costs. There is no connector stock,
  tool manufacture, gathering, physical inventory transport or stock recovery.
- Engineers act within an observation/interaction radius and do not walk. Four
  visible agents have no policy. Observation is perfect, local and can be stale.
- The offline parser defaults to one metre/two repetitions, targets one selected
  body, searches only short graphs, shapes one candidate geometry and cannot
  express every structural/transport goal. It reports these limits.
- Model inference is assisted by a disclosed bounded planner. Invalid responses
  stop rather than being repaired through an invisible scripted success.
- Discovery principles are measured instance records, not generalized laws.
  Warm transfer replaces an endpoint; current observations still require retests.
- Numeric goals are conjunctions over known identities with cumulative counters.
  Experiment-to-design causal attribution and time-windowed performance are
  incomplete; prior activity can contribute to a later measurement.
- Failed physical attempts consume an attempt but no resources or simulation
  time. Accepted actions commit atomically and appear discretely in the client.
- Budgets count primitive attempts, experiments and accepted reasoning artifacts.
  Startup observations and lifecycle actions are separately journaled. Incomplete
  or malformed model-response token usage is not fully accounted for.
- Saves duplicate state in journals, assume compatible runtime/rules and have no
  migration, authentication or compact checkpoints. Python privacy is an API
  boundary, not a hostile-code sandbox.
- Pending local HTTP calls have finite timeouts but cannot be forcibly killed
  by the thread pool. Stop discards their responses; replay never calls a model.
- UI glyphs and material treatments are procedural; graph geometry is a visual
  grammar rather than an engineering mesh. No external sprite assets are bundled.

All inherited details are enumerated in [DECISIONS.md](../docs/DECISIONS.md).
No missing physical abstraction is concealed by LLM text or visual effects.

## L. What still prevents the CIVITAS vision?

The largest gaps are reliable independent generative reasoning, authentic energy
conversion from environmental fields, spatial contact/assembly constraints,
autonomous behavior, manufacturing know-how, causal evidence attribution and
broader language understanding. Social/economic/institutional simulation remains
outside this milestone. This is a working small research game, not open-ended
technology evolution.

## Validation and next review

The full suite passed 72 tests at final implementation verification, including original
baseline replay hashes. Offline laboratory, impossible control, altered gravity,
matched knowledge transfer, variant numeric input and the original suites were
run and traces inspected. Every saved suite run replayed successfully.

The smallest next experiment is an independently authored numeric holdout with a
frozen kernel and explicit interpretation checks, comparing a reliable free local
model with and without bounded-planner advice. First measure valid output rate,
latency and outcome fidelity; do not add any target-specific primitive to improve
the score. Open questions include design attribution across tasks, reusable
symbolic component bindings, safe autonomous cycles and general environmental
interaction primitives.

No Milestone 3 work has been started.
