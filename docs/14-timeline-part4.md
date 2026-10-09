# 14 — Revised 4-Week Timeline, Part 4: D17 in Detail

Expands the D17 list in section 6 of [14-timeline-part3.md](14-timeline-part3.md). Written
2026-10-09, at the close of D16. Back to the index: [00-overall-plan.md](00-overall-plan.md)

Lines marked **Change** differ from part 3 or doc 10, and give the reason. Times are estimates
unless they say "measured".

## 1. Where D17 starts

- **Exists:** 554 examples, not frozen (`training/stats.md`). One command rebuilds them in about
  a minute (measured): `uv run python training/prepare_dataset.py build --student-run
  20261009-student-pass`. Two builds give the same files.
- **Exists:** the message half of the parity test (`tests/test_prepare_dataset.py`, and the
  build's check of 240 student prompts).
- **Not written yet:** `training/finetune.py`, `training/requirements.txt`, the Kaggle notebook,
  the Modelfile.
- **No Kaggle token on the laptop:** `C:\Users\vardh\.kaggle\kaggle.json` does not exist. The
  Kaggle command line itself runs (`uvx kaggle --version` answers 2.2.4).
- **Ollama's `qwen3.5:4b` does not carry a chat template in its Modelfile.** It says
  `TEMPLATE {{ .Prompt }}` with `RENDERER qwen3.5` and `PARSER qwen3.5`, thinking on by default,
  temperature 1. A model made from your own GGUF needs the same two lines, or it may get no
  chat format at all. This is risk R3, and the reason the export rehearsal is today.
- **Disk:** 19 GB free on `F:`, where Ollama keeps its models, and 55 GB on `C:`. The library
  build of `qwen3.5:4b` is 3.16 GB, and `ollama create` stores its own copy of each GGUF.

## 2. Only you can do these

Nothing on Kaggle runs before the first two.

| Item | How | Note |
|---|---|---|
| Kaggle account, phone-verified | kaggle.com, in the account settings | Unlocks the GPU and internet in notebooks |
| Kaggle API token | Account settings, API section: create a token and save it in `C:\Users\vardh\.kaggle\`, as the page says | Lets the pilot be started and its files fetched from the laptop, with no clicking in the browser |
| Hugging Face token in Kaggle Secrets | Only if `Qwen/Qwen3.5-4B` asks for one | Same as part 3 |
| Look at the spot-check sheet | Optional, 15 minutes | Section 4, step 1 |

## 3. Decisions, with the default that applies if you say nothing

| Decision | Default | Alternative |
|---|---|---|
| Sequence length | 2,048 (554 examples). **4,096 (661 examples) only if** the memory probe in step 6 peaks under 14 GB and the full run is estimated under 3 hours | Stay at 2,048 whatever the probe says |
| Targets that call a function the prompt does not show (33 by pattern match) | Drop the ones the reading confirms, with a filter that is counted in `stats.md` | Keep them |
| Docstrings that name the fix (32 synthetic prompts) | Keep, as on D16 | Reword or drop |
| A second generation run | Not started. D18's dev result decides | Start it tonight; its examples would make a dataset v2 |
| Where the pilot runs | Kaggle, driven from the laptop with the API token | Kaggle in the browser, or Colab T4 with the same script |
| Laptop QLoRA demo (Qwen2.5-Coder-1.5B) | Only if the day has room (cut list item 6) | Move it to D21 |

## 4. Order of work

**Change: the freeze comes after the pilot, not before it.** Which set is frozen depends on
the sequence length, and the length depends on a memory number that only the pilot gives.

| # | Step | Estimate | Acceptance check |
|---|---|---|---|
| 1 | Read 30 random examples (seed 3407) from a sheet | 1 hour | At most 3 wrong or silly; otherwise tighten a filter first (doc 09 §10) |
| 2 | Apply what the reading decides; build both candidate sets | 30 minutes | `stats.md` for each; tests pass |
| 3 | `finetune.py`, `requirements.txt`, the notebook | 2 to 3 hours | The self-checks of section 5 pass on the laptop where they can |
| 4 | Template half of the parity test | 30 minutes | Token counts match Ollama's for every sampled prompt |
| 5 | Upload the data; pilot of 50 steps on 400 examples at 2,048 | 15 minutes of GPU (doc 10 §4), plus queue | Loss falls; peak VRAM under 14 GB; 5 validation outputs parse |
| 6 | Memory probe at 4,096: 20 steps on the 50 longest examples | 10 minutes of GPU | A peak VRAM number and a time per step |
| 7 | Choose the length; freeze dataset v1 | 20 minutes | SHA-256 of `train.jsonl` and `val.jsonl` in `NOTES.md` |
| 8 | Export rehearsal with the pilot adapter | 1 hour, mostly download | The GGUF answers one dev scenario in the edit format on the laptop |
| 9 | Untuned control through the same export | 45 minutes | The control resolves a dev scenario; one dev run recorded |
| 10 | Notes, commit | 30 minutes | Pilot log and both decisions in `NOTES.md` |

About 7 to 8 hours. It fits one day only if the Kaggle account and token are ready in the
morning. Steps 1 to 4 need neither, so they go first.

**Step 1.** A script writes `training/data/spotcheck-30.md` (ignored by git): 30 examples by
seed, each with its prompt, target, slice and source. What to look for is listed at the end of
the D16 section of `NOTES.md`: a target that calls an unseen function, a RATIONALE that only
restates the finding, a docstring that names the fix, a planted flaw in an odd place.

**Step 2.** `build` writes into `training/data/` and overwrites the last set. Give it an
output directory so that the 2,048 and the 4,096 candidates exist side by side.

**Step 8.** On Kaggle: merge the pilot adapter and export `q4_k_m` (doc 10 §6). On the laptop:
a Modelfile with `FROM`, `RENDERER qwen3.5`, `PARSER qwen3.5` and the parameters of doc 10 §8;
`ollama create aeropatch-pilot`; then
`uv run aeropatch remediate A-089-01 --config repair-local --local-model aeropatch-pilot`.
A pilot adapter of 50 steps does not have to resolve anything. It has to load, stop, and write
SEARCH/REPLACE blocks inside 3,891 MiB of VRAM (the untuned model peaked at 3,787).

**Step 9.** The same export with no adapter gives `aeropatch-control`; then
`uv run aeropatch bench --config repair-local --split dev --local-model aeropatch-control`
(a dev run took under 5 minutes on 2026-10-03, measured). Also send one prompt to the control
and to the library `qwen3.5:4b` and compare `prompt_eval_count`: equal counts mean both format
the prompt the same way. Confirm on the way that `Qwen/Qwen3.5-4B` is the checkpoint the
library tag is built from.

## 5. What `finetune.py` has to do

- **Change: mask by position, not with `train_on_responses_only`.** A repair-turn example holds
  the student's failed edits as assistant messages. Unsloth's helper is built to train on every
  assistant span, so it would teach those failures. Render `messages` with the generation prompt, render
  `messages` plus `target`, and set the label of every token of the first rendering to -100.
  The loss then covers the target and its end-of-turn token, nothing else.
- Render with the tokenizer's own chat template, thinking off (doc 09 §5).
- **Never truncate.** Count tokens with the real tokenizer and drop, with a count, any example
  over the sequence length. D16 estimated lengths at 3.6 characters per token; this replaces
  the estimate.
- **Self-checks that stop the run:** for 3 examples the unmasked labels decode to exactly the
  target; the prompt-side token count of a sampled repair turn equals what Ollama counted.
- Values of doc 10 §3: r 16 and alpha 16, learning rate 2e-4, batch 1 with accumulation 8,
  `adamw_8bit`, seed 3407. Arguments for the sequence length, the step limit (the pilot) and the
  epochs.
- After training: generate for 5 validation prompts and parse them with
  `aeropatch.agent.edits.parse`, the parser the loop uses. The repository is cloned on Kaggle,
  so nothing is copied.
- Write one `pilot.json`: loss per logged step, peak VRAM (`torch.cuda.max_memory_allocated`),
  seconds per step, examples dropped for length, the 5 outputs.
- `requirements.txt` pins what Kaggle resolved on the day (Unsloth, TRL, PEFT, transformers).
  The notebook only clones the repository, installs that file and calls the script (doc 10 §2).
- The masking is a pure function with a unit test, so it is checked on the laptop, where the
  training libraries are not installed.

**Template parity (step 4).** The student run recorded Ollama's token count for 310 prompts.
Put 20 of them in a small file with their messages. On Kaggle, render each with the Hugging
Face template and count. Equal counts for all 20 is the pass. A constant difference has to be
explained (a start token, for example) before any training; an uneven one means the two sides
format prompts differently, and doc 10 §12 says what to compare.

## 6. If something fails

| What happens | Then |
|---|---|
| Phone verification or the GPU queue holds Kaggle up | Do steps 1 to 4, then Colab T4 with the same script. If neither works today, steps 5 to 9 move to the morning of D18 and the D21 buffer pays |
| Out of memory at 2,048 | Sequence 1,536 (doc 10 §12). About 442 of the 554 examples are that short, by the D16 estimate |
| Unsloth cannot load or export Qwen3.5-4B with today's versions | Pin the versions of its Qwen3.5 guide. The fallback base, Qwen2.5-Coder-3B (doc 10 §1), is your decision, because its licence is non-commercial |
| Ollama loads the GGUF but the output has no chat format | The Modelfile lacks the renderer lines of section 1. If it still fails: `llama-server -m model.gguf -ngl 99 -c 8192 --jinja` (doc 10 §8) |
| Token counts differ between the two templates | Stop. Compare the rendered prompts byte by byte before training anything |
| The reading finds more than 3 bad examples of one kind | Write the filter, rebuild, read 30 again from a new seed |

## 7. Done when

- [ ] 30 examples read, with the verdict and any new filter in `NOTES.md`.
- [ ] Dataset v1 frozen: `train.jsonl`, `val.jsonl`, `stats.md`, the leakage report; SHA-256 of
      both files in `NOTES.md`.
- [ ] Parity: the message test (exists) and the template counts.
- [ ] Pilot log: the loss falls, peak VRAM, seconds per step, the estimated time of the full
      run, 5 parsed outputs.
- [ ] The rehearsal GGUF runs a dev scenario on the laptop.
- [ ] The control GGUF resolves a dev scenario, and its dev run is in `runs/`.

**Not on D17:** the full run (D18), anything on `test`, `test_b` or `test_c`, a second
generation run, the quant ablations, and the laptop QLoRA demo unless the day has room.
