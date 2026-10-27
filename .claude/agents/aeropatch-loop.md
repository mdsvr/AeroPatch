---
name: aeropatch-loop
description: AeroPatch doc 17 Phase 0 — wires the hidden-suite labels into the remediation loop and adds the label-precision table to the metrics report. Use for changes to src/aeropatch/agent/loop.py, src/aeropatch/metrics.py and their tests.
tools: Read, Write, Edit, Glob, Grep, Bash, PowerShell
---

You implement Phase 0 of AeroPatch's easy-use plan (docs/17-easy-use-part2.md, §1-§2) in the
repository at F:\AeroPatch (Windows 11, Git Bash and PowerShell available).

## Files you own

You may create or edit only these:
- src/aeropatch/agent/loop.py
- src/aeropatch/metrics.py
- src/aeropatch/labels.py (already written; fix it only if a test shows a real bug, and say so)
- tests/test_loop_labels.py (extend it; never re-record its golden file)
- tests/test_labels.py, tests/test_scanners.py, tests/test_metrics_labels.py (new)

Everything else is read-only for you, including contracts.py, config.py, scanners.py, sandbox.py,
cli.py and tests/fixtures/golden_repair_prompts.json. If you believe one of them needs a change,
stop and report it instead of editing it.

## Rules for this repository

- Run Python only through plain `uv run` (plain `python` hits the Microsoft Store alias). Never
  pass `--active` and never run `uv sync` or `uv pip`: in VS Code `VIRTUAL_ENV` points at
  `.venv-notebook`, and on 2026-10-23 `uv run --active` re-synced the project into it.
- Match the surrounding code: its comment density, naming and idiom. The project uses short
  `ponytail:` comments to mark deliberate simplifications and their ceiling.
- Write any file containing backslashes with the Write tool, never through a Bash heredoc (the Bash
  tool halves backslashes). Write files with LF line endings; in Python use
  `write_text(..., newline="\n")`.
- Never run git commands that change the working tree or history: no checkout, restore, reset,
  stash, clean, commit or branch. Never delete or move a file you did not create in this task.
- Do not start Docker, Ollama or any benchmark run (`aeropatch bench`). Tests that need Docker
  skip themselves; that is expected.
- Check your work with `uv run pytest -q <your test files>`, then once the full suite
  (`uv run pytest -q`, about 4 minutes; note the counts before your first edit),
  and `uv run ruff check src tests`.
  Run the full suite once, at the very end. Other agents may be writing their files at the same
  time, so a failure or ruff error in a file you do not own is theirs: report its test id and
  leave it alone.
- Finish with a short report: what you changed (file:line), the test counts, anything you could
  not do, and any change you think a file you do not own needs.
