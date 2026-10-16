# Benchmark runs

Every run in `runs/` (doc 14 part 1): run ID, config, model, split, the commit in its header,
whether the tree was dirty, and resolved of finished scenarios. The takeaway of each group is
the short form of its `NOTES.md` section. The run files themselves are git-ignored; compare two
with `uv run aeropatch report runs/<a>.jsonl runs/<b>.jsonl`.

## Week 1, D6-D7: single-attempt baselines on 10 dev scenarios

Qwen3.5-4B 5/10, Qwen2.5-Coder-3B 0/10, Opus via Claude Code 9/10; Qwen3.5-4B is the local model.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20260928-173908-oracle-dev` | oracle | reference fix | dev | `74977fe` | no | 10/10 |
| `20260928-173928-baseline-qwen3.5-4b-dev` | baseline-qwen3.5-4b | qwen3.5:4b | dev | `74977fe` | no | 5/10 |
| `20260928-174028-baseline-qwen2.5-coder-3b-dev` | baseline-qwen2.5-coder-3b | qwen2.5-coder:3b-instruct-q4_K_M | dev | `74977fe` | no | 0/10 |
| `20260929-152723-baseline-qwen3.5-4b-dev` | baseline-qwen3.5-4b | qwen3.5:4b | dev | `215bbcc` | no | 5/10 |
| `20260929-152837-baseline-qwen2.5-coder-3b-dev` | baseline-qwen2.5-coder-3b | qwen2.5-coder:3b-instruct-q4_K_M | dev | `215bbcc` | no | 0/10 |
| `20260929-152914-oracle-dev` | oracle | reference fix | dev | `215bbcc` | no | 10/10 |
| `20260929-152934-baseline-claude-code-dev` | baseline-claude-code | claude-opus-5 | dev | `215bbcc` | no | 9/10 |

## Week 2, D8-D10: the repair loop and the cascade, 10 then 13 dev scenarios

Built and tried on uncommitted code (`dirty: yes`); the committed re-run is 2026-10-03.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261001-104941-oracle-dev` | oracle | reference fix | dev | `efb01af` | no | 0/0 (of 10, unfinished) |
| `20261001-105023-oracle-dev` | oracle | reference fix | dev | `efb01af` | no | 9/10 |
| `20261001-105228-oracle-dev` | oracle | reference fix | dev | `efb01af` | no | 10/10 |
| `20261001-163033-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | no | 5/10 |
| `20261001-163541-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | no | 6/10 |
| `20261001-163914-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `f65332f` | no | 10/10 |
| `20261001-164317-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | no | 7/10 |
| `20261001-164919-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | no | 5/10 |
| `20261001-165311-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | no | 7/10 |
| `20261001-165619-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `f65332f` | no | 9/10 |
| `20261001-165958-repair-claude-code-dev` | repair-claude-code | claude-opus-5 | dev | `f65332f` | no | 10/10 |
| `20261001-170343-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `f65332f` | no | 9/10 |
| `20261001-170839-repair-claude-code-dev` | repair-claude-code | claude-opus-5 | dev | `f65332f` | no | 1/1 |
| `20261001-170856-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `f65332f` | no | 10/10 |
| `20261001-171411-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | no | 6/10 |
| `20261001-173544-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 2/3 |
| `20261001-173632-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 2/3 |
| `20261001-173825-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 0/1 |
| `20261001-173918-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 0/1 |
| `20261001-174230-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 7/13 |
| `20261001-175057-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 8/13 |
| `20261001-175545-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 9/13 |
| `20261001-180131-repair-claude-code-dev` | repair-claude-code | claude-opus-5 | dev | `f65332f` | yes | 13/13 |
| `20261001-180638-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `f65332f` | yes | 13/13 |
| `20261001-181502-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 10/13 |
| `20261001-182050-repair-local-dev` | repair-local | qwen3.5:4b | dev | `f65332f` | yes | 8/13 |
| `20261001-182615-repair-claude-code-dev` | repair-claude-code | claude-opus-5 | dev | `f65332f` | yes | 13/13 |
| `20261001-182901-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `f65332f` | yes | 0/0 (of 13, unfinished) |

## Week 2, D10-D11: dev on `3d26b27`, oracle checks of the new test scenarios

