# Free LLM options for CIVITAS (checked 2026-10-19)

Goal: good, fast language models at **zero cost to players**. Free tiers change
monthly; every row below was either probed from this machine on 2026-10-19
(**verified**) or taken from recent third-party reports (**reported**). Re-check
before relying on limits. Presets live in `civitas/llm.py`.

| Option | Signup / key | Free allowance | Speed | Status | CIVITAS preset |
|---|---|---|---|---|---|
| **OVHcloud AI Endpoints** (anonymous) | none | 2 req/min **per model** per IP (HTTP 429 + Retry-After); gpt-oss-120b, Qwen3.8-27B, Qwen3.6-27B, Qwen3.5-397B, Llama 3.3 70B, Mistral Small | 1–3 s, occasional 15 s queue | **verified** working, JSON schema honoured | `ovh` (default in `auto`) |
| **Groq** | free account + key, no card | ~30 req/min, ~1,000 req/day, ~200k tokens/day per model; Llama removed Aug 2026; gpt-oss-120b/20b, Qwen 3.x | fastest (hundreds of tok/s) | reported; endpoint reachable (401 without key) | `groq` (`GROQ_API_KEY`) |
| **OpenRouter `:free` models** | free account + key, no card | 20 req/min, **50 req/day** (1,000/day after a one-time $10 credit purchase) | varies | **verified** 16 free models listed (e.g. gemma-4-31b-it, nemotron-3-super-120b); keyless chat refused (401) | `openrouter` (`OPENROUTER_API_KEY`, `:free` enforced) |
| **Google Gemini API** | Google account + key | recent measurements ~20 req/day on Flash (older guides say 1,500); Pro removed from free tier | fast | reported; limits unpublished | `gemini` (`GEMINI_API_KEY`; keep billing off) |
| **Cerebras** | account; new accounts may need a card for $5 trial credit | ~1M tokens/day trial on gpt-oss-120b; no longer a permanent no-card tier | very fast | reported | `cerebras` (`CEREBRAS_API_KEY`) |
| **Ollama Cloud** | ollama.com account + key | small monthly starter allowance (gpt-oss:120b etc.), 1 concurrent | fast | reported (pricing changed 2026-08-31) | `ollama-cloud` (`OLLAMA_API_KEY`) |
| **Local Ollama** (qwen3-vl:2b here) | none | unlimited, private, offline | 6–12 s per request on this CPU; weak reasoning | **verified** | `ollama` |
| GitHub Models | GitHub token | — | — | **verified retired**: every path returns a stub `OK` | not used |
| Pollinations | key now required | — | — | **verified** 401 without key | not used |
| Mistral free mode | account | unpublished; terms reportedly changed Aug 2026 | — | reported, uncertain | not added |

## Recommendation

1. **Default `--language auto`**: player's own free keys first (Groq is the best
   speed/quality free tier), then keyless OVHcloud, then local Ollama, then the
   offline grammar. The backend that answered is named in every plan.
2. **"Completely free" means bring-your-own free key** for anything beyond the
   keyless tier. A shared developer key would hit per-organisation limits
   immediately and usually breaks provider terms. Keys stay in environment
   variables and are never saved in worlds or replays.
3. **Spend calls sparingly** (AIM §11–12): the grammar answers most commands
   with no call; one translation per player instruction; Oracle-level reasoning
   only on events (failures, novel requests). Thousands of agents must not mean
   thousands of LLM calls per tick.
4. **Privacy**: cloud backends receive the player's request text and the observed
   object summary. Use `--language none` or `ollama` to keep everything local.

## Sources

- Groq: https://klymentiev.com/blog/groq-pricing, https://benchlm.ai/free-tier/groq
- Cerebras: https://www.morphllm.com/cerebras-pricing, https://costbench.com/software/llm-api-providers/cerebras-inference/free-plan/
- Gemini: https://aiplug.work/en/blog/gemini-free-tier-limits, https://klymentiev.com/blog/gemini-api-free-tier
- OpenRouter: https://openrouter.ai/pricing, https://klymentiev.com/blog/openrouter-free-tier
- GitHub Models retirement report: https://github.com/robhunter/agentdeals/issues/1672
- Ollama Cloud: https://devtoolhub.com/ollama-cloud-free-vs-pro-limits-pricing-2026/
- Keyless lists: https://github.com/mnfst/awesome-free-llm-apis
- Pollinations docs: https://github.com/pollinations/pollinations/blob/main/APIDOCS.md
