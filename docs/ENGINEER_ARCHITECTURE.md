# Milestone 2 implementation contract

## Free-text reliability extension (2026-10-19)

The default playable Engineer will interpret language into a small outcome IR:
selected observed subject, axis, signed displacement or absolute coordinate,
repetitions, energy preference and optional effort bound. This describes outcomes,
not artifact recipes. A free local interpreter handles paraphrases; a conservative
offline parser is available when no model is running. Unknown clauses must not be
silently dropped. Unsupported physics, unclear requests, exhausted search and
kernel-proven impossibility must have distinct user-facing explanations.

Typed interpretation compiles to frozen numeric constraints. A bounded general
planner then chooses primitive actions, observes failures and revises compositions.
The local interpreter receives schema errors for a finite number of repairs; it
cannot change world truth. This hybrid prioritizes reliable action execution and
does not claim unrestricted model-generated invention. Existing model-driven
proposal mode remains an explicit experimental option.

Tests must cover units, directions, relative/absolute positions, repetitions,
energy/effort restrictions, paraphrases, unsupported compound requests, source
exhaustion, repeated tasks, failed-model recovery, replay and visible replies.

One World kernel serves a stepwise Engineer controller, headless laboratory runs
and an optional Pygame client. No second physics implementation or artifact
catalog is introduced. Existing 0.1 worlds retain their replay semantics; new
laboratories use the additive 0.2 project protocol.

Projects are kernel records created by validated actions. They own the player's
text, interpreted measurable goals, budgets/counters, structured cognitive
artifacts, referenced designs/experiments and independently evaluated status.
Models can propose a goal but cannot change an established project's evaluator.
Unknown language/physics remains unresolved. Project success requires a kernel
experiment against the frozen project goals; a model cannot submit success.

The provider protocol consumes copied agent observations, known records and the
actor's project, and returns a closed structured proposal. Invalid output is
rejected before physical execution. Supported artifacts are hypothesis, intent,
candidate design/revision, plan/action proposal, experiment proposal, diagnosis
and unresolved requirements. Text is a concise explanation, never raw reasoning.
Providers include offline bounded search, response playback, and a loopback-only
Ollama adapter for installed local models. No paid API, cloud model, automatic
download or credentials are used. The local model receives a disclosed bounded
planner advisory proposal; model output still passes the same validation.
The CLI defaults to explicit ChatML raw transport for the installed Qwen model;
`--local-format chat` uses Ollama's native template for other models. This is
provider compatibility, not a world rule. Private thinking is never retained.

The offline provider has a disclosed limited language parser for measurable
displacement/repetition; unknown requests do not select a canned construction.
It enumerates generic paths, shapes stock when required, reacts to failure and
reuses evidence-backed transmission paths in later projects. It has no private
world clone or success evaluator. Live models may propose other compositions
within the same schemas. No named technology appears in their system context.

All physical work remains primitive kernel actions, one action per scheduler
step. Simulation time comes from those actions; speed controls pace dispatch
independently of rendering FPS. Actions commit atomically; the client displays
the resulting positions/angles, not invented continuous dynamics. Live calls
run in one worker on copied context; only the main controller commits results.

Successful experiments create measured functional knowledge and scoped principles
(tested path, observed work and conditions). Reuse is a proposal requiring a new
test, not permission to bypass the kernel. Save/load re-executes the complete
action history and restores unfinished projects from kernel records. Provider
responses are recorded so physical replay needs no network or model invocation.

Normal panels display legitimate observations and project artifacts; truth-only
properties appear solely in the explicit debug overlay. Event feeds are derived
from the kernel journal. The source is visibly labelled a finite mechanical
energy boundary: fluid harvesting, autonomous machinery, spatial travel and
gathering are not falsely rendered as implemented features.

## Concrete boundaries

`cognition.py` validates data-only cognitive artifacts. `providers.py` defines
the duck-typed `propose(context) -> {proposal, usage}` interface and zero-fee
adapters. `planner.py` is an explicitly bounded non-LLM policy, also disclosed as
advice to the local model. `laboratory.py` owns scheduling and response transport;
it cannot patch state. `projects.py` is part of the trusted World dispatcher,
not a reasoning module. `client.py` is an optional Pygame view with no physics.

The provider gets a detached context, not a World or Laboratory reference. It
can inspect observations, properties, affordances, its own stock/claims/designs,
failure evidence and the current project. It returns one typed artifact. Only
the main controller submits `reason_project`/`step_project` actions. A cancelled
worker result is discarded, including when another project starts meanwhile.

`step_project` validates an inner primitive against a staged state. On physical
rejection, only the project's attempt budget and failure observation change;
the wrapper event is accepted while `metadata.operation_accepted` is false.
Consumers must inspect that field rather than treating every accepted wrapper
as successful construction. Failed experiments are accepted measurements.
Experiments in 0.2 pay their measurement cost before evaluating resource goals;
0.1 replay retains the original ordering. Each reasoning artifact consumes 1 s,
recording a design another 1 s, and physical actions retain their kernel costs.

A Project contains player text, selected subject, frozen interpreted goals,
status/feasibility, counters, design lineage, queue, attempts and evidence. Goal
interpretation remains fallible: benchmark success is independently checked
against scenario goals hidden from the provider, not the model-selected goals.
The UI displays interpreted assumptions; stopping and starting a revised project
is the current way to correct interpretation.

Save format `civitas-lab-1` binds scenario, actor and genesis, then reexecutes every
action and checks the complete resulting events and final digest. It restores
unfinished queues and all committed knowledge. An in-flight provider request is
not committed state and must be requested again after loading. Large snapshots
are intentionally duplicated for inspection; no migration/checkpoint format yet.
