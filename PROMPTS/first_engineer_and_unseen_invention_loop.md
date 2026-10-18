Read @AIM.md completely before making any changes.

Then read:

- @docs/ARCHITECTURE.md
- @docs/PRINCIPLES.md
- @docs/BENCHMARKS.md
- @docs/DECISIONS.md

Inspect the existing implementation and tests before modifying anything.

This milestone has TWO equally important outputs:

1. the first genuine **Unseen Invention Loop**, and
2. the first **playable CIVITAS world** in which a human can interact with that loop directly.

At the end of this milestone I should be able to run one simple command, open CIVITAS, see a small simulated world, select/interact with an Engineer, describe something in natural language, and watch the consequences unfold.

The playable interface is NOT a separate game implementation.

It must be a client/view over the exact same deterministic simulation kernel used by benchmarks and tests.

The central research question remains:

> Can an intelligent agent conceive, design, test, iterate on, and persist a functional solution that was never explicitly implemented in the codebase?

The central player fantasy is:

> I describe something that does not exist in the game, and inhabitants of the world attempt to make it real.

---

# 1. Preserve the Fundamental Rule

The most important invariant remains:

> LLMs propose. The world disposes.

The Engineer may:

- interpret goals,
- reason,
- inspect its knowledge,
- inspect permitted observations,
- propose designs,
- propose experiments,
- communicate,
- formulate plans,
- propose actions,
- analyze failures,
- revise designs,
- learn.

The Engineer must NOT:

- mutate authoritative world state,
- declare its own invention successful,
- create arbitrary resources,
- teleport,
- construct objects instantaneously,
- bypass time,
- bypass physical constraints,
- bypass resource constraints,
- access omniscient world state,
- execute arbitrary generated code.

The visual client must obey exactly the same rule.

A UI button must never secretly perform an action that would be impossible through the simulation API.

---

# 2. One Simulation, Multiple Interfaces

There must be ONE authoritative simulation implementation.

Architecture should conceptually resemble:

                        CIVITAS KERNEL
                              |
              +---------------+---------------+
              |                               |
         Benchmark CLI                    Game Client
              |                               |
         automated runs                  human interaction
              |                               |
              +---------------+---------------+
                              |
                         Event Log

Do NOT create:

`game_physics.py`

and separately:

`benchmark_physics.py`

Do NOT create simplified fake game rules just for visualization.

The graphical client observes world state and submits the same Actions used by every other system.

---

# 3. First Playable Command

At the end of this milestone I should be able to run something simple such as:

`python -m civitas play`

or:

`python run_game.py`

Prefer the package command if the current architecture supports it cleanly.

This should launch the first playable CIVITAS laboratory.

Document the exact command prominently in the README.

---

# 4. Choose an Appropriate Lightweight Client

For this milestone, prefer a lightweight Python-compatible graphical framework such as Pygame unless inspection of the existing repository reveals a substantially better choice.

Do NOT introduce Unity or Unreal.

Do NOT couple the simulation kernel to Pygame.

Keep the client replaceable.

Conceptually:

civitas/
    simulation/
    ...
    client/
        pygame/
            renderer.py
            input.py
            camera.py
            ui.py

The simulation should continue running perfectly without importing Pygame.

---

# 5. The First World

Create a deliberately tiny sandbox.

It should visually contain enough to understand the invention loop.

For example:

- terrain,
- a river or environmental energy source,
- trees/material sources,
- stones/resources,
- a workshop/construction area,
- approximately 3–5 agents,
- one Engineer.

Do not create a large procedural world.

A compact laboratory world is better.

The purpose is to WATCH causal simulation.

---

# 6. Visual Style

Do not spend significant time on art.

Use simple procedural graphics:

- colored terrain tiles,
- circles/rectangles/simple sprites for agents,
- basic geometric representations for objects,
- lines for connections,
- simple labels,
- minimal icons where useful.

No external art pipeline is required.