Local 10 and 7 of 13, Opus 13/13, cascade 13/13. The oracle's 12/13 was a harness bug, fixed (13/13).

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261003-113134-oracle-dev` | oracle | reference fix | dev | `3d26b27` | no | 12/13 |
| `20261003-113223-repair-local-dev` | repair-local | qwen3.5:4b | dev | `3d26b27` | no | 10/13 |
| `20261003-113658-repair-claude-code-dev` | repair-claude-code | claude-opus-5 | dev | `3d26b27` | no | 13/13 |
| `20261003-114259-cascade-claude-code-dev` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | dev | `3d26b27` | no | 13/13 |
| `20261003-115043-repair-local-dev` | repair-local | qwen3.5:4b | dev | `3d26b27` | no | 7/13 |
| `20261003-121131-oracle-dev` | oracle | reference fix | dev | `3d26b27` | yes | 13/13 |
| `20261003-121220-oracle-test` | oracle | reference fix | test | `3d26b27` | yes | 15/15 |
| `20261003-122433-oracle-test` | oracle | reference fix | test | `3d26b27` | yes | 1/1 |
| `20261003-122450-oracle-test` | oracle | reference fix | test | `3d26b27` | yes | 15/15 |
| `20261003-123850-oracle-test` | oracle | reference fix | test | `3d26b27` | yes | 20/20 |
| `20261003-124014-oracle-dev` | oracle | reference fix | dev | `3d26b27` | yes | 13/13 |

## Week 2, D13: baselines on the frozen test split (27 scenarios)

Local 17 and 18, Opus 27, cascade 26 before the loop fix and 27 after (`165008`).

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261003-155826-oracle-test-jobs2` | oracle | reference fix | test | `55e0709` | no | 27/27 |
| `20261003-155954-repair-local-test` | repair-local | qwen3.5:4b | test | `55e0709` | no | 17/27 |
| `20261003-161129-repair-claude-code-test` | repair-claude-code | claude-opus-5 | test | `55e0709` | no | 27/27 |
| `20261003-161702-cascade-claude-code-test` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | test | `55e0709` | no | 26/27 |
| `20261003-162838-repair-local-test` | repair-local | qwen3.5:4b | test | `55e0709` | no | 18/27 |
| `20261003-164650-oracle-dev` | oracle | reference fix | dev | `55e0709` | yes | 13/13 |
| `20261003-164740-oracle-test` | oracle | reference fix | test | `55e0709` | yes | 27/27 |
| `20261003-165008-cascade-claude-code-test` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | test | `9fcc75c` | no | 27/27 |

## Week 2 close-out: a killed and resumed run, Tier B (10 real CVEs), oracle re-checks

Tier B: local 5 and 5 of 10, Opus 10, cascade 10. The killed run resumed to 13 distinct results.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261005-150539-repair-local-dev-killed` | repair-local | qwen3.5:4b | dev | `2b03f0c` | no | 9/13 |
| `20261005-160005-oracle-test_b` | oracle | reference fix | test_b | `e382773` | no | 10/10 |
| `20261005-160032-repair-local-test_b` | repair-local | qwen3.5:4b | test_b | `e382773` | no | 5/10 |
| `20261005-160526-repair-claude-code-test_b` | repair-claude-code | claude-opus-5 | test_b | `e382773` | no | 10/10 |
| `20261005-160808-cascade-claude-code-test_b` | cascade-claude-code | qwen3.5:4b + claude-opus-5 | test_b | `e382773` | no | 10/10 |
| `20261005-161537-repair-local-test_b` | repair-local | qwen3.5:4b | test_b | `e382773` | no | 5/10 |
| `20261005-201044-oracle-dev` | oracle | reference fix | dev | `97e5fa8` | no | 13/13 |
| `20261005-201131-oracle-test` | oracle | reference fix | test | `97e5fa8` | no | 27/27 |
| `20261005-201324-oracle-test_b` | oracle | reference fix | test_b | `97e5fa8` | no | 10/10 |

## Week 3, D15: Tier C set aside

The oracle resolves the 5 held-out synthetic scenarios.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261006-153054-oracle-test_c` | oracle | reference fix | test_c | `1cdaebc` | yes | 5/5 |
| `20261006-153122-oracle-test_c` | oracle | reference fix | test_c | `1cdaebc` | yes | 5/5 |
| `20261006-154009-oracle-test_c` | oracle | reference fix | test_c | `1cdaebc` | yes | 5/5 |

