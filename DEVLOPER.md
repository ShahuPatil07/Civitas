# Coding-agent handoff — DEVLOPER.md

The filename is intentionally `DEVLOPER.md` (user request). **Keep it current at
every timepoint**: after each meaningful chunk of work, before stopping, and
before every commit/push. It always has exactly these two living sections.

Standing constraints: CIVITAS must stay **completely free** (free tiers or local
models only, never paid usage; kernel rejects cost ≠ 0). LLMs propose, the
kernel disposes (AIM.md). No named invention classes or recipes.

---

## 1. Recent work (2026-10-19)

**Free cloud language backends + multi-step free text** (on top of the earlier
task-understanding milestone: effort guard, energy certificates, honest replies).

- `civitas/llm.py`: OpenAI-compatible backend with free-tier presets
  (`ovh` keyless, `groq`, `cerebras`, `gemini`, `openrouter` `:free` only,
  `ollama-cloud`), local `OllamaBackend`, `FallbackBackend`, `backend('auto')`
  = configured free keys → keyless OVH → local Ollama. Rotates models on 429,
  waits on Retry-After within a cap, drops unsupported optional parameters.
- `civitas/language.py`: the model translates free text into ordered outcome
  steps (closed JSON schema). Each step is rendered as a **canonical grammar
  sentence** and must round-trip through `parse_offline`, so the deterministic
  grammar remains the only compiler to goals. Literal checks: single step uses
  `intents.consistency`; multi-step must use every stated distance. ≤2 repairs.
- `Laboratory.instruct(text)`: grammar first (no model call when it covers the
  text or refuses deliberately), else translator → plan recorded as a kernel
  **Idea** (`civitas-task-1`) → steps run as consecutive projects, stopping at
  the first failure. Async in the GUI; cancel discards late translations; the
  agenda is rebuilt from the journal on load (`_recover_agenda`).
- Grammar: `to x = N m` absolute horizontal destinations (negative allowed);
  `covered(..., multistep=True)` routes compound/two-axis requests to the
  translator when one exists.
- `InterpreterProvider` (per-project model interpretation) **removed**; the
  translator supersedes it. `--provider` is now only `offline|local`.
- CLI: `--language {auto,none,ovh,groq,cerebras,gemini,openrouter,ollama-cloud,ollama}`,
  `--language-model`. GUI shows the language backend, "reading your request",
  and the plan with per-step status.
- Research: `research/FREE_LLM_OPTIONS.md` (GitHub Models found retired,
  Pollinations needs a key, OpenRouter needs a key, OVH works keyless).

- Live-found fixes: restriction-cue guard (a model read "heave" as "by hand"),
  material in object list, model rotation on timeouts / spent output budget,
  GUI header names both planner and language backend.

Verified: **102 tests pass**; offline matrix 29/29; foundation hashes unchanged;
GUI live smoke: two-step plan executed and measured. Live keyless OVH language
matrix **16/17** (run 1 before fixes: 11/17); details in
`research/TASK_UNDERSTANDING_REPORT.md`. Not verified live: Groq, Gemini,
OpenRouter, Cerebras, Ollama Cloud presets (no keys on this machine; mocked
tests only).

## 2. Next update plans (ordered)

1. **Agentic Engineer on fast free models.** Make `LocalProvider` (decision
   mode) backend-agnostic so Groq/OVH models can propose hypotheses, designs and
   diagnoses, not only translate. Measure against the bounded planner on the
   existing benchmarks (success, actions, experiments, tokens, seconds).
2. **Tool-calling protocol.** Expose kernel affordances (observe, shape,
   connect, work, experiment) as typed tools with the same validation, so a
   model can run a short agent loop per project with a hard call budget.
3. **Ideas as world objects.** Ideas now hold player requests; extend to NPC
   proposals, propagation between agents, and lineage (AIM §7, §15).
4. **Planner limits**: move elevated loads (lower → re-support → lift → move),
   more than 3-body paths, mass/geometry choices beyond fixed 2 kg stock.
5. **Second agent + simple society primitive** (exchange or request) so
   language can address agents, not only objects.
6. Verify keyed presets live once free keys exist (Groq first); keep
   `research/FREE_LLM_OPTIONS.md` re-verified; add per-backend latency and
   success numbers from `python -m benchmarks.engineer.tasks --language-cases`.

## Commands

```console
python -m unittest discover -q
python -m benchmarks.engineer.tasks                                    # offline matrix
python -m benchmarks.engineer.tasks --language-cases --backend ovh     # live, keyless
python -m civitas laboratory --goal "Raise the stone by 40 cm and then drop it back down"
python -m civitas play                                                 # GUI, --language auto
```
