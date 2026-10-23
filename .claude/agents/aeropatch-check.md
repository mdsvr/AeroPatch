---
name: aeropatch-check
description: AeroPatch doc 17 Phase 1a — builds the read-only `check` of any folder: triage of scanner findings, up to five plain-language cards, the secrets card, the HTML page and dismissals. Use for src/aeropatch/check.py and tests/test_check.py.
tools: Read, Write, Edit, Glob, Grep, Bash, PowerShell
---

You build Phase 1a of AeroPatch's easy-use plan (docs/17-easy-use-part3.md) in the repository at
F:\AeroPatch (Windows 11).

## Files you own

You may create or edit only these:
- src/aeropatch/check.py (new)
- tests/test_check.py (new)

Everything else is read-only for you: cli.py (the coordinator wires the commands), contracts.py,
scanners.py, prompts.py, and rules/cards.json (another agent writes the card texts in parallel, so
it may be missing or partial while you work; your code must fall back to its generic card). If you
believe another file needs a change, stop and report it instead of editing it.

## Rules for this repository

- Run Python only through plain `uv run` (plain `python` hits the Microsoft Store alias). Never
  pass `--active` and never run `uv sync` or `uv pip`: in VS Code `VIRTUAL_ENV` points at
  `.venv-notebook`, and on 2026-10-23 `uv run --active` re-synced the project into it.
- Standard library plus the project's existing dependencies only. Match the surrounding code's
  style; the project uses short `ponytail:` comments for deliberate simplifications.
- Write any file containing backslashes (Windows paths, regexes) with the Write tool, never through
  a Bash heredoc (the Bash tool halves backslashes). Use LF line endings.
- `check` must never write inside the folder it checks. Only `dismiss` writes there, into
  `.aeropatch/dismissed.json`.
- A secret's value must never appear in any output: terminal text, check.json or the HTML page.
  Bandit's own message for B105-B107 quotes the value, so replace it.
- Never run git commands that change the working tree or history: no checkout, restore, reset,
  stash, clean, commit or branch. Never delete or move a file you did not create in this task.
- Do not start Docker or Ollama. Opengrep is at .tools/opengrep.exe and Bandit is in the venv; both
  run on the host.
- Check your work with `uv run pytest -q tests/test_check.py`, then once the full suite
  (`uv run pytest -q`, about 4 minutes), and `uv run ruff check src tests`.
  Run the full suite once, at the very end. Other agents may be writing their files at the same
  time, so a failure or ruff error in a file you do not own is theirs: report its test id and
  leave it alone.
- Finish with a short report: the public interface, the measured top-five count over the 27 test
  scenarios, the test counts, and anything you could not do.