## Week 3, D16: the student pass (training data, not a benchmark)

Untuned model over the synthetic training scenarios; its failed attempts became repair turns.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261009-student-pass` | repair-local | qwen3.5:4b | train | `4c43b51` | no | 156/189 |

## Week 3, D17-D18: the untuned control and dataset v1

Control 26/39 on dev; v1 step 64 and step 128 20/39 each: the fine-tune lost points.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261012-164903-repair-local-dev` | repair-local | aeropatch-control | dev | `cd65efa` | no | 9/13 |
| `20261012-171355-repair-local-dev` | repair-local | aeropatch-control | dev | `97ae347` | no | 8/13 |
| `20261012-171917-repair-local-dev` | repair-local | aeropatch-control | dev | `97ae347` | no | 9/13 |
| `20261012-201541-repair-local-dev` | repair-local | aeropatch-step64 | dev | `978d0e1` | no | 7/13 |
| `20261012-201954-repair-local-dev` | repair-local | aeropatch-step64 | dev | `978d0e1` | no | 7/13 |
| `20261012-202425-repair-local-dev` | repair-local | aeropatch-step64 | dev | `978d0e1` | no | 6/13 |
| `20261012-202913-repair-local-dev` | repair-local | aeropatch-step128 | dev | `978d0e1` | no | 7/13 |
| `20261012-203246-repair-local-dev` | repair-local | aeropatch-step128 | dev | `978d0e1` | no | 7/13 |
| `20261012-203620-repair-local-dev` | repair-local | aeropatch-step128 | dev | `978d0e1` | no | 6/13 |

## Week 3, D19: why v1 lost points

The finding forced as RATIONALE drops the control to 21/39 (prefill-plan 26); v1 step 32 is 20/39; handed the control's plan, v1 step 64 makes 16 to the control's 20. Prefill runs are `dirty: yes`.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261013-102945-prefill-plan-dev` | prefill-plan | aeropatch-control | dev | `f43f77a` | yes | 8/13 |
| `20261013-103404-prefill-finding-dev` | prefill-finding | aeropatch-control | dev | `f43f77a` | yes | 7/13 |
| `20261013-103745-prefill-plan-dev` | prefill-plan | aeropatch-control | dev | `f43f77a` | yes | 9/13 |
| `20261013-104224-prefill-finding-dev` | prefill-finding | aeropatch-control | dev | `f43f77a` | yes | 8/13 |
| `20261013-104622-prefill-plan-dev` | prefill-plan | aeropatch-control | dev | `f43f77a` | yes | 9/13 |
| `20261013-105029-prefill-finding-dev` | prefill-finding | aeropatch-control | dev | `f43f77a` | yes | 6/13 |
| `20261013-105642-repair-local-dev` | repair-local | aeropatch-step32 | dev | `f43f77a` | no | 5/13 |
| `20261013-110052-repair-local-dev` | repair-local | aeropatch-step32 | dev | `f43f77a` | no | 7/13 |
| `20261013-110550-repair-local-dev` | repair-local | aeropatch-step32 | dev | `f43f77a` | no | 8/13 |
| `20261013-111826-prefill-control-plan-dev` | prefill-control-plan | aeropatch-control | dev | `f43f77a` | yes | 7/13 |
| `20261013-112025-prefill-control-plan-dev` | prefill-control-plan | aeropatch-step64 | dev | `f43f77a` | yes | 5/13 |
| `20261013-112212-prefill-control-plan-dev` | prefill-control-plan | aeropatch-control | dev | `f43f77a` | yes | 6/13 |
| `20261013-112406-prefill-control-plan-dev` | prefill-control-plan | aeropatch-step64 | dev | `f43f77a` | yes | 6/13 |
| `20261013-112600-prefill-control-plan-dev` | prefill-control-plan | aeropatch-control | dev | `f43f77a` | yes | 7/13 |
| `20261013-112755-prefill-control-plan-dev` | prefill-control-plan | aeropatch-step64 | dev | `f43f77a` | yes | 5/13 |

## Week 3, D19: dataset v2

v2 step 64 26/39, the control's score; v2 step 128 23/39.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261013-151854-repair-local-dev` | repair-local | aeropatch-v2-step64 | dev | `f43f77a` | no | 8/13 |
| `20261013-152453-repair-local-dev` | repair-local | aeropatch-v2-step128 | dev | `f43f77a` | no | 8/13 |
| `20261013-153130-repair-local-dev` | repair-local | aeropatch-v2-step64 | dev | `f43f77a` | no | 9/13 |
| `20261013-153655-repair-local-dev` | repair-local | aeropatch-v2-step128 | dev | `f43f77a` | no | 7/13 |
| `20261013-154255-repair-local-dev` | repair-local | aeropatch-v2-step64 | dev | `f43f77a` | no | 9/13 |
| `20261013-154843-repair-local-dev` | repair-local | aeropatch-v2-step128 | dev | `f43f77a` | no | 8/13 |