However, the world should be visually understandable.

I should be able to distinguish:

- agents,
- materials/resources,
- constructed objects,
- environmental features,
- active projects.

---

# 7. Camera and Navigation

Implement basic:

- pan,
- zoom,
- entity selection,
- pause,
- resume,
- simulation speed controls.

Suggested speeds:

- paused
- 1x
- 5x
- 20x

Exact values may differ.

The player must be able to slow down the simulation to inspect invention attempts.

---

# 8. Clicking an Agent

When I select an agent, show a panel with relevant information.

For the Engineer, display at least:

- name/ID,
- current goal,
- current action,
- current plan,
- known relevant concepts,
- current hypothesis,
- active design,
- latest observation,
- latest failure/diagnosis.

Do NOT expose information the agent itself does not know unless it is clearly displayed in a separate developer/debug mode.

This distinction is important.

---

# 9. Natural-Language Command Interface

The playable client must contain a text input.

I should be able to select the Engineer and type something like:

> Use the river to create something that repeatedly raises these heavy stones without requiring people to continuously lift them.

The game must NOT map this string to a predefined invention.

Instead:

PLAYER TEXT
    ↓
Intent interpretation
    ↓
Engineer goal
    ↓
Engineer reasoning
    ↓
structured proposal
    ↓
simulation
    ↓
visible consequences

Other examples I should eventually be able to try:

> Build something that helps us move these rocks with less human effort.

> Find a way to cross this gap using the materials available here.

> Create a structure that can support this heavy stone above the ground.

These are goals.

They are NOT named recipes.

---

# 10. Visible Reasoning Without Raw Chain-of-Thought

Do not expose private/internal chain-of-thought.

Instead show concise structured reasoning artifacts generated by the system.

For example:

ENGINEER

Goal:
Raise stone repeatedly.

Current hypothesis:
Flowing water may provide continuous mechanical energy.

Need:
A mechanism that transfers environmental motion to the load.

Problem:
Current connection slips under load.

Next experiment:
Test stronger connection using available material.

This should come from structured:

- hypothesis,
- diagnosis,
- plan,
- experiment,
- observation

objects.

Do not display hidden model reasoning.

---

# 11. Projects

Introduce a first-class visual concept of a Project.

When the player gives an Engineer a sufficiently complex goal, create something like:

PROJECT #17

Goal:
Repeatedly raise stone.

Status:
Experimenting

Lead:
Engineer Ada

Design:
Prototype v3

Blocker:
Connection fails under load.

Projects should connect:

player intent
→ agent goal
→ designs
→ experiments
→ construction
→ results.

Selecting a Project should let me inspect its history.

---

# 12. Visualize Designs

A proposed Design must have a visible representation.

Do NOT require custom art for newly invented objects.

Render unknown constructions using their underlying components and relations.

For example:

- components as geometric shapes,
- connections as lines/joints,
- supports visibly attached,
- rotating components visually rotate if simulation state says they rotate,
- moving components move according to simulation state.

This is extremely important.

The rendering system must be able to display objects that developers never anticipated.

Do NOT require:

`if object.type == "water_wheel": draw_water_wheel()`

Instead render generic components based on structured world state.

---

# 13. Construction Must Be Visible

An Engineer should not say:

> Construction complete.

and instantly spawn the final object.

Where supported by the current simulation, the player should see agents:

- move toward resources,
- acquire materials,
- transport components,
- create/shape components,
- move to construction location,
- connect components,
- perform experiments,
- modify failed designs.

Keep animation simple.

The important thing is causal legibility.

If some construction actions remain abstract at this milestone, represent them explicitly through timed world actions rather than instantaneous magic.

---

# 14. Time Must Matter

Actions should consume simulation time.

Examples:

- moving,
- gathering,
- constructing,
- testing,
- researching.

Do not make the invention loop instantaneous.

The player should be able to watch:

Day 1
Goal received.

