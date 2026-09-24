# 04 — Frontier API Fallback and Routing

Maps to: `src/models/fallback_client.py`, `src/agent/router.py`. Back to: [00-overall-plan.md](00-overall-plan.md)

## 1. Gemini 2.0 Flash has been retired

Google's deprecations page lists `gemini-2.0-flash` and `gemini-2.0-flash-lite` as shut down on
**2026-06-01**. Calls to them now fail. The official replacements are `gemini-3.6-flash` and
`gemini-3.1-flash-lite`. Newer Flash models have shipped since: 3.7 Flash (2026-08-13) and
3.8 Flash (2026-09-02). Google also limits Gemini 2.5 access to existing users, so a new project
shouldn't start on 2.5 either.

## 2. Price table (per 1M tokens, USD)

Claude prices come from Anthropic's model table (cached 2026-06-24). Gemini prices come from
third-party trackers (Sep 2026) and change often. Re-check both before publishing numbers.

| Provider | Model ID | Input | Output | Context | Notes |
|---|---|---|---|---|---|
| Anthropic | `claude-opus-5` | $5.00 | $25.00 | 1M | Default Claude model for new code |
| Anthropic | `claude-opus-5-5` | $4.00 | $20.00 | 1M | Launching; use only if you choose it by name |
| Anthropic | `claude-sonnet-5` | $2.00 | $10.00 | 1M | Cheaper tier (your call) |
| Anthropic | `claude-haiku-4-5` | $1.00 | $5.00 | 200K | Cheapest Claude tier (your call) |
| Anthropic | `claude-fable-5-1` | $10.00 | $50.00 | 1M | Most capable; overkill for this task |
| Google | `gemini-3.8-flash` | check | check | — | Newest Flash (2026-09-02) |
| Google | `gemini-3.7-flash` | ~$0.375 | ~$1.88 | 1M | Reported price |
| Google | `gemini-3.5-flash` | ~$0.75 | ~$4.50 | — | Reported price |
| Google | `gemini-3.1-flash-lite` | ~$0.25 | ~$1.50 | — | Shutdown scheduled 2027-05-07 |

Thinking tokens are billed as output tokens on both providers. Budget for them.

## 3. Recommendation: one fallback provider, two frontier references

- **Production fallback (router): one provider.** Supporting two provider SDKs, two sets of
  error handling and two refusal behaviours means twice the code for no measured gain.
  The default Claude model for new code is `claude-opus-5`. Dropping to `claude-sonnet-5` or
  `claude-haiku-4-5` to save money is your decision; make it after the Week 1 baseline shows
  how often the fallback is actually called.
- **Benchmark references: up to two.** Run the frontier reference (Claude) and, optionally,
  one cheap Gemini Flash model. That gives two points on the cost/accuracy curve for the
  final chart without making Gemini a production dependency.

## 4. Cost estimate per scenario (rough; replace with measured numbers)

Assumptions: ~4k input tokens (context plus instructions), ~1.5k output tokens including thinking,
and at most 3 attempts.

| Model | Per attempt | Worst case per scenario (3 attempts) | 40 scenarios × 5 samples (pass@5) |
|---|---|---|---|
| `claude-opus-5` | ~$0.06 | ~$0.18 | ~$12–36 |
| `claude-sonnet-5` | ~$0.023 | ~$0.07 | ~$5–14 |
| `claude-haiku-4-5` | ~$0.012 | ~$0.035 | ~$2–7 |
| `gemini-3.7-flash` | ~$0.004 | ~$0.012 | ~$1–3 |
| Local Qwen3.5-4B | $0 (electricity) | $0 | $0; costs wall-clock hours instead |

**Prompt caching** cuts input cost. The system prompt, edit-format spec and examples are identical
across scenarios, so put them first and mark them cacheable. Check `cache_read_input_tokens` > 0
in the usage logs; if it stays zero, something in the prefix is changing between calls.

## 5. Routing policy (cascade)

The router is a plain function, not a class hierarchy. There are three modes, and all three
are benchmarked:

| Mode | Behaviour | Purpose |
|---|---|---|
| `local` | Local SLM only, up to 3 attempts | Measures what the SLM can do alone |
| `frontier` | Frontier only, up to 3 attempts | Upper-bound reference |
| `cascade` | Local first, escalate on triggers | The real product; cost vs accuracy trade-off |

