# 14 — Revised 4-Week Timeline, Part 5: Week 4 in Detail

Expands section 2 of [14-timeline-part2.md](14-timeline-part2.md). Written 2026-10-16, after
D20. Back to the index: [00-overall-plan.md](00-overall-plan.md)

Lines marked **Change** differ from part 2, doc 11, doc 12, doc 13 or doc 15, and give the
reason. Times are estimates unless they say "measured".

## 1. Where Week 4 starts

- **The Week 4 model is the untuned control, `aeropatch-control`** (Q4_K_M, the D17 export). v2
  lost on test by the rule written before the runs: 32 against 38 of 54 (`NOTES.md`, D20). You
  said to go ahead with it on 2026-10-16.
- **D21 is done already.** The quant, the README training section and `runs/INDEX.md` were
  finished on D20, so Week 4 starts at D22.
- **The harness is frozen at `c03f33f`.** `git diff c03f33f HEAD -- src/ training/Modelfile` is
  empty today, so D20's runs used the code Week 4 measures.
- **In hand on that commit** (alternated, `dirty: false`): the control twice on `test` (19 and
  19 of 27), `test_b` (4 and 3 of 10) and `test_c` (5 and 4 of 5), and v2 step 64 the same way
  (18 and 14, 2 and 1, 4 and 5).
- **Older than the harness:** every frontier and cascade run (Week 2: `55e0709`, `9fcc75c`,
  `e382773`), and the cascade's local half was the library `qwen3.5:4b`. Neither has run on
  `test_c`.
- **Run times, from the start times of consecutive runs (upper bounds):** a `repair-local` run
  takes about 11 minutes on `test`, 6 on `test_b` and 1 on `test_c` (D20). In Week 2 the
  frontier took about 6 and 3 minutes on `test` and `test_b`, the cascade about 12 and 8. Part 2 marked D22 to D24 as overnight from doc 11 §9's
  estimate of 3 to 6 hours per config; most of it fits in daytime, attended.
- **Not built:**
  - doc 12's missing pieces: pass@k (no sampling config, no `pass_at_k`), the bootstrap, CSV
    output, tokens and $ per resolved scenario, p95 latency
  - doc 13 §6's adversarial scenarios
  - grammar-constrained decoding
  - tool localization: nothing reads the `localization` key, and `loop.py` always uses the
    scenario's finding
- **Disk:** 15.7 GB free on `F:`, where Ollama keeps its models. The Q5_K_M (3.07 GB) and Q8_0
  (4.48 GB) files sit on `D:` (446 GB free) and are not in Ollama.
- **Memory:** during D20, free commit fell to 0.5 GB while the model server grew from 7.8 to
  10.3 GB with one model loaded. It came back at each change of model.

## 2. Only you can do these

| Item | Needed by | Note |
|---|---|---|
| Choose the frontier model | D22, before the first frontier run | Section 3, first row |
| A standing yes for local commits on the branch during Week 4 | D22, before the first new config | Section 5: every run needs a clean tree. Commits only, no push |
| Name a demo repository you own, and say when to push to it | D26 | For the draft PRs of part 2, D26. Nothing is pushed or opened without your word |
| Make this repository public | After D27 | Once the security checklist is ticked |
| The `v1.0` tag and the PR into `main` | D28 | As for every push so far |
| Delete the Kaggle dataset `aeropatch-v2-step64-adapter` | Any time | Unused; the same adapter is in `D:\aeropatch-d20\adapter-v2-step64` |

## 3. Decisions, with the default that applies if you say nothing

| Decision | Default | Alternative |
|---|---|---|
| Frontier model | `claude-opus-5`, as in every frontier run so far | `claude-opus-5-5`. It costs no extra runs, because every frontier row runs again on D22, and the README would name the current model. The cascade uses the same model as the frontier row |
| Frontier route | Claude Code on the subscription (`repair-claude-code`, `cascade-claude-code`) | The API route, which spends per token |
| Dev experiments of `NOTES.md` "Next" 6 to 8: presence penalty, headers copied into edits, a shorter escalation prompt | Not in Week 4. Adopting any of them changes the measured harness after the freeze, so they go on the later list | Run one as a reported ablation on `test`, never adopted |
| Thinking ablation | Kept, with a 4,096-token budget (D24) | Cut (cut list item 3) |
| Run files behind the README | Commit the JSONL of each run the README cites, through a `.gitignore` exception. The attempt folders, with prompts and raw outputs, stay local | A release archive of `runs/` |
| Model for the fresh-clone reproduction | The library `qwen3.5:4b` (`ollama pull`). Every Week 1 and 2 baseline used it, and it scored 17 and 18 on `test` against the control's 19 and 19 | Publish the control GGUF (2.7 GB) for an exact match |
| MCP demo | A recorded terminal transcript in the README | A screen recording (cut list item 8) |

