# CIVITAS — AIM.md

> This file defines the architectural philosophy and long-term objective of CIVITAS.
>
> Every coding agent, contributor, and future implementation decision should refer back to this document.
>
> **Do not optimize for implementing individual game features at the expense of the general simulation.**

---

# 1. The Vision

CIVITAS is an AI-native civilization sandbox in which players and simulated inhabitants can conceive of things that were never explicitly implemented by the game's developers.

The central promise is:

> **If you can explain it, your civilization can try to create it.**

A player should eventually be able to describe an amusement park, a new political system, a mechanical invention, a company, a sport, a school system, a financial institution, or another novel concept without that concept existing as a predefined game entity.

The simulation should attempt to ground the idea in the rules, resources, knowledge, agents, and institutions of the current world.

CIVITAS is therefore NOT primarily:

- a city builder,
- a scripted technology-tree game,
- a collection of LLM-powered NPC conversations,
- a text-to-prefab generator,
- or a game where natural language selects predefined actions.

It is an attempt to build a **programmable civilization sandbox**.

Natural language communicates intent.

The simulated universe determines consequences.

---

# 2. The Fundamental Rule

## LLMs propose. The world disposes.

Generative models may:

- interpret intent,
- reason,
- propose plans,
- design objects,
- formulate hypotheses,
- communicate,
- negotiate,
- generate candidate institutions,
- diagnose failures.

Generative models must NOT be authoritative about world state.

An LLM cannot declare:

> "The bridge is structurally sound."

It may propose a bridge design.

The simulation determines whether the bridge is structurally sound.

An LLM cannot declare:

> "The amusement park was profitable."

Agents, prices, demand, costs, and the economy determine whether it was profitable.

An LLM cannot declare:

> "The population supports this law."

Individual agents determine their reactions.

**Truth belongs to the simulation kernel.**

---

# 3. Do Not Hard-Code Emergent Concepts

Whenever implementing a feature, ask:

> Am I implementing a general primitive, or am I hard-coding one example of something that should emerge?

Avoid functions such as:

```text
build_amusement_park()
create_bank()
invent_ferris_wheel()
start_revolution()
create_religion()
form_democracy()
```

These are outcomes, not primitives.

Prefer reusable operations and representations from which such outcomes could emerge.

The existence of a concept in a test scenario is NOT sufficient justification for adding that concept to the engine.

If a test asks agents to invent a water wheel, do not implement a `WaterWheel` entity merely to pass the test.

The correct question is:

> What missing general primitive prevents the system from independently representing a water wheel?

---

# 4. The Five Layers

CIVITAS should conceptually separate five layers.

## Layer 1 — Universe

Defines fundamental rules.

Examples:

- space,
- time,
- gravity,
- available matter,
- energy behavior,
- environmental rules,
- tunable physical constants.

Universe rules should eventually be configurable.

Different universes may have different physical parameters.

The initial implementation should remain intentionally small.

Do NOT attempt atomic-scale or molecular-scale simulation merely because real elements exist.

---

## Layer 2 — Physical World

Represents physical entities and interactions.

Objects should be defined primarily through properties, components, relationships, and affordances rather than human-readable labels.

Relevant concepts may include:

- material,
- mass,
- geometry,
- position,
- temperature,
- structural strength,
- friction,
- tension,
- compression,
- rotation,
- containment,
- connectivity,
- energy,
- damage.

Simulation fidelity should be only as high as necessary for meaningful gameplay.

CIVITAS seeks **semantic physical consistency**, not perfect physical simulation.

---

## Layer 3 — Knowledge

Reality and knowledge of reality are different.

The universe may permit something that no civilization currently knows how to produce.

Maintain a conceptual distinction between:

### World truth

What is actually possible according to simulation rules.

### Agent knowledge

What an individual believes, understands, or knows.

### Civilization knowledge

Knowledge that has propagated sufficiently through society.

Knowledge can be:

- discovered,
- forgotten,
- misunderstood,
- taught,
- stolen,
- independently rediscovered,
- combined,
- improved.

There should eventually be no mandatory fixed technology tree.

Technological history should be path-dependent.

---

## Layer 4 — Society

Society provides mechanisms for coordination between agents.

