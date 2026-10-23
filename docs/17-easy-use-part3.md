# 17 — Easy Use for Non-Experts, Part 3: Phase 1a, Check a Folder

Back to [Part 1](17-easy-use-part1.md) · Phase 0: [Part 2](17-easy-use-part2.md) · Phase 1b:
[Part 4](17-easy-use-part4.md) · index: [00-overall-plan.md](00-overall-plan.md)

Phase 1 makes AeroPatch work on any folder from the command line, in two steps:
- **1a, check** (this part; ~3 days, a third of it writing cards): read-only. It needs nothing from Phase 0, so it can start beside it.
- **1b, fix, apply and undo** ([Part 4](17-easy-use-part4.md); ~5 days): needs Phase 0's labels and loop
  changes.

## 1. Commands

| Command | Needs | Writes into the user's folder |
|---|---|---|
| `aeropatch check <folder> [--open]` | Only the scanners: no Docker, no Ollama | Nothing; `--open` writes `report.html` in the run folder and opens it |
| `aeropatch fix <folder> <n>` (1b) | Ollama. Docker is optional: without it the change is not run (`suggest-local`, best label "Scanner quiet, not tested") | Nothing; works on a scratch copy |
| `aeropatch apply <folder> <n>` (1b) | A finished `fix` | The changed file, after a backup to `.aeropatch/backup/<timestamp>/` |
| `aeropatch undo <folder>` (1b) | An earlier `apply` | Restores the backup |
| `aeropatch dismiss <folder> <n> --reason "…"` | — | `.aeropatch/dismissed.json` |

Results live under `runs/folders/<name>-<hash8>/`, not in the folder. `check` gives value before
Docker is even installed, so it is the first thing a new user runs. If the folder is a git repository,
`apply` says once that `.aeropatch/` can go into `.gitignore`; it never edits `.gitignore` itself.

`check` prints one card per finding, at most five, then a line like "3 more parked (likely not a
problem): show with --all". Each card shows its number, headline, file and line, and the label once
`fix` has run.

**The HTML page** renders the same cards from a string template in the standard library. `fix`
re-renders it with the label, the checked and unchecked lists, and the diff.
- It is the first thing a non-technical person can read without a terminal.
- It is the material for the review test ([Part 4 §5](17-easy-use-part4.md#5-exit-criteria-all-must-hold)).
- Phase 2's page reuses it.

`aeropatch prune --folders` deletes the run folders, which hold copies of the user's code.

## 2. Triage and cards

Deterministic, in this order:

1. Scan with Opengrep and Bandit (`scanners.scan`, unchanged).
2. Park findings in test code (`tests/**`, `test_*.py`, `*_test.py`, `conftest.py`) and in
   virtual-environment and build folders (the staging list in [Part 4 §2](17-easy-use-part4.md#2-the-folder-sandbox-image)).
3. Merge findings on the same file within 3 lines across both tools; keep the Opengrep one.
4. Park Bandit findings with LOW confidence or LOW severity. Bandit's precision was 11% on one 2026
   Python dataset.
5. Hide dismissed fingerprints and show the reason. The fingerprint includes the code snippet, so a
   dismissal lapses when that code changes.
6. Rank by severity, then by the size of the enclosing function, then put first the CWE classes the
   local model fixed in every run. Small patches succeed far more often: in PatchEval, 32.5% for
   1-5 lines against 7.7% for 20 or more.
7. Show the top five; the rest are one `--all` away, never deleted.

**Cards are fixed templates**, one per rule, in `rules/cards.json`:
- a headline in the user's terms ("someone could read any file on this computer through your upload page");
- what could happen;
- when it matters ("only if the app is reachable from the internet");
- what the suggested change does;
- two or three things to try by hand.

The rule ID, CWE, diff and logs sit behind "details". Write the cards for the 22 project rules and the
15 most common Bandit tests first. An unknown rule gets a generic card that says so. A 4B model never
writes a risk claim.

For classes the local model often missed on test (path traversal, SSRF;
[per-CWE table](results/test/07-resolved-per-cwe.csv)), the card says so and, from Phase 3, offers
"Ask Claude". The fix is still attempted: the untuned model fixed the held-out path-traversal and
weak-hashing scenarios (C-022-01, C-328-01) in both Tier C runs.

## 3. Secrets card (no model call)

Triggered by Bandit B105/B106/B107, or by `check_no_secrets` firing on the snippet
([prompts.py:83](../src/aeropatch/agent/prompts.py#L83)). Bandit's password checks often fire on
harmless strings, so the card starts with "If this is a real password or key". It names the file and
line, never the value, and gives two steps:
1. **Change the key at the provider first.** Editing the code does not undo an exposure.
2. Move the value into an environment variable, using the card's two-line Python example.

The same redaction applies to everything written to disk. `prompt.txt` is saved per attempt
([loop.py:111](../src/aeropatch/agent/loop.py#L111)), and the HTML page shows code.

## 4. Exit criteria for 1a (all must hold)

1. **Triage keeps the real finding.** The scenario's finding is in the top five for at least 25 of 27
   test scenarios. Tier A repos are small, so this is a sanity check, not evidence.
2. **Real projects, detection.** On 10 small public repos at pinned commits, with licences checked,
   at least 50% of the shown findings are real.
   - You and I label them separately against the rule's CWE definition, and disagreements are listed.
   - Include deliberately vulnerable apps for ground truth. Candidates to check: OWASP PyGoat, vulpy,
     and DVPWA (which needs PostgreSQL).
   - Include ordinary small Flask, FastAPI and CLI projects as well.
   - These repos are likely in model training data, so they measure detection and setup, not fix rate.
3. **No writes.** `check` leaves the folder byte-identical, checked by hashing it before and after.
4. **Works without Docker or Ollama.** Check passes with both stopped.