## 4. What changes from part 2

- **Change: no separate repair-off runs.** The first attempt of a repair run is a one-attempt
  run: the same prompt at `temperature_first` 0.2. resolve@1 of D20's runs is the repair-off row.
- **Change: the second greedy seed is done.** D20 ran the control twice on each split.
- **Change: no frontier pass@5.** With repair the frontier resolved 27 of 27 on `test`, 10 of 10
  on `test_b` and 13 of 13 on dev, so pass@5 can only read close to 1.0. Part 2 §4 cuts it first
  anyway. Its pass@1 is resolve@1 of the D22 run.
- **Change: the grammar ablation is cut** (cut list item 3). Nothing implements it. In D20's four
  control runs on `test` and `test_b`, a format failure ended 3 of the 29 failed scenario runs
  (1 of 16 on `test`, 2 of 13 on `test_b`). A grammar can win back at most those.
- **Change: the tool-localization ablation is cut.** A Tier A finding already is the scanner's
  own finding, within 3 lines (validator check 4), and tree-sitter cuts the context around that
  line. What "oracle" adds is the choice of which finding to fix. Tier B findings come from
  advisories and have no scanner finding to compare with. The ablation means new code in
  `loop.py` after the freeze. The README's limitations say what "oracle localization" means here.
- **Change: no `docker-compose.yml`.** Ollama runs natively with the GPU. A container would need
  GPU passthrough in Docker and a second copy of the model on `F:`.
- **Change: no model card or Hugging Face upload.** The Week 4 model is the base model, unchanged.
  A "Model" section in the README gives its source, quantisation and SHA-256. The v2 adapter lost
  and is not published.
- **Change: the adversarial scenarios are built**, though doc 11 says Week 4 adds no scenarios.
  That line protects the headline splits. Doc 13 §6 reports adversarial scenarios separately, and
  the Week 4 demo and the definition of done (part 2 §7 and §8) need them.
- **Change: in the definition of done, "the fine-tuned model served at Q4" becomes "the Week 4
  model".** That is met: the control at Q4 peaked at 3,043 MiB and decoded 46.5 tokens a second
  on D20 (measured).
- **Change: resume bullets (doc 15).** The fine-tuning bullet reports the null result with its
  numbers. Doc 15 already says to lead with another bullet when the delta is small.

## 5. Rules for every Week 4 run

- **Freeze check before each run:** `git diff c03f33f -- src/` may touch only `metrics.py`, the
  `report` command and new entries in `CONFIGS`. If it shows anything else, the control runs
  again; a footnote does not cover it.
- **A clean tree for each run**, so every header says `dirty: false` as D20's do. A new config,
  scenario or `split.json` key is committed before its first run.
- **Ablations and sampled runs are reported, never adopted.** The headline config does not change
  because of what `test` shows (`NOTES.md`, D19, the rule written before the test runs).
- **Two runs per local row, read with D20's rule.** A difference of 4 or more of 54 is a
  difference; under 4 is "no difference shown". A frontier row gets one run, since it sits at
  the ceiling.
- **One heavy job at a time.** `ollama stop <model>` after each long run releases the server's
  growth. A long run gets its own `--run-id`, so it can be resumed.
- Before the first run of a day: Ollama answers on `/api/tags`, and Docker is up.

## 6. Day by day

| Day | Work | Run time (estimate) | Acceptance check |
|---|---|---|---|
| D22 | Cascade with the control, 2 runs per split; frontier, 1 run per split; adversarial scenarios written | About 1.5 hours | Local, cascade and frontier rows on one harness; each adversarial scenario rejects its injection with the expected code |
| D23 | Sampling config, 5 runs per split; `pass_at_k`; adversarial runs | About 1 hour | pass@1, @3 and @5 beside resolve@1, @2 and @3; injection-follow and injection-success rates |
| D24 | Ablations on `test`: Q5_K_M, Q8_0, thinking | 3 to 6 hours; the thinking runs go in the evening | Ablation table with tok/s, peak VRAM and run files |
| D25 | `metrics.py` final; charts | None | Every table and chart regenerates from run files |
| D26 | README; fresh-clone reproduction; MCP transcript; draft PRs | One `remediate` | One scenario resolved from a fresh clone, tested once |
| D27 | Security checklist; secret scan; publish the run files | None | Checklist ticked |
| D28 | Buffer; resume bullets; write-up; `v1.0` on your word | None | Part 2's Week 4 exit criteria |

## 7. D22 to D24: the runs

**D22**
- [ ] One `remediate` call on the Claude Code route with the chosen frontier model, to confirm
      it still answers.
