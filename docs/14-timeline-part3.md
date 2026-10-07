# 14 — Revised 4-Week Timeline, Part 3: Week 3 in Detail

Expands section 1 of [14-timeline-part2.md](14-timeline-part2.md). Written 2026-10-05, at the
close of Week 2. Back to the index: [00-overall-plan.md](00-overall-plan.md)

Lines marked **Change** differ from doc 09, doc 10 or part 2, and give the reason.

## 1. Where Week 3 starts

- **Exists:** 50 frozen scenarios (13 dev, 27 test, 10 `test_b`), untuned baselines on all three
  splits, and `training/inject_cwe.py`. The script has had a smoke test only: 0 of 3 candidates
  kept, 50–100 s each, with the student standing in as teacher.
- **Not written yet:** `training/prepare_dataset.py`, `training/finetune.py`,
  `training/requirements.txt`, the Kaggle notebook and the Ollama Modelfile.
- **Untuned `repair-local` on dev is noisy:** 10/13 and 7/13 on 2026-10-03 (runs `113223`,
  `115043`) and 9/13 on 2026-10-05 (`150539`). Section 6 is built around this.
- **Disk:** 25 GB free on `F:` and 63 GB on `C:`, against the 40–60 GB estimate in part 2 §4.

## 2. Only you can do these

| Item | Needed by | Note |
|---|---|---|
| Choose the teacher model | D15, first thing | Nothing runs unattended until then (section 3) |
| Read the teacher host's terms on training with its outputs | D15 | The conclusion goes in the README (doc 09 §4) |
| Kaggle account, phone-verified | D17 | Verification unlocks GPU and internet in notebooks |
| Hugging Face token in Kaggle Secrets | D17 | Only if `Qwen/Qwen3.5-4B` asks for one; the dataset goes up as a private Kaggle dataset |

## 3. Decisions, with the default that applies if you say nothing

| Decision | Default | Alternative |
|---|---|---|
| Teacher | **None. This one blocks** | See below |
| Source of real fix pairs | **Change:** the GitHub advisory database (the Tier B route), advisories before 2026-01-01 | MoreFixes: a PostgreSQL dump, 2.0–3.5 GB zipped, about 14 GB restored |
| Dedupe and leakage scan | **Change:** every pair compared on token 5-grams with identifiers blanked; near-duplicate groups capped, not deleted | Doc 09 §7 and §9 as written: exact hash and a 13-gram scan |
| Tier C | Build 5 from the D15 pilot, set aside before any training example is kept; drop it if the pilot keeps fewer than 5 | Drop it now (cut list item 2) |
| Context format | Frozen as it is for the rest of the project | Change it on D15, as a new config judged on dev |
| CWE weights | From dev only (`NOTES.md`, D14) | Part 1 §5 as worded: from the baselines |

**Teacher.** `--teacher` takes an Ollama tag, so any model behind an Ollama endpoint works with
no code change. The local Ollama already lists four hosted tags: `kimi-k2.6:cloud` (reports
1,042B parameters), `minimax-m2.7:cloud` (229B), `glm-5.1:cloud` and `qwen3.5:cloud` (no
metadata, size unknown). Doc 09 §4 names Qwen3-Coder-Next and Qwen3.6-35B-A3B. Check for each:
an open-weights licence on the model card, the host's terms on training with outputs, limits
and cost, and that it is clearly larger than the 4.7B student.

**Fix pairs.** The 2026-01-01 cutoff (doc 09 §9) keeps training pairs out of the Tier B window,
2026-03-16 to 2026-10-02.

**Dedupe and leakage.** The laptop test of 2026-10-01 on 5,000 Python functions (research doc,
not in the repo): the exact hash found 0 of 150 one-line edits; the 13-gram scan linked about
35% of functions to another one, mostly false alarms, and missed a third of renamed copies; the
every-pair check fixed both in about 33 s. `inject_cwe.py` uses the 13-token scan today, with
the vendored Tier B library files in its reference set: expect false `leakage` rejects.

**Context format.** Training examples are rendered with `get_context` and `prompts.py` as they
are on D17. A later change (`NOTES.md`, D13, finding 3) means rendering and training again.

## 4. Day by day

