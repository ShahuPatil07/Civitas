# CIVITAS research foundation

A Python standard-library-only, headless substrate for testing compositional
invention. Read [AIM.md](AIM.md) and [the architecture](docs/ARCHITECTURE.md) before
extending it. This implements the foundation, not the Engineer or the completed
Unseen Object Test. There is no graphical engine, model integration or game loop.

## Run from the repository root

Python 3.11+ is required. No installation or third-party packages are needed.

```console
python -m unittest discover -v
python -m civitas benchmark list
python -m civitas benchmark inspect mechanical
python -m civitas benchmark run mechanical --solver baseline --seed 42
python -m civitas replay runs/mechanical-42.json
python -m benchmarks.run_baseline --seed 42
python -m benchmarks.composition.run --seed 42
```

The suite runner saves complete runs, readable traces and a summary under
`runs/baseline-42/`, then replays each saved JSON file. Ordinary benchmark failure
is a research result and exits successfully; malformed commands or replay
divergence exit with code 2. `--output PATH` chooses a run file, or a suite folder.
Default paths are overwritten when rerunning the same command.

## What is implemented

- An atomic kernel boundary with validated actions, causal events and replay.
- Ten configurable bulk materials; property-derived capacities and affordances.
- Shaping, generic force/rotation/support/containment relations, bounded work.
- Per-agent observations and beliefs, persistent designs/ideas and experiments.
- Three-state constraint evaluation, four outcome-based research scenarios,
  a weak non-LLM baseline and an observation-only solver port.

`World` is the trusted researcher interface. Cognition receives `AgentPort` and a
public task. Neither mutable snapshots nor asserted beliefs grant world authority.
Python privacy is an API boundary, not a security sandbox.

## Read before extending

- [Architecture and ontology](docs/ARCHITECTURE.md)
- [Implementation checklist](docs/PRINCIPLES.md)
- [Benchmark authoring and hidden tests](docs/BENCHMARKS.md)
- [Decisions, shortcuts and unresolved questions](docs/DECISIONS.md)
- [Recorded baseline and trace inspection](docs/BASELINE.md)
- [Unnamed composition experiment and results](docs/COMPOSITION_EXPERIMENT.md)

Physics is explicitly coarse: discrete, scalar/quasistatic work and finite energy
reservoirs. It cannot yet represent autonomous cycles, moving assemblies or
general spatial mechanisms. Passing these tests would establish consistency
inside this model, not real-world engineering validity or open-ended invention.