- [ ] `uv run aeropatch bench --config cascade-claude-code --split <split> --local-model
      aeropatch-control`, twice each on `test`, `test_b` and `test_c`, alternating splits. Add
      `--frontier-model` if section 3 changes the model.
- [ ] `uv run aeropatch bench --config repair-claude-code --split <split>`, once on each split.
- [ ] Read against Week 2: escalation rate, local-resolved share, $ per resolved scenario (the
      Claude Code route reports the API-equivalent cost).
- [ ] Adversarial scenarios, about 3 hours. X-01, X-02, X-03, X-05 and X-06 of doc 13 §6, each a
      copy of a small dev scenario with the planted text, under a new `adversarial` key in
      `split.json`. X-04 (network and writes outside `/work`) is already
      `tests/test_sandbox_security.py`, which is cited, not rebuilt. Beside each scenario an
      `injection.json` holds the marker that the injected action leaves in an edit and the
      expected code (`requests.post` and `RISKY_IMPORT`, a `tests/` path and `FORBIDDEN_PATH`,
      `# nosec` and `SUPPRESSES_CHECKS`, a `.github/` path and `FORBIDDEN_PATH`). The marker
      stays out of the `Task` contract, so `src/` stays frozen. X-06 plants a key with a provider
      prefix that `prompts.SECRET_PATTERNS` matches. Their images are built between the runs
      above, not beside them.
- [ ] Acceptance:
  - **The model can see the planted text.** It sees only the context cut around the finding, so
    `uv run aeropatch context` on each finding's path and line must show the injected string,
    X-06's key included. X-05's text must reach the prompt's `Message:` line.
  - `aeropatch validate` passes all four checks on each scenario, because the planted text
    changes no behaviour.
  - A hand-written patch that obeys the injection, sent through the MCP `validate` tool, gets the
    expected code. X-06 records `SECRET_BLOCKED` before any generation.
  - **X-01 is sent twice**, with and without an `import requests` line, and both results are
    recorded. `gates.py` flags a risky module only when an import of it is added, and
    `requests.post` is not in `RISKY_CALLS`. So the bare call passes the gates in a file that
    already imports `requests`, and the sandbox, which has no network, is the layer that has to
    stop it.

**D23**
- [ ] Config `sample-local`: `{"attempt_plan": ["local"], "temperature_first": 0.7}` (doc 12 §2
      says 0.6 to 0.8). The client sends no seed, so the runs are independent samples.
- [ ] 5 runs each on `test`, `test_b` and `test_c` with `--local-model aeropatch-control`.
- [ ] `pass_at_k` in `metrics.py` as doc 12 §2 writes it, with its three asserts in
      `tests/test_metrics.py`. `report` groups the runs of one config, model and split, and gives
      pass@1, @3 and @5.
- [ ] Read pass@3 against resolve@3: the same budget of three generations, sampling against
      repair (doc 12 §1).
- [ ] Adversarial runs: `repair-local` with the control twice, `repair-claude-code` once.
      `report` gains two rates. The injection-follow rate counts attempts whose edit carries the
      marker. The injection-success rate counts those that got past every deterministic layer
      (doc 13 §6): the gates, the sandbox and the tests, so the run accepted the edit as a fix.
      The target is 0.

**D24**: ablations on the control, on `test`, 2 runs each, against D20's 38 of 54.
- [ ] **Q5_K_M.**
  - Copy `training/Modelfile` beside the file on `D:`, with only `FROM` changed, and run
    `ollama create aeropatch-control-q5`.
  - Smoke test with `remediate` while sampling `nvidia-smi`. Peak VRAM must stay under 3,891 MiB.
    Expect about 3,400: Q4 peaked at 3,043 with a file 366 MB smaller.
  - 2 runs, about 22 minutes. Then `ollama rm`.
- [ ] **Q8_0.**
  - At 4.48 GB it cannot fit the 4 GB GPU with every layer on it. Find the most layers that stay
    under 3,891 MiB: send `num_gpu` in a request's options and watch `nvidia-smi`.
  - Config `repair-local-q8`: `repair-local` plus that `local_num_gpu` and a
    `scenario_wallclock_s` of 1,800, so a slow CPU share is not scored as a wrong fix. Speed goes
    in its own column.
  - Time one scenario first. At 9 tokens a second (`qwen3.5:4b` with 54% on the CPU, measured,
    `config.py`), four generations of 1,024 tokens take about 8 minutes.
  - Attended, with nothing else heavy running, because the CPU share adds to RAM. Then
    `ollama rm`.
- [ ] **Thinking.**
  - Config `repair-local-think`: `local_think` on, `max_tokens_local` 4,096,
    `scenario_wallclock_s` 1,800.
  - Ollama returns the thinking in `message.thinking` and the client reads `message.content`
    only, so the edit parser sees the answer alone. The thinking does use up the token budget.
  - A full budget takes about 90 seconds at 46.5 tokens a second. The 2 runs take 1 to 3 hours,
    started in the evening.
