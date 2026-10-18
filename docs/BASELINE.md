# Baseline result and review

Recorded on 2026-10-18 using Python 3.13.3, rule version
`civitas-semantic-0.1`, seed 42. The implementation uses only the standard library.

## Verification

`python -m unittest discover -v`: **42 tests passed**. The tests cover action
schema validation, atomic rollback, detached state/history/views, scoped knowledge
and false beliefs, manufacturing knowledge gates, design serialization and
lineage, evidence provenance, resource conservation, physical capacity, friction,
force/power/energy limits, rotation, altered gravity, local observations, repeated
crossing accounting, successful and unsuccessful evaluation, budgets, CLI use,
tampering detection and replay of JSON artifacts for all four scenarios.

One composition test creates a stock segment and combines generic force-transfer
and support relations. A two-edge path raises a 10 kg load by 1 m, delivering
98.1 J while debiting 98.1 / 0.81 J from a finite source. It introduces no artifact
class. A separate calibration goal accepts both human and environmental work
paths. These demonstrate useful composition and evaluator flexibility within
the model; they do not demonstrate an agent independently inventing a design.

## Research benchmark results

Command: `python -m benchmarks.run_baseline --seed 42`

| Benchmark | Attempts / limit | Accepted | Experiments / limit | Success | Disk replay |
| --- | ---: | ---: | ---: | --- | --- |
| Mechanical transformation | 34 / 40 | 9 | 1 / 2 | No | Exact |
| Transportation | 34 / 40 | 18 | 1 / 2 | No | Exact |
| Structural | 27 / 40 | 12 | 1 / 2 | No | Exact |
| Novel environment | 27 / 40 | 14 | 1 / 2 | No | Exact |

Total: **0/4 successes, 122 attempts, 53 accepted actions, 69 rejections**. Each
scenario's final experiment was accepted as a measurement action and recorded
an unsuccessful hypothesis. Attempt budgets were respected. Counts and full
digests are in the [machine-readable reference](../benchmarks/results/baseline-42-summary.json).
These are single-seed reference results, not statistically meaningful estimates.

## Trace inspection

- [Mechanical trace](../benchmarks/results/mechanical-42.txt): the baseline shaped
  two components and made several connections, but the load had no viable support
  for the attempted raise. Human force was insufficient. Other failures exposed
  insufficient structural capacity, unavailable property affordances and reach
  limits. Final complete raises: 0; environmental work delivered to the load: 0 J.
- [Transportation trace](../benchmarks/results/transportation-42.txt): environmental
  work moved some created components, but the target remained at x=0. The baseline
  made the target a loaded anchor, which v0 cannot move; short connections also
  blocked displacement. Total effort was 363.905 J against the 100 J bound.
- [Structural trace](../benchmarks/results/structural-42.txt): the fixed 2 m stock
  geometry did not span the 3 m task distance. Relations failed on reach, existing
  load-bearing assignments or unsupported nesting. Target elevation and measured
  bearing span remained 0. The baseline has no geometry refinement or undo step.
- [Novel-environment trace](../benchmarks/results/novel_environment-42.txt): the
  agent successfully raised the 100 kg load to 2 m under gravity 2 m/s². However,
  shaping, connection and motion effort totalled 992.4 J, above the 700 J limit.
  The evaluator correctly rejected the overall result despite physical progress.

All four complete JSON runs and matching readable traces are retained locally
under `runs/baseline-42/`. Full runs are ignored by Git because state-rich events
are verbose; the summary and readable reference traces are kept in the source
tree. Regenerate them with the command above. Replay checks the actual saved
JSON file, including rejected requests, knowledge changes, event effects and
final benchmark outcome. Repeating the suite produced the same final digests.

## Interpretation and next review

The substrate runs, rejects invalid proposals with structured reasons, supports
property-based composition and persists research records without trusting their
claims. The weak baseline exercises physical construction, work and measurement
without a model or privileged truth access. Its failure does not establish that
the tasks are impossible or that the physics is sufficient for unseen inventions.

The sharpest current restrictions are independent scalar transmission paths,
immobile loaded anchors, fixed observation positions, coarse support/containment,
and the absence of environmental energy conversion, disassembly and design symbol
binding. All **20 decision/shortcut groups**, along with unresolved questions,
are explicitly recorded in [DECISIONS.md](DECISIONS.md). No named target invention,
recipe, alias or scenario-specific physical rule was added.

The recommended next experiment is a held-out unnamed composition with bounded
deterministic search, a feasible and impossible control, and persisted design
lineage tied to measured evidence. Freeze the kernel and test transfer under one
changed property before integrating an Engineer. **That experiment has not been
started.**

This report describes the foundation checkpoint. The user subsequently authorized
the [unnamed composition experiment](COMPOSITION_EXPERIMENT.md), which now has
separate results. These original baseline results remain unchanged.