Day 2
Materials inspected.

Day 3
Prototype planned.

Day 5
Prototype constructed.

Day 5
TEST FAILED.

Day 6
Engineer diagnoses failure.

Day 8
Prototype v2 constructed.

This is the beginning of CIVITAS history.

---

# 15. Failure Must Be Visible

Failure is gameplay.

If something breaks:

show it.

If something does not move:

show it.

If a connection fails:

show the disconnected state.

If the design lacks sufficient force:

show that the experiment failed to move the target.

Then display structured diagnosis.

Do NOT fake dramatic failure animations if the underlying simulator did not produce that failure.

Visuals reflect simulation truth.

---

# 16. Event Feed

Add a small event/history panel.

Examples:

12:31 — Engineer received new goal.

12:34 — Design Prototype-1 created.

12:41 — Construction started.

12:52 — Experiment started.

12:53 — Connection failed under load.

12:55 — Engineer created Prototype-2.

13:07 — Prototype-2 transferred rotational motion.

This feed must originate from the simulation Event Log.

Do not maintain a separate UI-only history.

---

# 17. Debug / Research Overlay

Provide a toggleable developer overlay.

It may show:

- entity IDs,
- physical properties,
- affordances,
- forces/loads where implemented,
- constraint evaluations,
- current simulation tick,
- event IDs,
- random seed,
- design component graph,
- Engineer knowledge references.

This is a research prototype.

Debuggability is more important than visual polish.

---

# 18. Save and Load

Implement simple save/load if it fits the current architecture cleanly.

At minimum support:

- save current world,
- reload current world,
- preserve discovered designs,
- preserve agent knowledge,
- preserve projects,
- preserve event history or sufficient replay information.

Prefer deterministic serialization.

If full save/load conflicts significantly with existing architecture, document why rather than implementing an unsafe shortcut.

---

# 19. Engineer Reasoning API

Implement the provider-independent Engineer introduced in the original Milestone 2 plan.

The Engineer receives only legitimate observations and knowledge.

Create structured interfaces for:

- inspect_known_materials
- inspect_known_affordances
- inspect_environment
- inspect_known_designs
- propose_design
- propose_experiment
- propose_plan
- inspect_failure
- revise_design
- record_hypothesis

Exact API names may differ.

Do not expose raw internal world objects unnecessarily.

---

# 20. Model Adapter Layer

Create a provider-independent reasoning interface.

It should be possible to use:

- OpenAI
- Anthropic
- local models
- deterministic mock models
- recorded/replayed reasoning traces

without rewriting simulation logic.

Automated tests must NOT depend on paid API calls.

If credentials are available, provide a documented way to configure a live Engineer.

If no credentials are available, the playable game should still launch.

In that case clearly indicate that the Engineer is running in mock/non-live mode.

---

# 21. Structured Cognitive Outputs

All actionable Engineer output must be schema validated.

Implement representations for at least:

- Hypothesis
- CandidateDesign
- ExperimentProposal
- ActionProposal
- Diagnosis
- DesignRevision

Invalid model output must not mutate world state.

---

# 22. No Arbitrary Generated Code

The Engineer must NOT generate Python and execute it as an invention mechanism.

It composes:

- materials,
- properties,
- components,
- relations,
- affordances,
- actions,
- constraints.

If it needs a capability not represented by the ontology, represent that explicitly as an unresolved requirement.

Do not silently manufacture a new engine primitive.

---

# 23. Full Invention Loop

Implement:

GOAL
  ↓
OBSERVE
  ↓
REASON
  ↓
HYPOTHESIS
  ↓
DESIGN
  ↓
VALIDATE
  ↓
PLAN
  ↓
CONSTRUCT
  ↓
EXPERIMENT
  ↓
WORLD SIMULATION
  ↓
OBSERVATION
  ↓
