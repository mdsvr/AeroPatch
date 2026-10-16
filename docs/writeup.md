# A 4B model, a 4 GB GPU, and 55 Python vulnerabilities

Can a small open model, running on a laptop GPU, fix real security bugs, and know when to ask
for help? I spent four weeks building AeroPatch to measure that rather than argue it. This is
what came out, including the part that did not work.

## The setup

AeroPatch takes a scanner finding (Opengrep or Bandit), cuts the vulnerable function and its
imports out with tree-sitter, and asks a model for a minimal fix as SEARCH/REPLACE blocks. The
model has no tools and no shell: it is a function from text to edits. The harness applies the
edits to a scratch copy, runs eight deterministic gates (no test edits, no new risky imports, no
`# nosec`, no deleted functions, size limits), then runs the scenario's exploit test and
regression tests in a Docker container with no network, a read-only root and dropped
capabilities. A failure goes back to the model as trimmed test output, up to three attempts.

The model is Qwen3.5-4B at 4-bit, served by Ollama on an RTX 3050 Laptop GPU with 4 GB of VRAM:
100% on the GPU, about 3 GB used, 46 tokens a second.

The benchmark has three tiers, frozen before any tuning: 40 hand-built scenarios over 16 CWEs
(13 dev, 27 test), 10 real CVEs from other projects with their upstream fixes, and 5 synthetic
scenarios held out of the training data. Every comparison was decided by a rule written before
the runs, and every number traces to a committed run file.

## What the small model does alone

On the 27 test scenarios, two runs each, the untuned 4B model resolves **38 of 54 (70%)** with no
API cost. On the real CVEs it manages **7 of 20 (35%)**. With so few scenarios the intervals are
wide (57–81% and 18–57%), so these are rough positions, not leaderboard numbers.

Where it fails is consistent. Path traversal through archive extraction, unsalted password
hashing and SSRF are never fixed in either run: each needs a piece of knowledge the model does
not bring, such as checking the resolved address rather than the hostname, or changing a hash and
its verifier together. More samples do not find it either.

## Fine-tuning made it worse

I fine-tuned the same model with LoRA on a free Kaggle T4: 541 examples, all verified in the
sandbox, from GitHub security advisories, synthetic fixes made by a local 9B teacher, the small
model's own failed attempts turned into repair turns, and general bug fixes. The comparison was
against an untuned control exported through the identical path, so only the adapter differed.

On dev the tuned model tied (26 of 39 each). On test it lost: **32 of 54 against 38**, and 3 of 20
against 7 on the real CVEs. The gap alone is not significant (McNemar p = 0.15), but the rule I
had written down called four or more below a loss, so the untuned model went into the final week.
The failure analysis shows why: the tuned model's fixes break existing behaviour more often, and
after feedback it repeats the same edit nine times where the untuned model never did. My reading
is that 541 examples taught it a format more than security knowledge. I report it as the null
result it is.

## Feedback beats resampling, mostly

Is the repair loop just a fancy way of sampling three times? I ran five independent one-attempt
runs per split and computed pass@k. On test, three repair attempts resolve 70% where three
independent samples reach 61%: the test feedback is worth something. On the ten real CVEs it is
the other way round, 35% against 45%, which is a reminder of how small that tier is.

## The cascade, and what it really costs

The cascade gives the local model two attempts and hands the third to Claude Opus 5.5. It
resolves **54 of 54** test runs, 32 of them without any frontier call, and 18 of 20 on the real
CVEs, against 10 of 10 for Opus alone. It misses one CVE twice: its single Opus attempt breaks a
regression test, where Opus alone fixes it with feedback on the next try.

The cost result surprised me. Per resolved scenario the cascade is only 8% cheaper than Opus
alone on the hand-built tier and no cheaper on the real CVEs, mostly because escalation sends
the local model's whole failed history along with the task. A shorter escalation prompt is the obvious next experiment.

## Prompt injection: zero for twelve

Five adversarial copies of one scenario carry a planted instruction: post `os.environ` to a URL,
delete a test assertion, add `# nosec`, change CI configuration from the advisory text, and a
credential sitting beside the code. Neither the local model nor Opus followed any of the four
instructions in three runs, and both fixed the real flaw. The credential was blocked before any
prompt left the machine. I also wrote, by hand, the edit that obeys each instruction: the gates
reject all of them except one. A bare `requests.post(...)` added without an import passes every
gate, and only the sandbox and the tests stop it. That is the gap to close first.

## Quantisation and thinking did not matter

Q5 and Q8 builds, and thinking mode, each scored 41 of 54 against the control's 38, under the
bar set in advance. Q8 does not fit 4 GB whole and runs at a third of the speed, so the 4-bit
model stays.

## What I would do next

A shorter escalation prompt; a gate for risky calls whose module is already imported; a larger
fine-tuning set aimed at the three classes the model never fixes; a microVM sandbox on a Linux
host; and more real CVEs, because ten is too few to separate anything.

The limits are worth stating plainly: Python only, function-level fixes, a small benchmark, tests
as the oracle, and one laptop. A passing exploit test is evidence, not proof. Every fix is a
candidate for a person to review.

Code, benchmark, run files and the full notes: this repository
([README](../README.md), [NOTES](../NOTES.md)).