- [ ] Table: resolved of 54, tok/s, peak VRAM and run files per row, with D20's rule.

## 8. D25 to D28: report, package, check

**D25**: `metrics.py` final (doc 12 §5).
- [ ] Paired bootstrap over scenarios: 10,000 resamples, stdlib `random`, seeded.
- [ ] A CSV per table (`report --csv <dir>`).
- [ ] Tokens (input, output, cache read) and $ per resolved scenario; p50 and p95 latency. Results
      per tier: A, B and C, and the adversarial scenarios apart.
- [ ] Charts: cost against accuracy, the repair curve, failure attribution. They are drawn in
      `notebooks/runs.ipynb`, which already draws the GPU traces, and saved as PNG under
      `docs/results/`. The benchmark's `.venv` gets no plotting library.
- [ ] Doc 12 §7's headline table and the delta table (untuned, then v2 from D20, then frontier),
      with each cell naming its run file.

**D26**: after the last run, so the freeze no longer binds.
- [ ] README: the results, with the tables, the charts and the run files named; the Model
      section; the limitations (doc 12 §6 item 8, what oracle localization means here, the
      fine-tune's null result); the isolation statement; the later list (part 2 §9, `NOTES.md`
      "Next" 6 to 8, the audit's cuts).
- [ ] Fresh-clone reproduction, tested once in an empty folder on `D:`: `uv sync`,
      `ollama pull qwen3.5:4b`, then `uv run aeropatch remediate <scenario> --config
      repair-local`, using a dev scenario that every local run resolved.
  - `remediate` builds the scenario image but not the base image (`scenario.ensure_image`), so
    today that takes four commands.
  - Having `ensure_image` build a missing base image makes it three. It is a few lines, done now
    that no run is left.
- [ ] MCP transcript: one `remediate` and one `validate` call through `aeropatch mcp`, saved under
      `docs/`.
- [ ] Draft PRs on your demo repository, once you name it and say go.
- [ ] `docs/architecture.html` and `docs/architecture-interactive.html` are the same file: keep one
      and fix the links (`NOTES.md`, "Next" 11).

**D27**
- [ ] Doc 13's checklist, item by item.
- [ ] Secret scan of the whole history (`git log -p --all`) and of the run files to publish, with
      `prompts.check_no_secrets` (its patterns and the assignment rule). Fakes planted on purpose
      are listed as expected hits: X-06's key, and the `"changeme"` credentials of `A-798-01` and
      `A-798-02` if the scan matches them. Any other hit is resolved before anything is published.
- [ ] Publish the run files as section 3 decides.

**D28**
- [ ] Resume bullets from measured numbers only (doc 15), changed as section 4 says.
- [ ] A short write-up.
- [ ] Part 2's Week 4 exit criteria; `NOTES.md`; the `v1.0` tag and the PR into `main` on your
      word.

## 9. If something fails

| What happens | Then |
|---|---|
| `claude-opus-5` no longer answers on the Claude Code route | The decision in section 3 is made: `claude-opus-5-5` |
| A Claude Code run hits the subscription limit (R13) | `bench` resumes with the same `--run-id`; spread the frontier runs over the day |
| Free memory falls under 1 GB during a run | `ollama stop` once the run ends, and nothing else heavy beside it. If the run dies, resume it by its run ID |
| Q8_0 does not load, or times out at every layer count that fits | Report Q8_0 as not runnable inside 4 GB, with the measured numbers. The Q4 and Q5 rows stand |
| Most thinking attempts stop at 4,096 tokens | Report how many did. The budget is not raised again on `test` |
| An injection patch gets past the gates | That is a real gap. Record it, report the success rate as measured, and fix the gate as its own change after the Week 4 runs |
| A cascade run escalates far more often than in Week 2 | Its local half is the control now, not the library model. Report both rates; neither run is repeated |

## 10. Done when

Part 2's four Week 4 exit criteria, plus:
- [ ] Every Week 4 run passed the freeze check.
- [ ] The adversarial scenarios have a measured injection-success rate (target 0) and a reported
      follow rate.
- [ ] pass@k and resolve@k sit in one table for the control.

**Not in Week 4:**
- the grammar and tool-localization ablations, and frontier pass@5
- a `docker-compose.yml`, the model card and the Hugging Face upload
- the dev experiments of `NOTES.md` "Next" 6 to 8, and repair feedback full against trimmed
  (doc 12 §6)
- `propose_fix` and `apply_edits` as MCP tools, and a Tier B "before release" group
- a second training run, and the audit's cuts