SUCCESS?
  ├── YES
  │     ↓
  │   PERSIST KNOWLEDGE
  │
  └── NO
        ↓
      DIAGNOSE
        ↓
      REVISE
        ↓
      RETRY

This loop must work both:

- through automated benchmark execution,
- through the playable client.

There must not be separate implementations.

---

# 24. Budgets

Every project must have finite budgets.

Support at least:

- maximum reasoning iterations,
- maximum experiments,
- maximum actions.

Architect for later:

- resource budget,
- monetary budget,
- model-token budget,
- simulated-time budget.

Agents must be capable of giving up or declaring:

- unresolved,
- currently infeasible,
- insufficient knowledge,
- insufficient resources.

---

# 25. Unknown vs Impossible

Represent at least:

- known feasible,
- known infeasible,
- unknown,
- currently unrealizable.

Unknown should often trigger investigation.

Impossible should arise from universe constraints rather than model opinion.

---

# 26. Experiments Produce Evidence

Experiments must produce structured observations.

Possible examples:

- displacement,
- rotation,
- structural failure,
- connection failure,
- energy transferred,
- force insufficient,
- object remained stable,
- object moved,
- target elevation changed.

Evidence should be stored and viewable through the UI.

---

# 27. Design Lineage

Never overwrite designs.

Show:

Prototype 1
    ↓
Prototype 2
    ↓
Prototype 3

The UI should allow inspecting at least basic design lineage.

Each revision records:

- parent,
- modifications,
- reason,
- evidence,
- outcome.

---

# 28. Persistent Discoveries

Successful inventions become Knowledge.

Do not merely mark the project complete.

Store:

- design,
- demonstrated functionality,
- evidence,
- discovered relationships,
- provenance.

The Engineer should be capable of reusing this knowledge later in the SAME playable world.

---

# 29. Principle Extraction

Attempt to persist reusable functional principles separately from entire inventions.

Example:

environmental motion
→ rotational motion

or:

distributed supports
→ reduced load per support

These principles require evidence.

The model cannot simply assert them into truth.

---

# 30. First Playable Scenario

Create one intentionally small playable scenario.

It should contain:

- small map,
- moving water/environmental energy,
- several resource types,
- heavy movable objects,
- construction area,
- several simple agents,
- Engineer.

The player should be able to give the Engineer arbitrary text goals.

Provide a suggested first test in the README:

> Use the movement of the river to create something that repeatedly raises these heavy stones without requiring people to continuously lift them.

Do NOT call the expected solution a water wheel anywhere in the Engineer's context.

Do NOT require a water wheel for success.

Any physically valid solution satisfying the functional goal is acceptable.

---

# 31. Automated Blind Benchmark

The same playable scenario must also be executable headlessly as a benchmark.

Success should be functional.

For example:

- environmental energy captured,
- target repeatedly receives useful mechanical work,
- human/animal energy remains below threshold,
- behavior persists for N simulation steps.

The evaluator must not check for named inventions.

---

# 32. Impossible Scenario

Add an automated scenario requesting sustained net useful energy with no energy input while conservation is enabled.

The Engineer may attempt it.

The simulator must prevent physical violation.

Failure should emerge from energy accounting.

Do NOT hard-code a textual rule saying:

"perpetual motion is impossible."

---

# 33. Altered Universe Scenario

Run at least one physical task under different universe parameters.

For example:

gravity = 9.81

and:

gravity = 3.0

The same Engineer architecture must operate in both.

This tests whether the agent reasons from actual world properties.

---

# 34. Transfer Scenario

After one successful invention, give the Engineer another goal in the same playable world where previously discovered knowledge could help.

Compare:

- cold attempt,
- knowledge-enabled attempt.

Record:

- attempts,
- experiments,
- actions,
- reasoning calls,
- simulated time.

We want the first evidence that CIVITAS can accumulate technology.

---

# 35. Game UI Layout

Keep the UI simple.

A useful layout might be:

