# Can the Engineer understand and perform a specific task? (2026-10-19)

Scenario: `engineer_laboratory` (seed 42): 100 kg load at x=2, 80 kg load at
x=2.5, a 15 kJ mechanical source at x=0, Engineer with 600 J, 100 N, 100 W and
wood/iron/rope stock. All results below were measured by running the kernel.

## Offline matrix — `python -m benchmarks.engineer.tasks`: 29/29

Every case checks the expected reply category, an independent world-state
check (never the Engineer's own interpretation), save/replay hash equality and
four invariants: success ⇒ every frozen goal kernel-satisfied; an effort cap is
never exceeded; refusals perform no physical attempt; "impossible" requires a
kernel certificate.

| Group | Cases | Result |
|---|---|---|
| Units, number words, left/right, up, absolute heights, by-mass target, 10 m lift | 8 | succeeded, correct final positions |
| 3 environmental lifts (human work stays 0), already-satisfied target, effort ≤ 100 J | 3 | succeeded |
| Sequences in one world (lift→lower, lift→lift, right→left→lift, 2 m→1 m) | 4 | all succeed; later tasks reuse measured paths (4–5 actions vs 11–14) |
| Effort ≤ 20 J | 1 | `not_found`, refused before overspending (needs ≥ 52 J) |
| Lift by hand (981 J needed, 600 J held) / no source / 2.5 kJ for 3 lifts | 3 | `proven_infeasible` with energy certificate in ≤ 3 actions |
| Push 50 cm by hand (affordable energy, 687 N vs 100 N) | 1 | `capability_limit` |
| Lower below ground | 1 | `boundary`, 0 actions |
| Elevated load moved sideways | 1 | `not_found` (known limitation, below) |
| Negation, compound steps, two axes, energy conflict, ambiguous mass, "ferris wheel", "fly to the moon", extra clause "and paint it blue" | 8 | `clarify`, 0 actions |

## Historical: live local model (qwen3-vl:2b, superseded interpreter): 8/9

`qwen3-vl:2b` via loopback Ollama, CPU, ~6–12 s per request, $0. These phrases
are outside the offline grammar, so the model is actually invoked.

| Request | Outcome |
|---|---|
| "nudge the big rock a metre towards the left" | ✅ x 2→1 |
| "Slide the boulder 30 cm rightwards please" | ✅ x 2→2.3 (first reading was absolute x=0.3 — a move *left* — until the consistency check was added) |
| "shove the rock 40 centimetres to the right without using your own muscles" | ✅ x→2.4, human work 0 |
| "Heave the stone upwards by about one and a half metres" | ✅ z→1.5 after one guided repair |
| "Get the heavy block two meters off the floor" | ❌ refused (model: "already on the floor") — safe failure |
| Paint blue / build a bridge / carry to the moon / teleport | ✅ unsupported, 0 actions |

No live run executed a wrong movement. Results are model-dependent and should
be re-measured on another machine or model.

## Changes that made these results possible

- Kernel energy certificate generalised to conservation of energy over the
  remaining displacement and the energy channels the task permits.
- Project effort limits are hard preconditions in `step_project` (`effort_limit`).
- Planner prunes candidates whose published action costs exceed the limit, and
  lengthens duration after `inadequate_power`.
- Structured replies (`civitas/replies.py`) in CLI and GUI.
- Tiered interpreter (since replaced by the translator below); literal-consistency check with actionable repairs.
- Bug fixed: "one and a half metres" used to parse as 0.5 m in the grammar.

Foundation baseline (4/4) and composition (6/6) hashes are unchanged; the
original Engineer benchmark metrics are identical (warm transfer 6 actions /
1 experiment vs cold 20 / 8).

## Known limitations

- Grammar-only mode: one object, one axis, one movement per task (compound requests need a language backend, which splits them into steps).
- An elevated load cannot be moved sideways: its support cannot reach and v0
  forbids swapping a loaded support. Reported as `not_found`, not impossible.
- The 2B model over-refuses some valid phrasings; refusals are labelled as its
  judgement.
- "a metre"/"half a metre" are grammar gaps: offline mode asks to rephrase.

## Free cloud translator — `--language-cases --backend ovh` (2026-10-19, later the same day)

Keyless OVHcloud AI Endpoints (gpt-oss-120b, falling back to Qwen3.8-27B on
rate limits), 17 grammar-external requests including multi-step ones. The
model only returns steps; each is a canonical grammar sentence the player can
read; the kernel measures every result.

| Run | Result | Notes |
|---|---|---|
| 1 (before fixes) | 11/17 | "heave" read as *by hand* (kernel then proved it impossible); 5 kg source taken as "the lighter rock"; two 60 s timeouts; 2 checker bugs |
| 2 (after fixes) | **16/17** | only miss: "to the 4 metre mark" answered with a clarifying question (passed in run 1) |

Passing in run 2: a metre left, 30 cm rightwards, two metres off the floor, 40 cm
right without muscles (environmental energy, 0 human work), heave 1.5 m, raise
40 cm then drop back down (2 steps), 1 m left then another 50 cm (2 steps),
lighter rock (80 kg load), push 50 cm then "back where it started" (2 tasks),
and refusals for paint, bridge, moon, teleport, spin, ramp and a vague request.
Typical latency 2–8 s per request; 28–30 s when every model was rate limited.

Fixes made from these live failures: restriction cues (energy, effort,
repetition must be stated), observed material in the object list, rotation on
timeouts and on hidden-reasoning budget exhaustion, per-step invariants.
Outputs vary between runs (model sampling and fallback models), so treat single
runs as indicative; failures were safe (clarify/refuse) in run 2.