Examples include:

- ownership,
- exchange,
- labor,
- organizations,
- contracts,
- authority,
- law,
- norms,
- markets,
- governance.

Avoid assuming modern institutions are universal primitives.

For example, "bank" should ideally be an emergent organization implementing more primitive economic relationships.

---

## Layer 5 — Cognition

Agents:

- observe,
- remember,
- reason,
- communicate,
- plan,
- act,
- learn.

Agents should possess incomplete information.

Agents should not have direct access to global world state unless a mechanism in the world gives them that information.

Different agents may hold contradictory beliefs.

---

# 5. Affordances Over Names

One of CIVITAS's most important abstractions is the AFFORDANCE.

An object's name should not determine what can be done with it.

Instead, physical properties expose possibilities.

Examples:

A rope may:

- transfer tension,
- connect objects,
- suspend objects,
- pull objects.

A wheel may:

- rotate around an axis,
- support loads,
- transfer motion.

A rock may:

- support weight,
- transfer force,
- be shaped,
- be thrown,
- fracture.

This allows agents to reason compositionally.

Novel inventions should arise by combining existing capabilities.

---

# 6. Composition Is the Core Mechanic

Minecraft obtains expressiveness through composition of simple blocks.

CIVITAS should obtain expressiveness through composition of:

- matter,
- physical affordances,
- information,
- knowledge,
- agents,
- organizations,
- rules,
- incentives.

Complex systems should ideally be compositions of simpler systems.

The engine should favor:

> small number of expressive primitives

over:

> large number of predefined game entities.

---

# 7. Ideas Are First-Class World Objects

An idea is not merely text stored in an LLM conversation.

Ideas should have persistent representation.

An idea may contain:

- origin,
- description,
- purpose,
- conceptual components,
- known requirements,
- unknown requirements,
- evidence,
- associated designs,
- agents who know it,
- confidence,
- revisions,
- lineage from previous ideas.

Ideas can propagate between agents.

During propagation they may mutate or be misunderstood.

Ideas may lead to:

- research,
- designs,
- institutions,
- actions,
- other ideas.

---

# 8. Designs Are First-Class Objects

When agents invent something, the result should become persistent structured knowledge.

A design should represent:

- components,
- component relationships,
- required materials,
- required capabilities,
- constraints,
- construction procedure,
- known failure modes,
- performance evidence,
- version lineage.

A design should NOT merely be generated prose.

A design should be interpretable by the simulation.

Designs may be:

- constructed,
- tested,
- copied,
- taught,
- stolen,
- modified,
- combined,
- improved.

---

# 9. Use an Intermediate Representation

Natural language must NOT directly mutate arbitrary simulation state.

Preferred conceptual pipeline:

```text
Natural Language
      ↓
Intent / Concept Interpretation
      ↓
Structured CIVITAS Representation
      ↓
Planning
      ↓
Primitive Actions
      ↓
Simulation Kernel
      ↓
Events / Consequences
```

CIVITAS should develop constrained intermediate representations for concepts such as:

- intent,
- plans,
- physical designs,
- experiments,
- organizations,
- contracts,
- laws.

Do NOT solve open-endedness by allowing models to generate and execute arbitrary code.

---

# 10. Oracles

Complex reasoning should be separated from ordinary agent simulation.

Potential specialized reasoning systems include:

- Engineer Oracle
- Scientist Oracle
- Economist Oracle
- Legal / Justice Oracle
- Architect Oracle
- Strategic Oracle

An Oracle is NOT omniscient.

It must receive only information legitimately available in the context where it is invoked.

An Oracle proposes reasoning or solutions.

It does not override the simulation.

Ordinary agents should remain comparatively lightweight.

Use expensive reasoning selectively.

---

# 11. Agent Scalability

The long-term goal may involve thousands of agents.

Therefore:

**Do not architect the game around one frontier-model invocation per agent per simulation tick.**

Prefer hierarchical cognition.

Possible tiers:

### Tier 0 — deterministic behavior

Routine actions.

### Tier 1 — lightweight policies

Common decisions.

### Tier 2 — local/small model reasoning

Moderately novel situations.

### Tier 3 — expensive reasoning / Oracle

Rare difficult decisions.