+------------------------------------------------------+
| CIVITAS                         Day 12   > 1x 5x 20x |
+--------------------------------------+---------------+
|                                      |               |
|                                      |   SELECTED    |
|                                      |   Engineer    |
|             WORLD                    |               |
|                                      |   Goal        |
|                                      |   Hypothesis  |
|                                      |   Plan        |
|                                      |   Design      |
|                                      |               |
+--------------------------------------+---------------+
| EVENTS                                               |
| ...                                                  |
+------------------------------------------------------+
| Tell Engineer what you want: [____________________]  |
+------------------------------------------------------+

This is only a conceptual suggestion.

Adapt it if a better layout fits the framework.

Prioritize:

1. world,
2. command interface,
3. current project,
4. causal events.

Avoid dashboard clutter.

---

# 36. Player Experience Requirement

The following experience should work by the end of the milestone:

1. I launch CIVITAS.
2. A small world appears.
3. I can pause/pan/zoom.
4. I select the Engineer.
5. I type an arbitrary physical goal.
6. The Engineer receives the goal.
7. A Project appears.
8. The Engineer inspects its environment/knowledge.
9. A hypothesis appears.
10. A structured design is proposed.
11. Agents/world actions begin.
12. Components appear through actual construction actions.
13. An experiment occurs.
14. The simulator determines the result.
15. I visibly observe success or failure.
16. On failure, the Engineer receives evidence.
17. It revises the design.
18. Another attempt occurs.
19. If successful, the design becomes persistent knowledge.
20. I can issue another goal without restarting the world.

This is the first actual CIVITAS gameplay loop.

---

# 37. Do Not Script the Demo

This requirement is extremely important.

Do NOT implement:

if player_prompt_contains("river"):
    start_water_machine_demo()

Do NOT implement predetermined animation sequences.

Do NOT create a hidden successful design specifically for the README example.

The visual experience must emerge from the same actions/events produced by the invention system.

If the Engineer fails spectacularly, that is acceptable.

An honest failure is more valuable than a scripted success.

---

# 38. Rendering Unknown Inventions

This deserves special attention.

CIVITAS cannot rely on predefined sprites for every invented object.

Implement a first generic visual grammar.

For example:

physical component
→ primitive geometry

connection
→ visible joint/line

rotation
→ orientation update

support
→ structural connection

container
→ enclosing geometry

material
→ visual material treatment

The exact representation can be crude.

But if an Engineer invents something the developers never anticipated, the client must still be capable of displaying its structure.

This is a fundamental requirement, not polish.

---

# 39. Performance

Do not optimize prematurely.

However:

- rendering should not control simulation speed,
- simulation tick rate should be separable from rendering FPS,
- reasoning calls must not freeze/corrupt the simulation,
- expensive cognition should be event-driven.

If live model calls are synchronous initially, handle the UI state cleanly and visibly indicate that the Engineer is thinking.

Do not allow repeated accidental model calls every frame.

---

# 40. Research/Debug Controls

In developer mode, allow useful inspection such as:

- pause on experiment,
- step simulation,
- inspect object properties,
- inspect constraints,
- inspect design graph,
- inspect knowledge,
- inspect event history.

Do NOT add god-mode world mutation unless clearly separated as a developer/testing tool.

---

# 41. Benchmark Metrics

Continue recording:

- success/failure,
- attempts,
- experiments,
- actions,
- design revisions,
- constraint violations,
- resource consumption,
- simulated time,
- reasoning calls,
- model tokens/cost when available,
- reusable knowledge created.

Do not collapse these into one arbitrary score.

---

# 42. Testing

Automated tests must cover:

- deterministic simulation,
- replay,
- UI-independent kernel,
- action validation,
- structured model outputs,
- invalid proposal rejection,
- invention loop,
- design lineage,
- experiment evidence,
- knowledge persistence,
- unknown vs impossible,
- benchmark evaluation,
- save/load if implemented.

