# Training set statistics

Written by `uv run python training/prepare_dataset.py build`. Counts only: the examples stay on the laptop (doc 09 §2).

**541 examples**: 511 in `train.jsonl` and 30 in `val.jsonl`, which holds whole repositories and whole synthetic scenarios.

## Filters, in the order of doc 09 §7

Pairs left after each step. Test files and the 60-line limit were applied when the pairs were mined.

| Step | ghsa | synthetic | swe-gym | swe-smith | all |
|---|---|---|---|---|---|
| Converted pairs, and synthetic examples kept by the sandbox | 531 | 189 | 555 | 339 | 1614 |
| Language: a Python file, and a CWE on the advisory | 510 | 189 | 555 | 339 | 1593 |
| Reading: not a fix that was read and rejected (training/rejected.txt, doc 09 §10) | 510 | 169 | 555 | 339 | 1573 |
| Size: at most 60 changed lines, in at most 2 functions | 419 | 169 | 472 | 288 | 1348 |
| Noise: at most 6 hunks, none of them whitespace only; no SWE-smith bug that a comment announces | 401 | 169 | 460 | 203 | 1233 |
| Context: every SEARCH line is in the prompt (not in doc 09) | 304 | 169 | 384 | 161 | 1018 |
| Names: the fix uses no function, class or constant of the file that the prompt hides (not in doc 09) | 303 | 144 | 373 | 161 | 981 |
| Gates: the fix passes the loop's safety gates (not in doc 09) | 292 | 144 | 370 | 161 | 967 |
| Dedupe: at most 2 functions that share 80% of their blanked 5-token runs | 292 | 144 | 369 | 161 | 966 |
| Length: prompt and target within 4096 tokens | 288 | 144 | 333 | 161 | 926 |
| Secrets: no key or token pattern | 279 | 144 | 315 | 161 | 899 |
| Leakage: no benchmark project, no advisory after the cutoff, no copied benchmark code | 275 | 105 | 314 | 161 | 855 |
| Diversity: at most 30 per CWE and repository | 275 | 105 | 290 | 161 | 831 |
| Mix: general bug fixes are 20% of the examples | 275 | 105 | 44 | 64 | 488 |
| Plan: the RATIONALE says what the fix does, and the target still passes length, secrets and leakage | 275 | 105 | 44 | 64 | 488 |

## Examples by slice

| Slice | Examples | Share | Doc 09 §8 | Sources |
|---|---|---|---|---|
| first | 380 | 70% | 55% | ghsa 275, synthetic 105 |
| repair | 53 | 10% | 20% | synthetic 53 |
| general | 108 | 20% | 20% | swe-gym 44, swe-smith 64 |
| format practice, inside the slices above | 49 | 9% | 5% | repairs after a format failure 7, fixes of 3 or more blocks 42 |

- Checked by the sandbox (the synthetic examples, first attempts and repair turns): 158. The other 383 re-apply byte-exact and have no test.
- Synthetic examples that met validator check 3 only through a PoC test: 59.
- First attempts and bug fixes with a block that starts at a `def`, `class` or decorator line: 206 of 488.
- The RATIONALE of every target was written by `qwen3.5:4b` from the fix (`build --plans`), 488 of them in this build and the rest read from `plans.jsonl`. The step dropped 0 pairs and 0 repair turns: no usable line in two answers, or a target that no longer passes the length, secret or leakage check.

## Student pass

Run `20261009-student-pass`: the untuned student on every kept synthetic scenario, three attempts each.

- 189 scenarios: 111 resolved at the first attempt, 156 within three.
- 57 failed attempts on scenarios in the set; 2 are over the length limit and 2 fail the leakage check, so 53 repair turns are in the set: 34 after POC_FAIL, 9 after REGRESSION, 4 after FORMAT_FAIL, 3 after SEARCH_NOT_FOUND, 2 after GATE_REJECT, 1 after IMPORT_ERROR.
- Scenarios whose rebuilt conversation differs from a prompt on disk: 0. 43 of the repair turns in the set were sent to the student as its next prompt and were compared with it; the others end a conversation, so no prompt on disk holds them.
- Repair turns that follow a third attempt, a conversation `repair-local` never sends: 8.