| Day | Work | Acceptance check |
|---|---|---|
| D15 (O) | Teacher pilot of 30; Tier C set aside; overnight generation; `prepare_dataset.py` with the exclusion list and the fix-pair converter | Pilot yield and seconds per candidate in `NOTES.md`; conversion spot check 20/20 byte-exact |
| D16 (O) | General bug-fix slice; student pass overnight for repair turns; format-hardening slice; filters, dedupe, leakage | `stats.md`; zero repo overlap with eval; every n-gram hit looked at |
| D17 | Spot check of 30; freeze dataset v1; parity test; `finetune.py`; Kaggle pilot; **export rehearsal and untuned control** | Pilot log; the control GGUF resolves a dev scenario on the laptop |
| D18 | Full LoRA run; export at most 3 checkpoints; 3 dev runs each | Loss curves; dev table per checkpoint next to the control |
| D19 | Second run only if dev is flat; final merge and GGUF at Q4, Q5, Q8 | Files downloaded; SHA-256 in `NOTES.md` |
| D20 | Modelfile; smoke test at each quant; VRAM and tok/s | The chosen model resolves dev scenarios on the laptop inside the VRAM limit |
| D21 | Buffer; pick checkpoint and quant; README training section; runs in `runs/INDEX.md` | Decision recorded with the dev table |

## 5. D15–D16: data

**D15**
- [ ] Pilot: `uv run python training/inject_cwe.py --teacher <tag> --count 30`. From
      `training/synthetic/manifest.jsonl` record kept/30, the reject reasons, seconds per
      candidate and the number of `leakage` rejects.
- [ ] **Change: size the run from the pilot, not from doc 09's 1,000–2,000.** Expected kept =
      hours × 3,600 × yield ÷ seconds per candidate. The script runs one candidate at a time,
      and generation has about 24 hours: the D15 night and the D16 day. The D16 night belongs to
      the student pass. At 60 s each that is 1,440 candidates:

| The pilot predicts, for those 24 hours | Then |
|---|---|
| 800 or more kept (over half kept at 60 s each) | Follow the mix in doc 09 §8 |
| 300–800 | Mined fix pairs fill the first-attempt slice; total target 1,500 (R4) |
| Under 300 (a fifth kept at 60 s each), or yield under 10% | Fix the prompt or change teacher before the night |

- [ ] Expect the middle row. The likeliest prompt fault is the smoke test's: a PoC that does not
      separate the two versions (`1_vulnerable_baseline`, `poc_wrong_reason`).
- [ ] The script resumes from the manifest, so it can be stopped and restarted. Ids come from the
      manifest's line count: never run two generators at once.
- [ ] Laptop on AC power with sleep off for the night (R10).
- [ ] Tier C, if kept, between the pilot and the overnight run: move 5 kept examples into
      `evaluations/scenarios/`, change their manifest status from `kept` to `tier_c` (the student
      pass takes every `kept` record), bring them to the Tier A bar and add their own key to
      `split.json`. The overnight run rebuilds its leakage set at start, so it then covers them;
      `prepare_dataset.py` must drop any pilot example that overlaps them.
- [ ] `prepare_dataset.py`, starting with the exclusion list checked in code: Mako, mistune,
      sqlparse, microdot, geopy, Flask-HTTPAuth, PyJWT, hpack, pyasn1. No pair from these
      repositories is kept. Then the converter of doc 09 §6: SEARCH/REPLACE blocks applied with
      `aeropatch.agent.edits`, byte-exact against the post-fix file.

**D16**
- [ ] General bug fixes (~20% of the mix): SWE-smith and SWE-Gym final patches through the same
      converter and filters.
- [ ] Student pass overnight (`--count 0 --student` runs it alone): each failed attempt with its
      feedback and the reference fix is a repair-turn example (~20%). Time it on the first 50 kept
      to know whether one night is enough.
- [ ] Format-hardening examples (~5%).
- [ ] Filters in doc 09 §7's order with a count at each step; dedupe and leakage as decided in
      section 3; `stats.md`.
- [ ] R4 check at the end of the day: under 800 verified examples means the total target drops
      to 1,500.

## 6. D17–D20: training and the dev comparison

Part 2 §4 budgets 6–10 of Kaggle's 30 GPU hours a week. The rehearsal, the control and the
checkpoint exports below are extra sessions inside that budget.