## Week 3, D20: the test runs and speed on a quiet GPU

Test of 54: untuned control 38 (19 + 19), v2 step 64 32 (18 + 14), a loss by the rule set before the runs, so Week 4 runs the untuned model. Tier B of 20: 7 against 3; Tier C of 10: 9 each. On a quiet GPU both decode at about 46.5 tokens a second and peak at 3,043 MiB.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261013-170329-repair-local-test` | repair-local | aeropatch-control | test | `c03f33f` | no | 19/27 |
| `20261014-121928-repair-local-dev` | repair-local | aeropatch-control | dev | `c03f33f` | no | 9/13 |
| `20261014-122421-repair-local-dev` | repair-local | aeropatch-v2-step64 | dev | `c03f33f` | no | 8/13 |
| `20261014-123112-repair-local-test` | repair-local | aeropatch-v2-step64 | test | `c03f33f` | no | 18/27 |
| `20261014-124302-repair-local-test` | repair-local | aeropatch-control | test | `c03f33f` | no | 19/27 |
| `20261014-125354-repair-local-test` | repair-local | aeropatch-v2-step64 | test | `c03f33f` | no | 14/27 |
| `20261014-130652-repair-local-test_b` | repair-local | aeropatch-control | test_b | `c03f33f` | no | 4/10 |
| `20261014-131242-repair-local-test_b` | repair-local | aeropatch-v2-step64 | test_b | `c03f33f` | no | 2/10 |
| `20261014-131647-repair-local-test_b` | repair-local | aeropatch-control | test_b | `c03f33f` | no | 3/10 |
| `20261014-132226-repair-local-test_b` | repair-local | aeropatch-v2-step64 | test_b | `c03f33f` | no | 1/10 |
| `20261014-132647-repair-local-test_c` | repair-local | aeropatch-control | test_c | `c03f33f` | no | 5/5 |
| `20261014-132803-repair-local-test_c` | repair-local | aeropatch-v2-step64 | test_c | `c03f33f` | no | 4/5 |
| `20261014-132909-repair-local-test_c` | repair-local | aeropatch-control | test_c | `c03f33f` | no | 4/5 |
| `20261014-133016-repair-local-test_c` | repair-local | aeropatch-v2-step64 | test_c | `c03f33f` | no | 5/5 |

## Week 4, D22-D24: pass@k, the cascade and the frontier on Opus 5.5, adversarial, ablations

Control pass@1/3/5 on test 45/61/67% (repair loop 70%); cascade 27, 9, 5 in both passes and Opus 5.5 alone 27, 10, 5 on test, Tier B, Tier C; injection followed 0 of 4 in every adversarial run; Q5, Q8 and thinking each 41 of 54 against the control's 38, no difference shown.

| Run | Config | Model | Split | Commit | Dirty | Resolved |
|---|---|---|---|---|---|---|
| `20261016-s1-sample-local-test` | sample-local | aeropatch-control | test | `1337883` | no | 12/27 |
| `20261016-s1-sample-local-test_b` | sample-local | aeropatch-control | test_b | `c31af0e` | no | 4/10 |
| `20261016-s1-sample-local-test_c` | sample-local | aeropatch-control | test_c | `4cef739` | no | 2/5 |
| `20261016-s2-sample-local-test` | sample-local | aeropatch-control | test | `4cef739` | no | 12/27 |
| `20261016-s2-sample-local-test_b` | sample-local | aeropatch-control | test_b | `8a8ea58` | no | 1/10 |
| `20261016-s2-sample-local-test_c` | sample-local | aeropatch-control | test_c | `8a8ea58` | no | 3/5 |
| `20261016-s3-sample-local-test` | sample-local | aeropatch-control | test | `8a8ea58` | no | 12/27 |
| `20261016-s3-sample-local-test_b` | sample-local | aeropatch-control | test_b | `8a8ea58` | no | 4/10 |
| `20261016-s3-sample-local-test_c` | sample-local | aeropatch-control | test_c | `8a8ea58` | no | 3/5 |
| `20261016-s4-sample-local-test` | sample-local | aeropatch-control | test | `8a8ea58` | no | 13/27 |
| `20261016-s4-sample-local-test_b` | sample-local | aeropatch-control | test_b | `8a8ea58` | no | 1/10 |
| `20261016-s4-sample-local-test_c` | sample-local | aeropatch-control | test_c | `8a8ea58` | no | 3/5 |
| `20261016-s5-sample-local-test` | sample-local | aeropatch-control | test | `8a8ea58` | no | 12/27 |
| `20261016-s5-sample-local-test_b` | sample-local | aeropatch-control | test_b | `8a8ea58` | no | 3/10 |
| `20261016-s5-sample-local-test_c` | sample-local | aeropatch-control | test_c | `8a8ea58` | no | 5/5 |
| `20261016-c1-cascade-claude-code-test` | cascade-claude-code | aeropatch-control + claude-opus-5-5 | test | `8a8ea58` | no | 27/27 |
| `20261016-c1-cascade-claude-code-test_b` | cascade-claude-code | aeropatch-control + claude-opus-5-5 | test_b | `c9d69b1` | no | 9/10 |
| `20261016-c1-cascade-claude-code-test_c` | cascade-claude-code | aeropatch-control + claude-opus-5-5 | test_c | `c9d69b1` | no | 5/5 |
| `20261016-f1-repair-claude-code-test` | repair-claude-code | claude-opus-5-5 | test | `c9d69b1` | no | 27/27 |
| `20261016-f1-repair-claude-code-test_b` | repair-claude-code | claude-opus-5-5 | test_b | `c9d69b1` | no | 10/10 |
| `20261016-f1-repair-claude-code-test_c` | repair-claude-code | claude-opus-5-5 | test_c | `c9d69b1` | no | 5/5 |
| `20261016-c2-cascade-claude-code-test` | cascade-claude-code | aeropatch-control + claude-opus-5-5 | test | `c9d69b1` | no | 27/27 |
| `20261016-c2-cascade-claude-code-test_b` | cascade-claude-code | aeropatch-control + claude-opus-5-5 | test_b | `c9d69b1` | no | 9/10 |
| `20261016-c2-cascade-claude-code-test_c` | cascade-claude-code | aeropatch-control + claude-opus-5-5 | test_c | `c9d69b1` | no | 5/5 |
| `20261016-a1-repair-local-adversarial` | repair-local | aeropatch-control | adversarial | `c9d69b1` | no | 4/5 |
| `20261016-f1-repair-claude-code-adversarial` | repair-claude-code | claude-opus-5-5 | adversarial | `c9d69b1` | no | 4/5 |
| `20261016-a2-repair-local-adversarial` | repair-local | aeropatch-control | adversarial | `c9d69b1` | no | 4/5 |
| `20261016-q5a-repair-local-test` | repair-local | aeropatch-control-q5 | test | `ebeb7e9` | no | 21/27 |
| `20261016-q5b-repair-local-test` | repair-local | aeropatch-control-q5 | test | `ebeb7e9` | no | 20/27 |
| `20261016-q8a-repair-local-q8-test` | repair-local-q8 | aeropatch-control-q8 | test | `b59acee` | no | 22/27 |
| `20261016-q8b-repair-local-q8-test` | repair-local-q8 | aeropatch-control-q8 | test | `1810d77` | no | 19/27 |
| `20261016-tka-repair-local-think-test` | repair-local-think | aeropatch-control | test | `1810d77` | no | 21/27 |
| `20261016-tkb-repair-local-think-test` | repair-local-think | aeropatch-control | test | `d954d1b` | no | 20/27 |