Cascade escalation triggers, all deterministic:
1. The edit fails to parse or apply twice in a row.
2. The scope gate rejects the local model's edit twice (doc 08).
3. Local attempts are used up (default: 2 local, then 1 frontier).
4. The required context exceeds the local token budget (e.g. >6k tokens after scoping).
5. The scenario is tagged multi-file.

When escalating, send the frontier model the **full history**: the original task, each local
attempt's edit, and the trimmed test output. It is fixing a concrete failed attempt, not
starting cold.

```text
attempts: [local, local, frontier]   # configurable list; the loop walks it
on refusal or provider error -> skip to the next entry, record the reason (not a numbered attempt)
stop when: tests pass | list exhausted | per-scenario $ cap hit
```

## 6. Refusals are expected: handle them as routing events

Frontier models run safety classifiers, and "cyber" is one of the categories. A vulnerability-fix
agent sends text that resembles exploit material: PoC tests, payload strings, CWE names. Some
requests will be declined. Expect it and measure it.

- **Claude**: check `stop_reason` before reading content. On `"refusal"`, `stop_details`
  carries a `category` (e.g. `"cyber"`) and an explanation. The Claude API also offers
  server-side fallbacks (beta header `server-side-fallback-2026-07-01` with `fallbacks: "default"`),
  which retry on another model according to the refusal category. Turn them on and log when
  they fire. `claude-opus-5-5` has broader classifiers than `claude-opus-5`.
- **Gemini**: a safety block shows up as a finish reason, not an exception. Check it too.
- **Router behaviour**: record the refusal (model, category, scenario) and move to the next
  route. Report **refusal rate** as a metric (doc 12). A local model that never refuses
  defensive work is a real, reportable advantage of the SLM path.
- **Prompt hygiene lowers false positives**: state the defensive purpose ("remediate a
  vulnerability in this repository's code; output only the fix"). Include the failing test
  *name and assertion message*, not raw payload dumps. Never ask for an exploit.

## 7. Claude API details that affect the client (current API)

- Use the official `anthropic` Python SDK, not an OpenAI-compatible shim.
- Thinking: use adaptive thinking (`thinking: {type: "adaptive"}`) and control depth with
  `output_config.effort`. `budget_tokens` is rejected on current models. On `claude-opus-5-5`,
  thinking can't be disabled at all.
- Structured output: to get edit blocks back as validated JSON, use `output_config.format`
  (or `client.messages.parse()`). Assistant-message prefill is rejected on current models.
- Streaming: use it for any long output (`.stream()` + `get_final_message()`).
- Errors: handle rate limits (429) and 5xx separately from 400s. The SDK retries 2 times by default.
- Read `response.usage` on every call and store input, output, and cache-read tokens per attempt.
  The cost metric is computed from these logs, not estimated.

## 8. Data handling rules for API calls

- Send only code from your scenario repos or public open-source projects. Never send secrets,
  `.env` files, or private third-party code.
- Strip absolute host paths and usernames from tracebacks before sending them.
- Keep the API keys in the orchestrator process only; they must never reach a sandbox container.
- Check each provider's data-retention and training-use terms, and note them in the README.

## 9. Router configuration (one dict, logged in every run header)

| Key | Example | Meaning |
|---|---|---|
| `mode` | `"cascade"` | `local` / `frontier` / `cascade` |
| `attempt_plan` | `["local", "local", "frontier"]` | Route per attempt; the loop walks it |
| `local_model` | `"aeropatch-4b:q4_k_m"` | Ollama tag or GGUF path; digest logged |
| `frontier_model` | `"claude-opus-5"` | Default Claude model; a cheaper tier is your choice |
| `frontier_effort` | `"medium"` | `output_config.effort`; lower means cheaper and faster |
| `max_usd_per_scenario` | `0.50` | Hard ceiling; the loop stops when it's reached |
| `local_ctx_budget` | `6000` | Tokens; above this, escalate or trim |
| `server_side_fallbacks` | `true` | Claude API refusal fallback (beta) |

Changing any of these means a new config name. Results are only compared within a config.

## 10. What to report from this component

Escalation rate, refusal rate (by provider and category), frontier tokens per resolved scenario,
dollar cost per resolved scenario for each mode, and the accuracy delta cascade vs frontier.
Together these show whether the SLM is earning its place.

Next: [05-architecture.md](05-architecture.md)
