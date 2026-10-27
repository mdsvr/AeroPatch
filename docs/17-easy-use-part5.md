# 17 — Easy Use for Non-Experts, Part 5: Phases 2 and 3

Back to [Part 1](17-easy-use-part1.md) · Phase 1: [Part 3](17-easy-use-part3.md) and
[Part 4](17-easy-use-part4.md) · index: [00-overall-plan.md](00-overall-plan.md)

## 1. Phase 2: no terminal needed (~4 days)

The user pastes one line into PowerShell, waits, and gets a desktop shortcut that opens a local page.
Everything the page does is a Phase 1 command underneath.

### 1a. `install.ps1`

Served from a release tag: `irm https://raw.githubusercontent.com/mdsvr/AeroPatch/<tag>/install.ps1 | iex`.
It installs in the order of the three levels (Part 1 §1). After each level it asks whether to go on;
the default is Suggest. Each step is skipped if already done, so after a restart the user runs the
same line again.

| Step | How | Note |
|---|---|---|
| **Check level** | | No admin, about 2 minutes |
| 1. uv | `irm https://astral.sh/uv/<pinned version>/install.ps1 \| iex` | Per user |
| 2. AeroPatch | Download the release zip with `Invoke-WebRequest`, `Expand-Archive` to `-InstallDir` (default `%LOCALAPPDATA%\AeroPatch\<tag>`), then `uv sync --frozen` | No `uv tool install`: `ROOT = parents[2]` and the wheel would lose `rules/` and `docker/` ([config.py:13](../src/aeropatch/config.py#L13)) |
| 3. Opengrep | Download the pinned Windows release asset; check its SHA-256, as CI does for the Linux one ([ci.yml](../.github/workflows/ci.yml)) | Without it, the scan is Bandit alone |
| **Suggest level** | | No admin; about 3 GB to download |
| 4. Ollama, pinned | `$env:OLLAMA_VERSION='<pinned>'; irm https://ollama.com/install.ps1 \| iex` | Per user; the script checks the installer's signature. Ollama shipped four releases from 14 to 21 October 2026, so the pin matters |
| 5. Model | `ollama pull <the model Phase 0 measured>` | Decision 3 in Part 1 §6 |
| **Test level** | | Admin; sometimes a restart |
| 6. Can this PC run Docker? | Windows 11 23H2 (build 22631) or later; 8 GB RAM; virtualization on in the firmware | The firmware switch is the one step software cannot do. Explain it and stop; the lower levels keep working |
| 7. Docker Desktop | Show its licence terms (free for personal use and businesses under 250 employees and $10M revenue) and ask yes or no; then `winget install -e --id Docker.DockerDesktop` | The winget package always passes `--accept-license`, so asking first is required. One UAC prompt, and `wsl --install` plus a restart the first time |
| **Always** | | |
| 8. Shortcut | Desktop shortcut "AeroPatch" → `uv run --directory <dir> aeropatch ui` | |
| 9. Doctor | `aeropatch doctor`, printed at the end | Shows which levels are ready, or the one thing left to do |

On the project laptop itself, pass `-InstallDir F:\…`, since files go on `F:` there, never `C:`.
No `.exe` of AeroPatch's own: unsigned apps get a strong SmartScreen block, and signing for individuals
is US/Canada only (SignPath Foundation is the free route if it is ever needed).

### 1b. `aeropatch ui`

- **Server:** stdlib `http.server.ThreadingHTTPServer`, zero new packages (Gradio would add 54, FastAPI
  with uvicorn 14). Bound to `127.0.0.1` on a free port, opened with `webbrowser.open`.
- **Security:** its buttons write files, so every request needs a per-launch token
  (`secrets.token_urlsafe`) and a `Host` header of `127.0.0.1:<port>`. Otherwise, any web page the
  user visits could drive it (CSRF, DNS rebinding).
- **One page** in `src/aeropatch/ui.html`: inline CSS and JS, no CDN, so it works offline.
- **Folder choice:** a "Choose folder" button opens a native dialog on the server side with stdlib
  `tkinter.filedialog`. First check that uv's Python includes tkinter; if not, the user pastes a path.
- **Endpoints:**
  - `GET /api/doctor`
  - `POST /api/check`
  - `POST /api/fix`, which returns a job ID; `GET /api/job/<id>` is polled every 2 seconds, since a fix
    takes from seconds to minutes
  - `POST /api/apply`, `/api/undo`, `/api/dismiss`

**What the page shows:**
- a doctor strip at the top, in words as well as colour;
- **live progress while a fix runs.** A fix takes from seconds to minutes, so the card shows each step
  as it happens: "Scanning" → "Writing a fix (try 1 of 3)" → "Testing with your tests" (or "Not run:
  no Docker") → the result. The steps come from the loop's attempt records, polled through
  `GET /api/job/<id>`, and the page needs no new packages for this;
- the Phase 1 cards;
- for each card:
  - the label with "checked" and "not checked" written out;
  - the diff, with the two or three lines that carry the security change highlighted;
  - one cheap question ("does your app need to open files outside this folder?");
  - Apply, Skip and Undo;
  - two or three "try this yourself" checks.

Keyboard use and visible labels are basic requirements.

### 1c. Exit criteria (all must hold)

1. A fresh Windows 11 Home machine gets to an all-green doctor from the one line, with only the
   firmware step done by hand. Record the time. A new local Windows account is a cheap stand-in for
   the per-user parts. Docker is machine-wide, so it needs a machine without it.
2. **Install test:** at least 2 of 3 participants reach green unaided, on their own laptops, at the
   level their machine allows. Record each one's RAM, GPU and level, which turns Part 1 §1's machine
   guidance from estimates into measurements. This test is kept apart from the review test, so a failed
   Docker install cannot spoil that session.
3. **Page test, 6 people:** Phase 1's reliance bars still hold through the page, all 6 can undo an
   applied fix, and the mean System Usability Scale score is at least 68, the average across about 500
   products.

## 2. Phase 3: stronger labels and opt-in help (~5 days)

### 2a. Attack tests written before the fix

For the 16 CWEs in Tier A, write one pytest template per CWE with slots: the import path, the call,
and where the payload goes. The local model fills the slots; it does not write the test from scratch.
Write and tune the templates on the dev split only, as the project has done with every prompt. The
test split's PoCs must not be seen until the measurement below.
The filled test is accepted only if all of these hold:

1. It was written and frozen **before any edit**.
2. Run on the original code in the sandbox, it **fails with an assertion**, not an ImportError,
   NameError or TypeError (classified from the JUnit kind and message).
3. It is baked into the folder image's existing PoC slot (`/opt/scenario/tests_poc`), which keeps it
   read-only to the candidate.

The loop then runs with the PoC visible, as on the benchmark, where that feedback was worth 18 points.
That is a third product config, `fix-local-witness`: `fix-local` with `hidden_suites: []`.

**Measure before shipping.** On the 27 test scenarios, hide the human PoC and generate a witness test
instead. Publish:
- how many scenarios get an accepted witness;
- the precision of "Attack test now blocked" against the hidden human PoC.

The label ships only if its precision beats the point estimate of "Scanner quiet, your tests still pass"
from V1.

**Risks.** A test that fails for an unrelated reason looks like a real attack test. In one study, about
44% of an agent's "this test exposes a bug" claims were wrong. Criteria 1 and 2 are the guard, and the
repair step must never see or edit the test.

### 2b. "Ask Claude" on one finding

- A per-card button. It first shows the exact text that would be sent: the prompt after `redact` and
  `check_no_secrets` ([prompts.py:83-100](../src/aeropatch/agent/prompts.py#L83-L100)).
- It says plainly that the request uses the user's own Claude Code subscription. After local attempts,
  it also says the whole attempt history is sent, which is why the cascade saved almost nothing on the
  real CVEs.
- A config `fix-claude`, built like `fix-local` but on the existing `claude-code` route. Never
  `baseline-frontier`, the paid API-key route.
- The doctor checks the Claude Code CLI version: Opus 5.5 needs 2.1.296 or later.
- It is the route the cards offer for classes the local model often missed on test (path traversal,
  SSRF).
- If it is wanted sooner, it can ship in Phase 1 as `fix --claude`, which prints the outgoing text and
  asks yes or no in the terminal.

### 2c. Exit criteria (all must hold)

1. The witness build share and label-1 precision are published; label 1 is shipped only under the rule
   in 2a.
2. The cascade's and Claude's resolve rates under V1 conditions are published beside the 100% and 90%
   they earned with PoC feedback.
3. The adversarial split still blocks the credential before sending, and lets 0 of 4 injections through.

## 3. Definition of done for the whole plan

- A non-expert can install, check a folder, read five cards, apply or skip one fix, and undo it,
  without opening a terminal after the install line.
- A user who cannot install Docker still gets the Check and Suggest levels, with labels that say so.
- Every label in the interface carries a measured "N of M" from AeroPatch's own benchmark.
- The README states the honest rates: V1's resolve rate for "you have tests", V2's for "you have none",
  and how many real advisories the scanners found.
- Nothing leaves the laptop without a per-finding preview and a click.
- The checks written in each phase pass in CI: labels, doctor faults, undo integrity, hidden-suite leak.

## 4. Recommended first step

1. Make Phase 0's loop changes 1-11 (Part 2 §2), about a day, with their tests.
2. Stop and ask before the runs. They take about 2 hours on the laptop, and their numbers decide
   whether Phase 1b ships as a fixer or as an explainer that offers suggestions.
3. In parallel, build the doctor (change 12) and Phase 1a's `check`. Neither needs a run, and together
   they give a non-expert something useful before any fix exists.
