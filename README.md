# CIVITAS

A small playable invention laboratory. Describe a goal to an Engineer, watch
property-based components get shaped and connected, inspect failed experiments,
and reuse measured designs in the same world. Read [AIM.md](AIM.md) before
extending the ontology.

## Current status — free-text Engineer, 2026-10-19

Type a task in your own words. The Engineer turns it into measurable goals,
executes them only through validated kernel actions, and replies with an
honest outcome: `succeeded` (kernel-measured), `proven_infeasible` (kernel
energy certificate), `clarify`, `unsupported`, `boundary`, `missing_resource`,
`capability_limit`, `not_found` (search/limit exhausted, *not* a proof),
`budget_exhausted` or `provider_failed`. **102 tests pass**
(`python -m unittest discover -q`). Results:
[research/TASK_UNDERSTANDING_REPORT.md](research/TASK_UNDERSTANDING_REPORT.md);
free model survey: [research/FREE_LLM_OPTIONS.md](research/FREE_LLM_OPTIONS.md);
handoff: [DEVLOPER.md](DEVLOPER.md).

### How free text is understood

1. A deterministic **grammar** handles plain commands ("Lift the selected object
   50 cm", "Move the 80 kg object 1 m to the left") with no model and no network.
2. Anything else goes to a **free language model**, which may only return
   ordered movement steps in a closed JSON schema. Each step is rewritten as a
   canonical grammar sentence and must parse back to exactly the same outcome,
   so the grammar remains the only compiler to goals, and you can read the plan
   ("1. Lift the selected object 0.4 m  2. Move the selected object to a height
   of 0 m"). Readings that contradict your words — wrong distance, direction,
   axis, invented "by hand" or repetitions — are rejected and repaired (≤ 2).
3. The plan is stored in the world as an **Idea** and its steps run as
   consecutive projects, stopping at the first failure. Saves replay without
   any model call.

### Free language backends (`--language`)

| Value | Needs | Notes |
|---|---|---|
| `auto` (default) | nothing | your free keys below if set, else **keyless OVHcloud**, else local Ollama |
| `ovh` | nothing | OVHcloud AI Endpoints anonymous tier: gpt-oss-120b, Qwen 3.x; ~2 req/min per model |
| `groq` | free `GROQ_API_KEY` (no card) | fastest free tier |
| `openrouter` | free `OPENROUTER_API_KEY` | `:free` models only (enforced), 50 req/day |
| `gemini` | free `GEMINI_API_KEY` | small daily quota; keep billing disabled |
| `cerebras`, `ollama-cloud` | free keys | trial / starter allowances |
| `ollama` | local Ollama | private and offline, slow on CPU |
| `none` | nothing | grammar only, no network |

Cloud backends receive your request text and a summary of observed objects;
use `none` or `ollama` to stay local. Keys are read from environment variables
and never saved. No backend may incur fees; the kernel rejects non-zero cost.

## Run CIVITAS

Python **3.11+**. From this repository:

```console
python -m pip install -e ".[play]"
python -m civitas play
```

Pygame is the only optional client dependency. Headless experiments need only
Python's standard library and run without installing Pygame.

Examples:

```console
python -m civitas laboratory --goal "Raise the stone by 40 cm and then drop it back down"
python -m civitas play --language groq          # after setting a free GROQ_API_KEY
python -m civitas play --language none          # fully offline
```

`--provider local` is a separate, experimental mode in which a local Ollama
model chooses Engineer proposals inside a project (with a disclosed advisory
from the bounded planner). The default `--provider offline` uses the bounded
planner; every proposal passes the same validation either way.

## First experiment

The initially selected target is the 100 kg body. Click the command field and
press Enter for the prefilled measurable task, or clear it with Ctrl+A and type:

> Use the movement of the river to create something that repeatedly raises these heavy stones without requiring people to continuously lift them.

The first world supplies **finite mechanical energy**, not simulated river flow.
The offline interpreter explicitly interprets the selected body, 1 m elevation
and two cycles when quantities are unspecified. Read the interpreted goal in the
project panel. Unsupported requests remain unresolved. The interpreter does not
understand every nuance of arbitrary language.

Construction consumes stock, effort and simulation time. Failed attempts leave
already-constructed parts in place. Experiments determine status through frozen
numeric constraints. A successful experiment records a scoped discovery. Select
the other load and submit a second task to exercise knowledge reuse.

## Controls

| Control | Action |
| --- | --- |
| Left click body / agent | Select; body selection also chooses the goal target |
| Right drag / arrow keys | Pan |
| Mouse wheel over world | Zoom |
| Space, or Pause button | Pause/resume |
| 1 / 2 / 3, or buttons | 1x / 5x / 20x simulation pacing |
| Click input; Enter | Edit / submit a natural-language goal |
| Ctrl+A in input | Clear text |
| Escape outside input | Stop the current project |
| Project / Object / Knowledge / History tabs | Inspect goal, properties, claims and lineage |
| Wheel over panel / event feed | Scroll details / older events |
| [ / ] | Inspect previous/next persistent project |
| F3 | Clearly marked world-truth debug overlay |
| N | One controller step, including asynchronous reasoning |
| P | Pause after each experiment |
| F5 / F9 | Save / verified replay-load `runs/laboratory.json` |

Reasoning waits show a thinking indicator and do not block the window. A pause
prevents applying pending proposals until resumed. Save stores the committed
world; an in-flight model response is not included. Close does not auto-save.

Solid lines show constructed relations; dotted lines show proposed designs.
Bodies render from generic geometry, with orientation taken from kernel angles.
Motion is discrete; there are no invented physics animations. Four other agents
are passive observers. Gathering, agent walking and autonomous machines are not
implemented.

## Headless experiments and replay

```console
python -m civitas laboratory --output runs/my-experiment.json
python -m civitas laboratory --gravity 3 --output runs/low-gravity.json
python -m civitas laboratory --source-energy 0 --output runs/no-energy.json
python -m civitas replay runs/my-experiment.json
python -m civitas play --load runs/my-experiment.json
python -m benchmarks.engineer.run
python -m unittest discover -v
```

Use `--goal "..."` for another goal and `--provider local --model NAME` for local
reasoning in either interface. `--load` restores unfinished projects as well as
completed worlds. `--output` chooses the save path. Repeating a path overwrites it.
The suite writes complete JSON journals, readable traces and independent numeric
evaluations under `runs/engineer-42/`. Live model responses can vary between runs;
replay uses their recorded actions and requires no model.

The original research workflows are preserved:

```console
python -m civitas benchmark list
python -m civitas benchmark run mechanical --solver baseline --seed 42
python -m benchmarks.run_baseline --seed 42
python -m benchmarks.composition.run --seed 42
```

## Architecture

The Pygame client is only a visualization/control layer. The deterministic
simulation kernel remains authoritative. Provider output is data, never executed
Python. Projects, budgets, designs, experiment outcomes and knowledge changes
all pass through validated actions and journaled events.

- [Foundation ontology](docs/ARCHITECTURE.md)
- [Engineer, provider and client contract](docs/ENGINEER_ARCHITECTURE.md)
- [Implementation principles](docs/PRINCIPLES.md)
- [Benchmark authoring](docs/BENCHMARKS.md)
- [Decisions and explicit shortcuts](docs/DECISIONS.md)
- [Milestone 2 results and limitations](research/MILESTONE_2_REPORT.md)
- [Experiment log](research/EXPERIMENTS.md)

The physics remains deliberately coarse. Success establishes consistency within
that model, not real-world engineering validity or completion of the central
Unseen Object Test.