At least one integration test must demonstrate that a generic composition can produce useful behavior without a dedicated class representing the resulting invention.

---

# 43. Architectural Honesty

If the current ontology cannot represent something necessary for the playable invention loop:

DO NOT fake it in the UI.

Instead:

1. identify the missing abstraction,
2. determine whether it is general,
3. document it,
4. implement the smallest reusable primitive,
5. test that primitive independently,
6. then return to the scenario.

Never let visual presentation hide simulation limitations.

---

# 44. Documentation

Update README.md with:

## Run CIVITAS

Exact installation instructions.

Exact command.

Required Python version.

Optional model configuration.

Example:

`python -m civitas play`

## First Experiment

Provide the suggested natural-language goal.

## Controls

Document:

- pan,
- zoom,
- pause,
- speed,
- select,
- command input,
- debug overlay.

## Architecture

Explain clearly:

> The Pygame client is only a visualization/control layer. The deterministic simulation kernel remains authoritative.

---

# 45. Research Log

Maintain:

`research/EXPERIMENTS.md`

Record serious invention runs.

Create:

`research/MILESTONE_2_REPORT.md`

At the end answer:

A. Can I actually launch and play CIVITAS?

B. Can I enter a goal that was not hard-coded?

C. What did the Engineer design?

D. Did the design physically exist in the simulated world?

E. Did I visually observe the experiment?

F. Did simulation independently determine success/failure?

G. Did failure lead to revision?

H. Did successful knowledge persist?

I. Did that knowledge transfer to another task?

J. Was any solution-specific knowledge accidentally encoded?

K. Which parts are genuine simulation versus current abstractions/placeholders?

L. What is preventing the experience from feeling like the CIVITAS vision?

Be extremely honest.

---

# Definition of Done

Milestone 2 is complete when all of the following are true:

1. `python -m civitas play` launches a graphical CIVITAS world.
2. The graphical client uses the same kernel as headless benchmarks.
3. I can navigate the world and select an Engineer.
4. I can type an arbitrary natural-language physical goal.
5. That goal creates a persistent Project.
6. The Engineer reasons through a constrained API.
7. All actionable model output is structured and validated.
8. The Engineer can propose a generic Design.
9. Construction occurs through simulation Actions.
10. The resulting structure is visible without requiring a dedicated invention sprite/class.
11. Experiments occur in the simulated world.
12. The simulator independently determines outcomes.
13. Failures produce structured evidence.
14. The Engineer can revise failed designs.
15. Design lineage is preserved.
16. Successful discoveries become persistent Knowledge.
17. Previously learned knowledge can be used in another task.
18. At least one impossible request fails because of universe constraints.
19. At least one altered-universe experiment can run.
20. The same scenarios can run headlessly.
21. Runs remain inspectable/reproducible.
22. Automated tests do not require paid model calls.
23. No target invention is hard-coded.
24. The README explains exactly how to play.
25. `MILESTONE_2_REPORT.md` documents what genuinely works and what does not.

---

# Final Perspective

At the end of this milestone I do NOT want a benchmark suite with a pretty wrapper.

I want the first tiny version of CIVITAS.

It may be ugly.

It may contain only a river, rocks, materials, a few agents, and an Engineer.

The Engineer may fail often.

That is acceptable.

What matters is that I can sit in front of the running world and type:

> "I want something that does X."

and then watch inhabitants attempt to transform that idea into physical reality using only what their universe permits.

The sequence:

PLAYER IDEA
    ↓
AGENT UNDERSTANDING
    ↓
DESIGN
    ↓
PHYSICAL ACTION
    ↓
EXPERIMENT
    ↓
FAILURE / SUCCESS
    ↓
LEARNING
    ↓
NEW WORLD KNOWLEDGE

must be real.

Not scripted.

Not a cutscene.

Not an LLM pretending something happened.

That is the first playable CIVITAS.

Stop after completing Milestone 2 and its report.

Do not begin Milestone 3 automatically.