Expensive intelligence should be event-driven, not continuously invoked.

---

# 12. Events, Not Constant LLM Simulation

The simulation should be event-driven wherever practical.

Important events may include:

- resource shortage,
- design failure,
- conflict,
- new information,
- contract proposal,
- unexpected physical event,
- discovery,
- social dispute,
- goal obstruction.

Events may trigger deeper reasoning.

Most routine world evolution should remain deterministic or inexpensive.

---

# 13. Failure Is Essential

Player intent must not imply success.

Projects may fail because of:

- impossible physics,
- insufficient knowledge,
- missing materials,
- inadequate manufacturing,
- insufficient labor,
- lack of funding,
- social resistance,
- poor demand,
- political opposition,
- design flaws,
- accidents,
- misunderstanding.

Failure should produce information.

A failed experiment may create knowledge.

A failed structure may expose a missing engineering principle.

A failed company may change economic beliefs.

Failure should often advance the simulation rather than simply terminate an action.

---

# 14. Discovery Must Be Possible

The engine must distinguish:

> impossible

from:

> possible but currently unknown.

Agents should be able to formulate hypotheses and perform experiments.

Conceptual loop:

```text
observation
    ↓
hypothesis
    ↓
experiment
    ↓
simulation
    ↓
evidence
    ↓
belief update
    ↓
new knowledge
```

Scientific discovery should ultimately emerge from this mechanism.

---

# 15. NPCs Must Also Invent

The player cannot be the only source of novelty.

Agents should eventually:

- identify problems,
- propose solutions,
- design objects,
- run experiments,
- create organizations,
- modify existing designs,
- combine ideas.

Player-created ideas may inspire unrelated discoveries.

NPC discoveries may fundamentally change the player's civilization.

CIVITAS should be capable of surprising its developers.

---

# 16. Matter and the Periodic Table

Long-term, the physical universe may use real or fictional elemental foundations.

However:

**Do not begin by simulating chemistry from first principles.**

Early prototypes should use a small material set such as:

- wood,
- stone,
- iron,
- steel,
- copper,
- glass,
- water,
- cloth,
- rope,
- soil.

Materials should expose gameplay-relevant properties.

Later implementations may derive materials from elemental composition.

The abstraction must permit this evolution without requiring the entire simulation to be rewritten.

---

# 17. Tunable Physics

Universe parameters should eventually be configurable.

Examples:

- gravity,
- atmospheric properties,
- thermal behavior,
- energy availability,
- material properties.

Changing a universe parameter should change consequences rather than merely visuals.

A low-gravity universe should permit structures or machines that an Earth-like universe does not.

Do not prioritize exotic universes before the Earth-like simulation demonstrates open-ended invention.

---

# 18. Rendering Is Not the Simulation

The simulation must not depend on a graphical client.

Architecture should allow:

```text
Simulation Server / Kernel
          ↕
       Game Client
```

The simulation should be runnable headlessly.

A command such as:

```text
simulate --steps N
```

should eventually be capable of evolving a world without rendering it.

Graphics visualize simulation state.

Graphics do not define simulation truth.

---

# 19. The First Research Milestone: The Unseen Object Test

Before building a large city, prove open-ended invention.

Construct a minimal world containing approximately:

- 5 agents,
- 10 materials,
- basic semantic physics,
- basic knowledge representation,
- one Engineer Oracle,
- a small set of primitive actions,
- minimal resource/economic constraints.

Then request an invention whose implementation does NOT exist anywhere in the repository.

Example:

> "Create a machine that uses flowing river water to repeatedly lift heavy stones onto a raised platform."

The repository must NOT contain:

- WaterWheel,
- water-wheel recipes,
- hard-coded solution plans,
- hidden aliases implementing the expected answer.

A successful system should:

1. interpret the goal,
2. inspect available knowledge,
3. identify useful physical affordances,
4. generate candidate designs,
5. determine missing knowledge,
6. obtain materials,
7. construct components,
8. assemble a prototype,
9. simulate its behavior,
10. observe failure or success,
11. diagnose failures,
12. modify the design,
13. eventually produce a functional solution if feasible,
14. persist the resulting design as new knowledge,
15. reuse principles from that design in a later unrelated task.

