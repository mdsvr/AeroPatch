# Training set statistics

Written by `uv run python training/prepare_dataset.py build`. Counts only: the examples stay on the laptop (doc 09 §2).

**470 examples**: 445 in `train.jsonl` and 25 in `val.jsonl`, which holds whole repositories and whole synthetic scenarios.

## Filters, in the order of doc 09 §7

Pairs left after each step. Test files and the 60-line limit were applied when the pairs were mined.

| Step | ghsa | synthetic | swe-gym | swe-smith | all |
|---|---|---|---|---|---|
| Converted pairs, and synthetic examples kept by the sandbox | 531 | 189 | 555 | 339 | 1614 |
| Language: a Python file, and a CWE on the advisory | 510 | 189 | 555 | 339 | 1593 |
| Reading: not a fix that was read and rejected (training/rejected.txt, doc 09 §10) | 510 | 169 | 555 | 339 | 1573 |
| Size: at most 60 changed lines, in at most 2 functions | 419 | 169 | 472 | 288 | 1348 |
| Noise: at most 6 hunks, none of them whitespace only; no SWE-smith bug that a comment announces | 401 | 169 | 460 | 203 | 1233 |
| Context: every SEARCH line is in the prompt (not in doc 09) | 304 | 169 | 384 | 160 | 1017 |
| Names: the fix uses no function, class or constant of the file that the prompt hides (not in doc 09) | 303 | 144 | 373 | 160 | 980 |
| Gates: the fix passes the loop's safety gates (not in doc 09) | 292 | 144 | 370 | 160 | 966 |
| Dedupe: at most 2 functions that share 80% of their blanked 5-token runs | 292 | 144 | 369 | 160 | 965 |
| Length: prompt and target within 2048 tokens | 251 | 144 | 222 | 143 | 760 |
| Secrets: no key or token pattern | 244 | 144 | 207 | 143 | 738 |
| Leakage: no benchmark project, no advisory after the cutoff, no copied benchmark code | 240 | 105 | 206 | 143 | 694 |
| Diversity: at most 30 per CWE and repository | 240 | 105 | 203 | 143 | 691 |
| Mix: general bug fixes are 20% of the examples | 240 | 105 | 33 | 61 | 439 |

## Examples by slice

| Slice | Examples | Share | Doc 09 §8 | Sources |
|---|---|---|---|---|
| first | 345 | 73% | 55% | ghsa 240, synthetic 105 |
| repair | 31 | 7% | 20% | synthetic 31 |
| general | 94 | 20% | 20% | swe-gym 33, swe-smith 61 |
| format practice, inside the slices above | 38 | 8% | 5% | repairs after a format failure 1, fixes of 3 or more blocks 37 |

- Checked by the sandbox (the synthetic examples, first attempts and repair turns): 136. The other 334 re-apply byte-exact and have no test.
- Synthetic examples that met validator check 3 only through a PoC test: 48.

## Student pass

Run `20261009-student-pass`: the untuned student on every kept synthetic scenario, three attempts each.

- 189 scenarios: 111 resolved at the first attempt, 156 within three.
- 57 failed attempts on scenarios in the set; 24 are over the length limit and 2 fail the leakage check, so 31 repair turns are in the set: 23 after POC_FAIL, 5 after REGRESSION, 1 after SEARCH_NOT_FOUND, 1 after GATE_REJECT, 1 after IMPORT_ERROR.
- Scenarios whose rebuilt conversation differs from a prompt on disk: 0. 30 of the repair turns in the set were sent to the student as its next prompt and were compared with it; the others end a conversation, so no prompt on disk holds them.
- Repair turns that follow a third attempt, a conversation `repair-local` never sends: 1.

## By CWE

| CWE | Examples | ghsa | synthetic | swe-gym | swe-smith |
|---|---|---|---|---|---|
| Bug | 94 | 0 | 0 | 33 | 61 |
| CWE-79 | 30 | 19 | 11 | 0 | 0 |
| CWE-918 | 30 | 7 | 23 | 0 | 0 |
| CWE-22 | 26 | 23 | 3 | 0 | 0 |
| CWE-20 | 25 | 10 | 15 | 0 | 0 |
| CWE-328 | 20 | 0 | 20 | 0 | 0 |
| CWE-601 | 19 | 9 | 10 | 0 | 0 |
| CWE-327 | 18 | 1 | 17 | 0 | 0 |
| CWE-200 | 16 | 16 | 0 | 0 | 0 |
| CWE-89 | 13 | 4 | 9 | 0 | 0 |
| CWE-78 | 12 | 4 | 8 | 0 | 0 |
| CWE-502 | 9 | 6 | 3 | 0 | 0 |
| CWE-77 | 8 | 8 | 0 | 0 | 0 |
| CWE-94 | 8 | 8 | 0 | 0 | 0 |
| CWE-1333 | 7 | 3 | 4 | 0 | 0 |
| CWE-400 | 7 | 7 | 0 | 0 | 0 |
| CWE-352 | 7 | 5 | 2 | 0 | 0 |
| CWE-338 | 6 | 1 | 5 | 0 | 0 |
| CWE-284 | 5 | 5 | 0 | 0 | 0 |
| CWE-276 | 5 | 5 | 0 | 0 | 0 |
| CWE-209 | 4 | 2 | 2 | 0 | 0 |
| CWE-770 | 4 | 4 | 0 | 0 | 0 |
| CWE-377 | 4 | 4 | 0 | 0 | 0 |
| CWE-798 | 4 | 0 | 4 | 0 | 0 |
| CWE-1336 | 3 | 3 | 0 | 0 | 0 |
| 62 others | 86 |  |  |  |  |

## Length

Tokens of prompt and target together, counted with the tokenizer of `Qwen/Qwen3.5-4B` as `finetune.py` encodes an example. Over the limit of 2048: 205 pairs at the length step and 24 repair turns. Within 4096: 165 and 22 of them.

| Tokens | Examples |  |
|---|---|---|
| 0-255 | 0 |  |
| 256-511 | 2 | # |
| 512-767 | 70 | ################## |
| 768-1023 | 158 | ######################################## |
| 1024-1279 | 106 | ########################### |
| 1280-1535 | 62 | ################ |
| 1536-1791 | 40 | ########## |
| 1792-2047 | 31 | ######## |
| 2048-2303 | 1 |  |

## Leakage

- Pairs from a benchmark project: 0. Advisories published on or after 2026-01-01: 0.
- Dropped at the leakage step: 44 pairs. 34 share a 13-token run with a line that a benchmark reference fix removes or adds. The others are over the limit of shared runs with one scenario (by tier: A 30, B 30, C 0), or their function overlaps a benchmark target function by 50% or more with identifiers blanked.
- In the set, 45 of 439 pairs share at least one 13-token run with a benchmark scenario, none with a fix line.
- A repair turn adds the student's edits and the test output to its scenario's prompt. By the same limits 2 turns were dropped, and 4 of the 31 in the set share a run with a benchmark scenario.
- `training/data/leakage.md` lists each of them and each shared passage.