## By CWE

| CWE | Examples | ghsa | synthetic | swe-gym | swe-smith |
|---|---|---|---|---|---|
| Bug | 108 | 0 | 0 | 44 | 64 |
| CWE-918 | 39 | 7 | 32 | 0 | 0 |
| CWE-79 | 34 | 23 | 11 | 0 | 0 |
| CWE-22 | 30 | 27 | 3 | 0 | 0 |
| CWE-20 | 27 | 11 | 16 | 0 | 0 |
| CWE-328 | 25 | 0 | 25 | 0 | 0 |
| CWE-601 | 22 | 10 | 12 | 0 | 0 |
| CWE-200 | 18 | 18 | 0 | 0 | 0 |
| CWE-327 | 18 | 1 | 17 | 0 | 0 |
| CWE-78 | 15 | 4 | 11 | 0 | 0 |
| CWE-89 | 13 | 4 | 9 | 0 | 0 |
| CWE-502 | 10 | 7 | 3 | 0 | 0 |
| CWE-94 | 10 | 10 | 0 | 0 | 0 |
| CWE-352 | 9 | 5 | 4 | 0 | 0 |
| CWE-77 | 8 | 8 | 0 | 0 | 0 |
| CWE-1333 | 8 | 4 | 4 | 0 | 0 |
| CWE-284 | 7 | 7 | 0 | 0 | 0 |
| CWE-400 | 7 | 7 | 0 | 0 | 0 |
| CWE-338 | 6 | 1 | 5 | 0 | 0 |
| CWE-287 | 5 | 5 | 0 | 0 | 0 |
| CWE-276 | 5 | 5 | 0 | 0 | 0 |
| CWE-209 | 4 | 2 | 2 | 0 | 0 |
| CWE-770 | 4 | 4 | 0 | 0 | 0 |
| CWE-444 | 4 | 4 | 0 | 0 | 0 |
| CWE-377 | 4 | 4 | 0 | 0 | 0 |
| 67 others | 101 |  |  |  |  |

## Length

Tokens of prompt and target together, counted with the tokenizer of `Qwen/Qwen3.5-4B` as `finetune.py` encodes an example. Over the limit of 4096: 40 pairs at the length step and 2 repair turns. Within 8192: 38 and 2 of them.

| Tokens | Examples |  |
|---|---|---|
| 0-255 | 0 |  |
| 256-511 | 1 |  |
| 512-767 | 49 | ############ |
| 768-1023 | 157 | ######################################## |
| 1024-1279 | 113 | ############################# |
| 1280-1535 | 71 | ################## |
| 1536-1791 | 40 | ########## |
| 1792-2047 | 31 | ######## |
| 2048-2303 | 22 | ###### |
| 2304-2559 | 16 | #### |
| 2560-2815 | 15 | #### |
| 2816-3071 | 9 | ## |
| 3072-3327 | 7 | ## |
| 3328-3583 | 4 | # |
| 3584-3839 | 3 | # |
| 3840-4095 | 3 | # |

## Leakage

- Pairs from a benchmark project: 0. Advisories published on or after 2026-01-01: 0.
- Dropped at the leakage step: 44 pairs. 34 share a 13-token run with a line that a benchmark reference fix removes or adds. The others are over the limit of shared runs with one scenario (by tier: A 30, B 30, C 0), or their function overlaps a benchmark target function by 50% or more with identifiers blanked.
- In the set, 54 of 488 pairs share at least one 13-token run with a benchmark scenario, none with a fix line.
- A repair turn adds the student's edits and the test output to its scenario's prompt. By the same limits 2 turns were dropped, and 6 of the 53 in the set share a run with a benchmark scenario.
- `training/data/leakage.md` lists each of them and each shared passage.
