# Experiment log

Recorded 2026-10-18. Windows, Python 3.13.3, optional Pygame 2.6.1.
All committed physical results use deterministic kernel actions and verified
replay. No paid API requests were made.

## Shared laboratory, offline provider, seed 42

Command: `python -m benchmarks.engineer.run`.
Reference measurements: [engineer-42-summary.json](engineer-42-summary.json).
Complete journals/traces regenerate in `runs/engineer-42/`.

| Case | Independent outcome | Actions | Experiments | Design attempts | Reasoning artifacts | Simulated seconds | Effort J |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 kg, two 1 m raises | Pass | 16 | 5 | 5 | 12 | 57 | 63 |
| Zero source energy | Fail, known infeasible | 3 | 1 | 1 | 4 | 8 | 41 |
| Gravity 3 m/s² | Pass | 16 | 5 | 5 | 12 | 57 | 63 |
| Second 80 kg load, cold | Pass | 20 | 8 | 8 | 17 | 66 | 21 |
| Second 80 kg load, knowledge enabled | Pass | 6 | 1 | 1 | 3 | 38 | 14 |

Actions include experiment actions, but exclude project lifecycle/reasoning and
the two initial inspection actions. All first-task feasible runs consumed 2 kg
stock. Transfer consumed no new stock. Every successful task created one scoped
discovery; the zero-energy task created none. Offline tokens/API fees are zero.

Inspected trace: failed reach connections do not appear in the world; accepted
connections survive later trial failures; attempted unsupported elevation is
rejected atomically; a later support relation permits measured displacement.
Two raises transfer 1,962 J to the 100 kg load from about 2,422.22 J source input.
Lowering dissipates potential energy and recovers none. Direct human work on the
load remains zero; construction and work-control effort total 63 J. The final
prototype has a source, shaped stock body and load, joined through generic force
and support relations. There is no dedicated class for the composite.

The impossible control receives a conservation bound, not a textual prohibition:
remaining environmental energy cannot produce the required environmental work.
This is a closed-model certificate, not a universal impossibility theorem.

Cold/warm transfer forks have identical physical states and resource balances.
Only access to prior measured design/discovery conclusions differs. Both retain
ordinary construction observations. This isolates retrieval's contribution
better than comparing a fully reset world to an already-built one, but remains
one authored public calibration, not a statistical or blind generalization claim.

## Additional input variation

`python -m civitas laboratory --goal "Raise the selected body by 0.5 m repeatedly, 3 times, using environmental energy" --output runs/variant-3x-half.json`

Passed its interpreted goal: three crossings, 1,471.5 J environmental work,
zero direct human work, 18 actions, 5 experiments, 77 simulated seconds. This
checks that numeric language controls outcomes without selecting a fixed
construction animation. It is not an independent held-out invention task.

## Original calibration suites

`python -m benchmarks.run_baseline --seed 42`: 0/4 successes, all replayed.
`python -m benchmarks.composition.run --seed 42`: feasible and gravity transfer
passed with the composition search; energy-limited control failed. Original
baseline hashes remain identical through regression tests. The original weak
baseline was not strengthened merely to improve its score.

## Local free model checks

Installed model: `qwen3-vl:2b`, Ollama on loopback, CPU inference. A minimal JSON
readiness request returned valid JSON in approximately 16 seconds. Full Engineer
requests encountered 120/180-second timeouts and an empty public response after
exhausting the generation budget. Internal thinking was not exposed or stored.
These attempts are honest integration failures, not substituted offline success.
The adapter uses compact structured decisions and separately validates any full
replacement proposal. Offline results above must not be attributed to this LLM.

The explicit ChatML raw transport subsequently returned a valid interpreted goal
in approximately 12.5 seconds. The next model response proposed a malformed
cognitive payload and was rejected; the project stopped with `unknown`, zero
physical actions and no invention claim. The accepted interpretation reported
919 input tokens and 130 output tokens, zero API fees. Its saved journal
`runs/local-engineer-structured.json` replayed successfully, final hash
`9cdbf0dfe7d4d6a23f8f779c727d626a3d2d4e626a606e6d2de4ee06094c0834`.
This establishes one real model-to-kernel proposal, not a successful LLM invention.

Timeout/invalid-output projects record their stop reason. Current counters count
accepted reasoning artifacts; tokens spent on a response that never completes
or fails parsing are unavailable in project metrics. This accounting limitation
must be fixed before comparing inference efficiency across providers.

## Client and architecture verification

`python -m civitas play --smoke-frames 3 --screenshot runs/play-initial.png`
launched and closed the actual Pygame window. A completed saved world also
rendered successfully. Automated client tests submit through the text-input
handler, run the same Engineer, exercise read-only panels/debug rendering,
selection, camera and pause. Screenshots under `runs/` are local inspection
artifacts, not required test fixtures. No external sprite assets were needed.

A real window was also run at 20x through the text-input handler, with its
asynchronous scheduler and event pump active. Failure and completed-state
screenshots were captured and inspected (`runs/play-live-failure.png` and
`runs/play-live-completed.png`). The saved graphical run (`runs/play-live.json`)
replayed and matched the headless feasible run exactly:
`144e81370e648384355c33e3a83a9bef5d736ae4fdbfc5f097ac00fece45065a`.

See [MILESTONE_2_REPORT.md](MILESTONE_2_REPORT.md) for the research interpretation
and remaining restrictions.

Final full-suite verification: **72 tests passed**. This includes optional client
tests, asynchronous cancellation, raw local transport validation, property-label
independence, numeric goal variation and preserved 0.1 reference hashes.