**D17**
- [ ] Read 30 random verified examples, about an hour. More than 3 wrong or silly: tighten the
      filters before freezing (doc 09 §10).
- [ ] Freeze dataset v1: `train.jsonl`, `val.jsonl` (5%), `stats.md`, the leakage report. SHA-256
      of both files in `NOTES.md`.
- [ ] Parity test. Messages: a unit test that `prepare_dataset.py` builds the system and user
      messages with the functions the loop uses (`get_context`, `prompts.first_user_message`,
      `prompts.repair_message`). Template: render one prompt with the Hugging Face chat template,
      thinking off, and compare it with what the local server renders for the same messages.
- [ ] `training/finetune.py`, `training/requirements.txt` with Unsloth, TRL and PEFT pinned, and
      a notebook that only clones the repo and calls the script (doc 10 §2).
- [ ] Kaggle pilot: 50 steps on 400 examples. Loss falls, peak VRAM under 14 GB, 5 validation
      prompts parse as SEARCH/REPLACE (doc 10 §4).
- [ ] **Change: export rehearsal.** In the same session, merge the pilot adapter and export
      Q4_K_M; load it with `ollama create` on the laptop and run one dev scenario. This moves
      risk R3 (llama.cpp support for Qwen3.5, the chat template, the stop sequence) from D19–D20
      to D17.
- [ ] **Change: untuned control.** Export the untuned base through the same path and run dev with
      it. Without it, "fine-tuned against untuned" also measures the difference between Ollama's
      library build of `qwen3.5:4b` and your own export. Confirm on the way that
      `Qwen/Qwen3.5-4B` is the checkpoint that tag is built from.
- [ ] Laptop QLoRA pilot on Qwen2.5-Coder-1.5B, if the day has room (cut list item 6).

**D18**
- [ ] Full run with doc 10 §3's values: r 16 / alpha 16, learning rate 2e-4, 2 epochs, sequence
      2,048, batch 1 with accumulation 8, seed 3407, a checkpoint every 200 steps.
- [ ] **Change: at most 3 checkpoints are judged.** The sandbox runs only on the laptop, so
      judging a checkpoint costs a merge, a Q4_K_M export and a download. Take the end of each
      epoch and the lowest validation loss.
- [ ] **Change: 3 dev runs per checkpoint and 3 of the control.** One run cannot separate a gain
      from the 7-to-10 spread in section 1. Compare totals out of 39, and watch A-328-01, A-918-01
      and A-601-01, which the untuned model failed in both runs of 2026-10-03. A dev run took
      under 5 minutes that day, so 12 runs are about an hour.
- [ ] The fine-tuned model runs under its own config name, or as `repair-local` with
      `local_model` overridden, so the model tag is in every run header.

**D19**
- [ ] A second run (r 32 / alpha 32, or 3 epochs) only if dev is flat (cut list item 4).
- [ ] Final export on Kaggle: Q4_K_M, Q8_0 and f16; Q5_K_M from the f16 file with
      `llama-quantize`. Download Q4, Q5 and Q8, not f16. SHA-256 of each in `NOTES.md`.
- [ ] Check free space first: `ollama create` stores its own copy of each GGUF.

**D20**
- [ ] Modelfile as in doc 10 §8, the same for the control and the fine-tuned model apart from
      `FROM`.
- [ ] Smoke test with `aeropatch remediate` at Q4, Q5 and Q8: peak VRAM under 3,891 MiB (the
      untuned model peaked at 3,787) and tok/s near the untuned 43–48.
- [ ] The Q4 dev runs of the chosen checkpoint exist from D18, so this day is light if the D17
      rehearsal worked. The slack goes to the README section or the laptop QLoRA demo.

## 7. Exit criteria, and a flat result

The four criteria of part 2 §1, plus two:
- [ ] The untuned control from the same export path is in the dev table.
- [ ] The parity test passes on the frozen dataset.

If dev shows no gain, the order in part 2 §1 holds: parity, then data quality, then learning
rate. A null result on dev is reported as one.

**Not in Week 3:** any run on `test` or `test_b` (D22), the quant and grammar ablations (D24),
pass@5, the shorter escalation prompt (`NOTES.md`, "Next", item 7) and the audit's cuts.
