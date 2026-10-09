# Training set statistics

Written by `uv run python training/prepare_dataset.py build`. Counts only: the examples stay on the laptop (doc 09 §2).

**554 examples**: 526 in `train.jsonl` and 28 in `val.jsonl`, which holds whole repositories and whole synthetic scenarios.

## Filters, in the order of doc 09 §7

Pairs left after each step. Test files and the 60-line limit were applied when the pairs were mined.

| Step | ghsa | synthetic | swe-gym | swe-smith | all |
|---|---|---|---|---|---|
| Converted pairs, and synthetic examples kept by the sandbox | 531 | 189 | 555 | 339 | 1614 |
| Language: a Python file, and a CWE on the advisory | 510 | 189 | 555 | 339 | 1593 |
| Size: at most 60 changed lines, in at most 2 functions | 419 | 189 | 472 | 288 | 1368 |
| Noise: at most 6 hunks, none of them whitespace only | 401 | 189 | 460 | 238 | 1288 |
| Context: every SEARCH line is in the prompt (not in doc 09) | 304 | 189 | 384 | 179 | 1056 |
| Gates: the fix passes the loop's safety gates (not in doc 09) | 293 | 189 | 381 | 179 | 1042 |
| Dedupe: at most 2 functions that share 80% of their blanked 5-token runs | 293 | 188 | 380 | 179 | 1040 |
| Length: prompt and target within about 2048 tokens | 238 | 188 | 206 | 157 | 789 |
| Secrets: no key or token pattern | 232 | 188 | 192 | 157 | 769 |
| Leakage: no benchmark project, no advisory after the cutoff, no copied benchmark code | 228 | 146 | 191 | 157 | 722 |
| Diversity: at most 30 per CWE and repository | 228 | 146 | 189 | 157 | 720 |
| Mix: general bug fixes are 20% of the examples | 228 | 146 | 44 | 67 | 485 |

## Examples by slice

| Slice | Examples | Share | Doc 09 §8 | Sources |
|---|---|---|---|---|
| first | 374 | 68% | 55% | ghsa 228, synthetic 146 |
| repair | 69 | 12% | 20% | synthetic 69 |
| general | 111 | 20% | 20% | swe-gym 44, swe-smith 67 |
| format practice, inside the slices above | 47 | 8% | 5% | repairs after a format failure 11, fixes of 3 or more blocks 36 |

- Checked by the sandbox (the synthetic examples, first attempts and repair turns): 215. The other 339 re-apply byte-exact and have no test.
- Synthetic examples that met validator check 3 only through a PoC test: 72.

## Student pass

Run `20261009-student-pass`: the untuned student on every kept synthetic scenario, three attempts each.

- 189 scenarios: 111 resolved at the first attempt, 156 within three.
- 119 failed attempts on scenarios in the set; 46 are over the length limit and 4 fail the leakage check, so 69 repair turns are in the set: 45 after POC_FAIL, 11 after REGRESSION, 6 after FORMAT_FAIL, 3 after SEARCH_AMBIGUOUS, 2 after SEARCH_NOT_FOUND, 1 after GATE_REJECT, 1 after IMPORT_ERROR.
- Scenarios whose rebuilt conversation differs from a prompt on disk: 0. 64 of the repair turns in the set were sent to the student as its next prompt and were compared with it; the others end a conversation, so no prompt on disk holds them.
- 3 repair turns follow a third attempt, a conversation that `repair-local` never sends.

## By CWE

| CWE | Examples | ghsa | synthetic | swe-gym | swe-smith |
|---|---|---|---|---|---|
| Bug | 111 | 0 | 0 | 44 | 67 |
| CWE-918 | 43 | 7 | 36 | 0 | 0 |
| CWE-22 | 35 | 21 | 14 | 0 | 0 |
| CWE-20 | 33 | 9 | 24 | 0 | 0 |
| CWE-79 | 31 | 19 | 12 | 0 | 0 |
| CWE-601 | 31 | 8 | 23 | 0 | 0 |
| CWE-328 | 26 | 0 | 26 | 0 | 0 |
| CWE-327 | 18 | 1 | 17 | 0 | 0 |
| CWE-200 | 17 | 17 | 0 | 0 | 0 |
| CWE-78 | 17 | 4 | 13 | 0 | 0 |
| CWE-798 | 17 | 0 | 17 | 0 | 0 |
| CWE-89 | 13 | 4 | 9 | 0 | 0 |
| CWE-352 | 11 | 4 | 7 | 0 | 0 |
| CWE-502 | 9 | 6 | 3 | 0 | 0 |
| CWE-77 | 8 | 8 | 0 | 0 | 0 |
| CWE-94 | 8 | 8 | 0 | 0 | 0 |
| CWE-338 | 8 | 1 | 7 | 0 | 0 |
| CWE-1333 | 7 | 3 | 4 | 0 | 0 |
| CWE-400 | 6 | 6 | 0 | 0 | 0 |
| CWE-284 | 5 | 5 | 0 | 0 | 0 |
| CWE-276 | 5 | 5 | 0 | 0 | 0 |
| CWE-209 | 4 | 1 | 3 | 0 | 0 |
| CWE-770 | 4 | 4 | 0 | 0 | 0 |
| CWE-377 | 4 | 4 | 0 | 0 | 0 |
| CWE-116 | 3 | 3 | 0 | 0 | 0 |
| 59 others | 80 |  |  |  |  |

## Length

Tokens of prompt and target together, estimated at 3.6 characters per token; for a repair turn the student was sent, Ollama's own count of the prompt.

Over the limit of 2048: 251 pairs at the length step and 46 repair turns. Within 4096: 202 and 41 of them.

| Tokens | Examples |  |
|---|---|---|
| 0-255 | 0 |  |
| 256-511 | 1 |  |
| 512-767 | 48 | ############ |
| 768-1023 | 157 | ######################################## |
| 1024-1279 | 138 | ################################### |
| 1280-1535 | 98 | ######################### |
| 1536-1791 | 56 | ############## |
| 1792-2047 | 56 | ############## |

## Leakage

- Pairs from a benchmark project: 0. Advisories published on or after 2026-01-01: 0.
- Dropped at the leakage step: 47 pairs. 37 share a 13-token run with a line that a benchmark reference fix removes or adds. The others are over the limit of shared runs with one scenario (by tier: A 30, B 30, C 0), or their function overlaps a benchmark target function by 50% or more with identifiers blanked.
- In the set, 48 of 485 pairs share at least one 13-token run with a benchmark scenario, none with a fix line.
- A repair turn adds the student's edits and the test output to its scenario's prompt. By the same limits 4 turns were dropped, and 6 of the 69 in the set share a run with a benchmark scenario.
- `training/data/leakage.md` lists each of them and each shared passage.