---

# 20. Generalization Tests

Do not evaluate the system solely on examples used during development.

Maintain hidden invention scenarios.

Potential categories:

- mechanical device,
- structure,
- transportation mechanism,
- economic organization,
- legal institution,
- recreational activity.

The engine succeeds when the same primitives generalize across previously unseen concepts.

Avoid adding scenario-specific primitives after observing failures unless the missing primitive is genuinely universal.

---

# 21. Anti-Cheating Principle

When an invention succeeds, ask:

> Did the simulation actually derive this solution, or did the language model already know the named object and reproduce it?

Tests should sometimes describe goals without naming known inventions.

Bad test:

> Build a water wheel.

Better test:

> Use the movement of the river to continuously rotate a shaft without requiring a person or animal to turn it.

Best tests should include genuinely unusual combinations unlikely to correspond directly to memorized named objects.

---

# 22. Current Priority Order

Until explicitly changed, optimize development in this order:

1. General world representation
2. Affordance system
3. Deterministic simulation kernel
4. Structured intent representation
5. Structured design representation
6. Knowledge representation
7. Engineer Oracle
8. Invention planning
9. Construction through primitive actions
10. Failure and feedback
11. Design iteration
12. Persistent discoveries
13. Lightweight agents
14. Basic economy and society
15. Visualization
16. Larger populations
17. Additional Oracles
18. Rich graphics
19. Detailed chemistry
20. Exotic universes

Do not reverse this order merely because later features are easier to demo.

---

# 23. What We Are NOT Building Yet

Unless required by the current milestone, do NOT spend significant development time on:

- detailed graphics,
- procedural terrain,
- thousands of NPCs,
- combat,
- multiplayer,
- detailed character customization,
- realistic atomic chemistry,
- fluid simulation,
- complete economics,
- political simulation,
- historical content,
- huge maps,
- dialogue polish,
- predefined technology trees,
- large catalogs of buildings/items.

These may eventually matter.

They do not prove the central thesis.

---

# 24. Architectural Test for Every New Feature

Before implementing a feature, answer:

### A. Is this a primitive or an outcome?

If it is an outcome, prefer implementing the primitives that permit it to emerge.

### B. Could another unrelated feature reuse this abstraction?

If not, reconsider the design.

### C. Does this give the LLM authority over simulation truth?

If yes, move authority into deterministic simulation.

### D. Does this require a predefined concept that agents should be able to invent?

If yes, redesign it.

### E. Would this still work for an object/concept the developers have never heard of?

If not, the abstraction may be too narrow.

---

# 25. Coding-Agent Instructions

When working on CIVITAS:

1. Read this file before making architectural changes.
2. Preserve the separation between generative reasoning and deterministic simulation.
3. Do not add hard-coded high-level concepts merely to complete a requested demo.
4. Prefer small composable primitives.
5. Keep simulation modules independent of rendering.
6. Keep world state structured and inspectable.
7. Make important model outputs structured and schema-validated.
8. Record causal simulation events so behavior can be debugged.
9. Make stochastic behavior reproducible through seeds where possible.
10. Write tests for primitives and emergent composition.
11. When uncertain between a convenient special case and a reusable abstraction, prefer the reusable abstraction.
12. Do not prematurely optimize simulation fidelity.
13. Do not prematurely introduce distributed infrastructure.
14. Document assumptions.
15. Explicitly flag any implementation that compromises the principles in this document.

---

# 26. The Ultimate Test

CIVITAS succeeds when this interaction is possible:

A player expresses an idea that:

- the developers did not anticipate,
- has no dedicated implementation,
- has no predefined recipe,
- and has never previously existed in that world.

Agents understand enough of the idea to investigate it.

They determine what they know and what they do not know.

They reason using existing physical, economic, and social capabilities.

They experiment.

They fail.

They learn.

They construct something.

The simulation determines whether it works.

The resulting knowledge persists.

Other agents encounter it.

They copy it.

They modify it.

They combine it with other discoveries.

Eventually the world contains technologies, organizations, customs, structures, and histories that were never authored by the game's developers.

At that point, CIVITAS is no longer a game containing a fixed possibility space.

**It is a game whose possibility space expands while it is being played.**

That is the project.