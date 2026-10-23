# Installing, packaging and presenting AeroPatch for non-technical Windows users (state as of 2026-10-22)

Scope note: these are research notes for a report writer. "Measured" means the researcher ran the command on the AeroPatch laptop (Windows 11 Home, build 26300, winget v1.29.290) on 2026-10-22. Everything else is cited inline. Older information is dated.

## 1. Installing the prerequisites on Windows 11 with the least friction (Docker Desktop, WSL2, Ollama, uv, alternatives)

### Takeaway
All three prerequisites install through winget: `Docker.DockerDesktop`, `Ollama.Ollama` and `astral-sh.uv`. Only Docker needs admin rights and a possible restart, because it depends on WSL2 and on virtualization being enabled in the BIOS. Docker Desktop stays free for personal use and for businesses under 250 employees and $10M revenue. Podman Desktop and Rancher Desktop are free and also on winget, but both still need WSL2/virtualization, so neither removes the main source of friction.

### Cited Findings
**winget IDs and current versions (measured 2026-10-22, `winget show --id <ID> -e`):**
- `Docker.DockerDesktop` 4.96.1, released 2026-10-21, proprietary licence.
- `Ollama.Ollama` 0.40.8, released 2026-10-21, MIT licence.
- `astral-sh.uv` 0.13.5.
- `RedHat.Podman-Desktop` 1.30.5.
- `SUSE.RancherDesktop` 1.24.0.
- `Anthropic.Claude` (Claude Desktop) 2.42304.2.

**What winget actually runs for Docker** ([winget-pkgs manifest 4.96.1](https://github.com/microsoft/winget-pkgs/blob/master/manifests/d/Docker/DockerDesktop/4.96.1/Docker.DockerDesktop.installer.yaml), read 2026-10-22):
- `InstallerType: exe`, `Scope: machine`, `ElevationRequirement: elevatesSelf`.
- Silent switch: `install --quiet`.
- Custom switches always added: `--accept-license --backend=wsl-2 --no-windows-containers`.
- So `winget install -e --id Docker.DockerDesktop --silent` does an all-users install, shows a UAC prompt, and accepts the licence for the user.

**What winget actually runs for Ollama** ([winget-pkgs manifest 0.40.8](https://github.com/microsoft/winget-pkgs/blob/master/manifests/o/Ollama/Ollama/0.40.8/Ollama.Ollama.installer.yaml)):
- `InstallerType: inno`, `Scope: user`.
- Default location `%LocalAppData%\Programs\Ollama`.
- Installer URL `https://github.com/ollama/ollama/releases/download/v0.40.8/OllamaSetup.exe`.

**Docker Desktop on Windows 11 (WSL2 backend)** ([Docker docs, install on Windows](https://docs.docker.com/desktop/setup/install/windows-install/); the page shows no date):
- **Requirements:**
  - WSL 2.1.5 or later (2.6+ for Enhanced Container Isolation).
  - Windows 11 version 23H2 (build 22631) or later.
  - The LanmanServer service enabled and set to Automatic.
  - The WSL 2 feature turned on.
  - A 64-bit CPU with SLAT, 8 GB RAM, and hardware virtualization enabled in BIOS/UEFI.
- **Editions (inconsistent extraction):**
  - The requirements list came back as "Enterprise, Pro, or Education".
  - The same page says "Home and Education editions only run Linux containers", which implies Home is supported for WSL2 Linux containers.
  - The target user, and this laptop, run Windows 11 Home, so check the page directly.
- **Install commands:**
  - Per-user, no admin: `"Docker Desktop Installer.exe" install --user`.
  - All-users, admin: `"Docker Desktop Installer.exe" install`.
  - PowerShell form: `Start-Process 'Docker Desktop Installer.exe' -Wait -ArgumentList 'install', '--user'`.
  - Flags: `--quiet`, `--accept-license`, `--backend=<wsl-2|hyper-v|windows|docker-vmm>`, `--always-run-service` (sets `com.docker.service` to Automatic so later actions need no elevation), `--installation-dir`.
- **Admin rights and restart:**
  - "Enabling WSL 2 for the first time needs admin rights once per machine."
  - The page does not say Docker itself needs a restart, but notes that `wsl --install` may ask for one.
  - "Docker Desktop does not start automatically after installation."
- **docker-users group:** Linux containers on WSL 2 don't need it. Membership "is equivalent to administrative privileges on the host".
- **Licence:**
  - Free for personal use, education, non-commercial open source, and small businesses with fewer than 250 employees and less than $10 million annual revenue.
  - Larger organisations and government entities need a paid subscription.

**WSL2** ([Microsoft Learn, Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install); ms.date 2025-06-09, updated 2026-06-02):
- Run `wsl --install` in an administrator PowerShell, then restart.
- Requires Windows 10 2004 (build 19041) or later, or Windows 11.
- The command only works if WSL is not installed at all.
- If the install hangs at 0.0%, use `wsl --install --web-download -d <Distro>`.
- Check versions with `wsl.exe --list --verbose`.

**Ollama on Windows** ([docs.ollama.com/windows](https://docs.ollama.com/windows)):
- **Requirements:** Windows 10 22H2 or newer (Home or Pro). The installer needs no admin rights and installs to the home directory.
- **Disk:** binaries need at least 4 GB; models take "tens to hundreds of GB".
- **Installer flag:** `OllamaSetup.exe /DIR="d:\some\location"` is the only documented flag.
- **Model location:** set the `OLLAMA_MODELS` user environment variable, then restart the tray app.
- **Standalone option:** `ollama-windows-amd64.zip` (CLI plus NVIDIA libraries), with `-rocm` and `-mlx` add-on zips. To run it as a service, use `ollama serve` with a tool such as NSSM.
- **Silent install flags (third party, not in Ollama's docs):** [Silent Install HQ](https://app.silentinstallhq.com/installer/0fd108b6b99488c4ff7cc06bf941265eb1fa77f6a4fad90ed079fde0229af068) lists `OllamaSetup.exe /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`. Ollama's own install script, below, confirms the core flags.

**Ollama's official PowerShell install script** (`https://ollama.com/install.ps1`, which redirects to the `install.ps1` asset of the latest GitHub release; read, not executed, on 2026-10-22; the asset was last modified 2026-10-21; [releases](https://github.com/ollama/ollama/releases)):
- **Quick install:** `irm https://ollama.com/install.ps1 | iex`.
- **Pinned version:** `$env:OLLAMA_VERSION="0.5.7"; irm https://ollama.com/install.ps1 | iex`.
- **Custom directory:** `$env:OLLAMA_INSTALL_DIR="D:\Ollama"; irm https://ollama.com/install.ps1 | iex`.
- **Uninstall:** `$env:OLLAMA_UNINSTALL=1; irm ... | iex`.
- **What it runs:** it downloads `OllamaSetup.exe` and runs it with `/VERYSILENT /NORESTART /SUPPRESSMSGBOXES`, plus `/DIR="..."` when a directory is set.
- **Signature check:** the script checks the installer's Authenticode signature (`Get-AuthenticodeSignature`) before running it.

**uv** ([docs.astral.sh/uv installation](https://docs.astral.sh/uv/getting-started/installation/)):
- Install: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
- Pinned version: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.13.5/install.ps1 | iex"`.
- Inspect the script first: `powershell -c "irm https://astral.sh/uv/install.ps1 | more"`.
- winget: `winget install --id=astral-sh.uv -e`.
- Update: `uv self update`, which only works for standalone-installer installs.
- `UV_NO_MODIFY_PATH=1` stops the installer from changing shell profiles.

**Alternatives to Docker Desktop:**
- **Podman Desktop requirements:** uses WSL2 or Hyper-V for its Linux VM. Needs Windows 10 2004+ or Windows 11, at least 4 GB RAM (8 GB recommended) and 2 GB free disk; it is on winget ([OneUptime guide, 2026-03-18](https://oneuptime.com/blog/post/2026-03-18-install-podman-desktop-windows/view)).
- **Podman compatibility:** `alias docker=podman` makes "most existing scripts" work. podman-compose is "good but not identical" ([Codersera, 2026](https://codersera.com/blog/podman-vs-docker-2026/); [Kunal Ganglani, 2026](https://www.kunalganglani.com/blog/docker-vs-podman-2026)).
- **Polish:** one 2026 comparison says Docker Desktop "still feels smoother" on Windows, and that Podman Machine is less seamless than Docker's WSL2 integration ([Codersera](https://codersera.com/blog/podman-vs-docker-2026/); [DataCamp](https://www.datacamp.com/zh/blog/docker-alternatives), a general guide).
- **Docker Engine inside a WSL2 distro** is listed as another option ([env.dev guide](https://env.dev/guides/docker-on-windows)).

**macOS and Linux differences, briefly:**
- **Ollama updates:** macOS auto-downloads updates the same way as Windows ([Ollama FAQ](https://docs.ollama.com/faq), via search summary). Linux uses a manual update path ([OpenVeil, 2026-08-03](https://openveil.app/blog/ollama-disable-automatic-updates-version-check)).
- **Claude Desktop config on macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`, with logs in `~/Library/Logs/Claude` ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/develop/connect-local-servers)).
- **Claude Desktop on Linux (conflict):** the MCPB doc says Claude Desktop runs on macOS and Windows only, while modelcontextprotocol.io says it also runs on Linux (see section 5).
- **Docker licence:** the same thresholds apply on macOS ([Docker docs](https://docs.docker.com/desktop/setup/install/windows-install/)).

### Inferences
- **Lowest-friction order:**
  1. uv: no admin.
  2. Ollama: no admin, user scope.
  3. Docker Desktop: one UAC prompt, plus a possible restart if WSL2 is missing.
- **The real friction point:** the one step a non-technical user can't do alone is turning on virtualization in the BIOS when it is off. Every container option needs it, so the installer should detect it and explain it, not try to automate it.
- **Install scope:** winget's Docker package forces an all-users install with `--accept-license`. A bootstrap script that wants a per-user, no-admin install should download `Docker Desktop Installer.exe` and run `install --user --accept-license --backend=wsl-2` itself. Even then, enabling WSL2 the first time needs admin.
- **Inno flags:** winget's `--silent` for `Ollama.Ollama` probably maps to Inno Setup's standard silent switches, since `InstallerType: inno`. This is not verified against the manifest, which lists no explicit `InstallerSwitches`.
- **Ollama without winget:** Ollama's own `install.ps1` is the no-winget path, and its `OLLAMA_VERSION` variable lets a bootstrap script install a pinned, known-good version (see section 4).
- **Licence consent:** winget's Docker package always passes `--accept-license`. A bootstrap script that uses it accepts Docker's subscription terms on the user's behalf, including the paid threshold for their employer. The script should show the terms (free under 250 employees and $10M revenue) and get an explicit yes first.
- **Recommended container runtime:** keep Docker Desktop as the default. Document Podman Desktop only as a fallback for users at organisations over Docker's licence threshold. It removes no install step and adds a risk that the Docker API used by the sandbox behaves differently.

### Gaps
- **Rancher Desktop:** no Windows requirements or Docker-compatibility details were retrieved beyond its winget ID and version.
- **macOS and Linux containers:** Docker Desktop requirements on macOS, and native Docker Engine on Linux (no WSL), were not researched in this pass.
- **Windows 11 Home:** confirm the exact Docker requirement wording for Home on the live Docker page, given the inconsistent extraction.
- **Docker licence:** the licence was read from the install page. The separate subscription-terms page was not fetched.

## 2. Distributing the Python app itself (uv tool / uvx, PyInstaller, Briefcase, Nuitka, MSIX/winget, PowerShell bootstrap, signing, updates)

### Takeaway
The cheapest route that avoids SmartScreen warnings ships no maintainer-built .exe at all. A short `install.ps1`, run with `irm ... | iex` the way uv does, installs uv and then runs `uv tool install git+https://github.com/<owner>/aeropatch@<tag>`. Any frozen .exe (PyInstaller and similar) brings signing costs and SmartScreen and antivirus friction. Azure Artifact Signing (about $9.99/month) is open to individual developers only in the USA and Canada; organisations also qualify in the EU and UK. The free options are SignPath Foundation for open-source projects, or publishing an MSIX through the Microsoft Store, which Microsoft re-signs.

### Cited Findings
**uv tool commands** ([docs.astral.sh/uv guides/tools](https://docs.astral.sh/uv/guides/tools/)):
- Install from PyPI: `uv tool install ruff`.
- Install from git: `uv tool install git+https://github.com/httpie/cli`.
- Run without installing: `uvx --from git+https://github.com/httpie/cli httpie`, pinning a branch or commit with `@<ref>`.
- Upgrade: `uv tool upgrade <tool>` and `uv tool upgrade --all`. Upgrades respect the original version constraints.
- PATH: if the tool `bin` directory is not on PATH, uv warns, and `uv tool update-shell` adds it.
- Choose an interpreter with `--python 3.10`. The guide page does not say whether uv downloads Python itself.

**Code signing for apps distributed outside the Store** ([Microsoft Learn, Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options), ms.date 2026-08-29):

| Option | Cost | SmartScreen behaviour |
|---|---|---|
| Microsoft Store MSIX | Free; Microsoft re-signs the package | No warnings |
| Azure Artifact Signing (formerly Trusted Signing) | About $9.99/month | Reputation builds over time; initial warnings expected |
| OV certificate | $150–300/year; private key on an HSM or hardware token since June 2023 | Same as Artifact Signing |
| EV certificate | $400+/year | Same as OV since 2024; no longer an instant bypass |
| Self-signed | Free | "Blocks installation for public users" |
| Unsigned | Free | "Strong SmartScreen block; enterprises may block entirely" |

- **Artifact Signing eligibility:** organisations in the USA, Canada, EU and UK; individuals in the USA and Canada only.
- **Open source:** "SignPath Foundation offers free code signing for qualifying open-source projects", at OV level through a managed pipeline.
- **Possible pause:** one May 2026 indie comparison says individual onboarding to Artifact Signing was "paused (March 2026)". This is unconfirmed by Microsoft ([gabrielmoraru.com](https://gabrielmoraru.com/obtaining-cheap-ev-ov-certificates-singing-your-application/), via search summary).

**PyInstaller false positives** (community reports, anecdotal):
- Defender tends to distrust onefile builds because "malware is sometimes packaged the same way" ([itch.io post](https://itch.io/post/9429945)).
- Detections are often machine-learning heuristics (an `!ml` suffix) ([microsoft/apm #487](https://github.com/microsoft/apm/issues/487)).
- Reported mitigations: code signing, PE version metadata, avoiding UPX, onedir builds instead of onefile, and submitting false-positive reports to Microsoft ([vba-edit #24](https://github.com/markuskiller/vba-edit/issues/24); [Python Discourse](https://discuss.python.org/t/pyinstaller-false-positive/43171)).
- Detections can return after Defender updates ([Open Stage Control forum](https://openstagecontrol.discourse.group/t/windows-deffender-flagged-osc-midi-windows-exe-as-trojan-horse/1437)).

**winget manifests as a model:** the Ollama manifest is a small YAML file pointing at a GitHub release asset, with `Scope: user` and `Commands: [ollama]` ([winget-pkgs manifest 0.40.8](https://github.com/microsoft/winget-pkgs/blob/master/manifests/o/Ollama/Ollama/0.40.8/Ollama.Ollama.installer.yaml)).

### Inferences
- **Shape of a bootstrap `install.ps1`, about 40 lines of PowerShell with no Python dependencies:**
  1. Check for uv and install it via the astral script or winget if missing.
  2. `uv tool install git+https://github.com/<owner>/aeropatch@vX.Y`.
  3. `winget install -e --id Ollama.Ollama`, then the Docker step.
  4. `ollama pull <model>`.
  5. `aeropatch doctor`.
- **Updates:** become `uv tool upgrade aeropatch`, or re-running the script.
- **SmartScreen:** a script piped into `iex` is never saved as a downloaded file, so it should not go through SmartScreen's file-reputation check. This is inferred from how Mark-of-the-Web works and was not verified in this pass. Antivirus or AMSI can still inspect it.
- **Trust:** offer an "inspect first" command (`irm .../install.ps1 | more`) the way uv does.
- **Frozen .exe:** a PyInstaller, Nuitka or Briefcase .exe only makes sense once signing is arranged. For a maintainer outside the USA and Canada, that means SignPath Foundation (free, OSS) or the Microsoft Store as MSIX (free re-signing). Without signing, a non-technical user hits "Windows protected your PC" on the first run.
- **Bundling doesn't remove prerequisites:** Docker Desktop and Ollama still have to be installed separately, so a frozen .exe saves only the uv step.
- **Is winget worth it for AeroPatch?** A winget manifest needs a stable installer URL. Without a built installer it adds little over the script. It becomes worthwhile once a signed MSIX or zip exists.

### Gaps
- Not researched in this pass, so no cited facts: Briefcase (MSI output, signing support), Nuitka (compile times, AV behaviour), and MSIX packaging of a Python app.
- winget support for `portable`/`zip` installer types, as a way to publish an unsigned zip, was not verified.
- Whether `uv tool install` downloads a managed Python automatically when none is installed was not confirmed. The guide page was silent; the Python-versions concept page was not fetched.
- No primary data was found on how often SmartScreen or AMSI flags `irm | iex` installers.

## 3. A "doctor" / preflight check: what to check and how to present fixes

### Takeaway
Model it on `flutter doctor`: one line per area with a pass or fail mark, a plain-language fix under each failure, `-v` for detail, and a final "No issues found!". The checks AeroPatch needs map directly onto documented requirements and failure modes:
- WSL ≥ 2.1.5 and virtualization on.
- Docker engine running.
- Ollama reachable at `localhost:11434`, which the tray app sometimes fails to start.
- The model pulled.
- Disk space.
- GPU and VRAM.
- A pending Ollama update.

### Cited Findings
- **The `flutter doctor` pattern:**
  - It "checks a machine's Flutter setup and reports what is missing, with recommendations for resolving it".
  - The output is a per-area checklist (Flutter, Android toolchain, Xcode, Chrome, Android Studio, VS Code, devices) that ends with "No issues found!".
  - Verbose mode "prints extensive information about the nature of an issue and shares how to fix it" ([Codecademy, Flutter Doctor](https://www.codecademy.com/article/check-your-flutter-installation-with-flutter-doctor)).
- **Docker prerequisites a doctor can check** ([Docker docs](https://docs.docker.com/desktop/setup/install/windows-install/)): WSL ≥ 2.1.5, LanmanServer service Automatic, WSL 2 feature on, SLAT and virtualization enabled in BIOS, 8 GB RAM, and Windows 11 build ≥ 22631. Docker Desktop "does not start automatically after installation".
- **WSL state:** `wsl.exe --list --verbose`. Fresh installs need `wsl --install` from an admin prompt plus a restart ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/wsl/install)).
- **Ollama endpoints and logs** ([docs.ollama.com/windows](https://docs.ollama.com/windows)):
  - The API is at `http://localhost:11434`.
  - Logs are in `%LOCALAPPDATA%\Ollama`: `app.log` (GUI), `server.log`, and `upgrade.log` (upgrade output). Downloaded updates are stored there too.
  - Models and config live in `%HOMEPATH%\.ollama`, or in `OLLAMA_MODELS`.
- **A documented failure mode to detect:** [ollama #18507](https://github.com/ollama/ollama/issues/18507) (Windows 11 26200, Ollama 0.34.1, 2026).
  - The tray icon appears, but `curl http://127.0.0.1:11434/api/version` fails.
  - `app.log` shows "existing instance found, exiting" and "ollama server not ready after retries".
  - A manual `ollama serve` works within about 3 seconds.
- **Claude Desktop MCP logs, for a "Claude can't see AeroPatch" check** ([modelcontextprotocol.io, Connect to local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers)):
  - `%APPDATA%\Claude\logs\mcp.log`, plus `mcp-server-SERVERNAME.log` with the server's stderr.
  - Config is at `%APPDATA%\Claude\claude_desktop_config.json`. Paths must be absolute, and Claude Desktop needs a full restart after edits.
- **Disk floor:** Ollama binaries need at least 4 GB; models need "tens to hundreds of GB" ([docs.ollama.com/windows](https://docs.ollama.com/windows)).

### Inferences
- **Stdlib only, no new dependencies:** `subprocess` for `wsl --list --verbose`, `wsl --version` and `docker info` (non-zero exit means the engine is not running), `urllib.request` for `GET /api/version` and `/api/tags` (is the model present?), `shutil.disk_usage`, and `nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader`.
- **Virtualization check:** `(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled` in PowerShell, or `systeminfo`.
- **The nvidia-smi and CIM commands are standard, but were not re-verified in this pass.**
- **Plain-language fix lines, one per check.** Examples:
  - "Docker is installed but not running. Open Docker Desktop from the Start menu and wait for the whale icon to stop animating."
  - "Virtualization is turned off in your PC's firmware. Restart, enter BIOS setup (often F2/Del), enable Intel VT-x/AMD-V (SVM), save."
  - "Ollama's tray icon is running but the server is not answering. Quit Ollama from the tray, then run `ollama serve`."
- **Optional `--fix`:** a `doctor --fix` flag could run the winget commands from section 1 after a yes/no prompt.
- **Update-risk check:** if `upgrade.log` or a staged installer in `%LOCALAPPDATA%\Ollama` exists, warn: "An Ollama update is waiting. Don't click 'Restart to update' during a run."
- **Exit codes:** return 0, 1 or 2 so the MCPB, plugin or web UI can show the same results.

### Gaps
- No source was found on `brew doctor` output style, or on any written design guidance for plain-language fix messages.
- The exact `/api/tags` and `/api/ps` response shapes were not re-fetched; check the current [docs.ollama.com](https://docs.ollama.com) API pages.
- No source was found on reliably detecting "virtualization disabled" versus "Hyper-V or WSL feature missing" from user-mode code on Windows 11 Home.

## 4. Hardware fallback: CPU-only speed, AMD/Intel GPUs, smaller models, pinning Ollama

### Takeaway
- **AMD and Intel GPUs:** Ollama turned Vulkan on by default in 2026 (0.30, per Ollama's blog), so recent AMD and, reportedly, Intel GPUs get acceleration without vendor libraries.
- **CPU only:** a 4B Q4 model is usable but slow. One guide gives 8–12 tok/s on a 4-core machine; the researcher's memory-bandwidth estimate puts a modern DDR5 laptop up to about 15 tok/s. That is a few times slower than the 46 tok/s GPU baseline.
- **Smaller fallback:** `qwen3.5:2b` at Q4_K_M (1.9 GB) is the natural one. No evidence was found on its patch quality.
- **Pinning:** Ollama ships releases every two to three days. The robust pin is the standalone zip run with `ollama serve`, with no tray app. The "Auto-download updates" toggle only stops downloads; the app still checks hourly.

### Cited Findings
**GPU support:**
- **Ollama Windows docs** ([docs.ollama.com/windows](https://docs.ollama.com/windows)):
  - NVIDIA needs driver 551.61 or newer.
  - AMD needs a ROCm v7 / HIP7 stack or a Vulkan-capable Radeon driver.
  - "Vulkan is enabled by default", and is the recommended fallback for some RDNA2 / RX 6000 cards.
  - On mixed iGPU/dGPU systems, set `GGML_VK_VISIBLE_DEVICES` to the discrete GPU.
  - Intel GPUs are not mentioned.
- **Ollama 0.30 blog (secondary):** Ollama's blog said Ollama 0.30 (2026-06-05) made Vulkan the default, "extending Ollama's GPU acceleration to … AMD and Intel devices", with NVIDIA "up to 20% faster" ([Ollama blog](https://registry.ollama.ai/blog/improved-performance-and-model-support-with-gguf), via search summary; the page returned 404 when fetched on 2026-10-22).
- **Older, October 2025:** Vulkan was experimental in 0.12.6-rc0 and source builds only ([Phoronix](https://www.phoronix.com/news/ollama-Experimental-Vulkan)).

**CPU-only speed:**
- "On a 4-core CPU with 16 GB RAM, expect roughly 8-12 tokens per second with the 4B model" (gemma3:4b; undated guide) ([ComputingForGeeks](https://computingforgeeks.com/install-ollama-rocky-ubuntu/)).
- The only laptop-specific CPU figures found came from low-quality mirror sites. One guide that once listed Qwen 3.5 4B CPU figures now says those numbers were removed because they had no protocol or raw data. Its remaining ranges are self-described as unmeasured ([bestllmfor.com, verified 2026-10-14](https://bestllmfor.com/guide/llm-local-cpu-sans-gpu/)). Neither is cited as a figure here.

**Model sizes, Ollama library** ([ollama.com/library/qwen3.5/tags](https://ollama.com/library/qwen3.5/tags), fetched 2026-10-22; every tag has a 256K context and the family is tagged "vision tools thinking"):

| Tag | Size |
|---|---|
| `qwen3.5:0.8b` | 1.0–1.3 GB |
| `qwen3.5:2b-q4_K_M` | 1.9 GB |
| `qwen3.5:2b-q8_0` | 2.7 GB |
| `qwen3.5:4b-q4_K_M` | 3.3 GB |
| `qwen3.5:4b-q8_0` | 5.2 GB |
| `qwen3.5:9b-q4_K_M` | 6.6 GB |

**Release cadence** (measured with `gh api repos/ollama/ollama/releases` on 2026-10-22; [releases page](https://github.com/ollama/ollama/releases)):
- v0.40.5: 2026-10-14
- v0.40.6: 2026-10-16
- v0.40.7: 2026-10-18
- v0.40.8: 2026-10-21
- v0.40.9-rc1: 2026-10-22

**Auto-update behaviour:**
- **FAQ:** Ollama on macOS and Windows "will automatically download updates", applied when the user clicks "Restart to update" in the tray ([Ollama FAQ](https://docs.ollama.com/faq), via search summary of the FAQ and its mirrors).
- **"Auto-download updates" toggle:** PR [ollama #13512](https://github.com/ollama/ollama/issues/13512), merged 2026-02-23, adds it to the app's Settings page.
  - When the toggle is off, the updater "still checks for updates but skips downloading". A download already in progress is cancelled.
  - The setting is stored in the app database (`auto_update_enabled`).
- **Version checks continue:** with the toggle off, the app still checks ollama.com "shortly after startup and about once an hour", and a previously staged package may remain on disk ([OpenVeil, 2026-08-03](https://openveil.app/blog/ollama-disable-automatic-updates-version-check)).
- **Open request:** [ollama #18122](https://github.com/ollama/ollama/issues/18122) asks for fully automatic install, deferred while a model is loaded. It states that installing currently "requires the user to manually click 'Restart to update'".
- **A user workaround:** [ollama #13377](https://github.com/ollama/ollama/issues/13377) advises disabling automatic updates in the tray settings to avoid moving to a broken version.
- **Unofficial claim, contradicted:** one unofficial site says "Ollama has no auto-updater on Windows" ([ai-ollama.github.io](https://ai-ollama.github.io/update.html)). The official FAQ contradicts it.
- **Conflict with the project's own experience:** the brief says the tray app "has auto-updated itself mid-run before". The project's own notes date that to 2026-10-21, the day 0.40.8 shipped. That conflicts with the documented "click to apply" behaviour. One possible cause is a staged update being applied when the app restarted, but this is unverified.
- **Pinnable alternative:** the standalone `ollama-windows-amd64.zip` plus `ollama serve` (optionally as a service via NSSM) runs without the tray app. When upgrading, "remove the old directories first" ([docs.ollama.com/windows](https://docs.ollama.com/windows)).

### Inferences
- **CPU bandwidth estimate (back-of-envelope, not measured):** CPU decoding is limited by memory bandwidth. Tok/s ≈ effective bandwidth ÷ bytes read per token, which is about the model's file size.
  - With a ~2.7–3.3 GB model, dual-channel DDR5-5600 (≈ 90 GB/s theoretical) has a ceiling near 27–33 tok/s; expect roughly half in practice.
  - DDR4-3200 (≈ 51 GB/s) gives a ceiling near 15–19 tok/s.
  - That agrees with the 8–12 tok/s figure above. A full remediation would take several times longer than on the 4 GB GPU.
- **Size discrepancy:** the Ollama library's `qwen3.5:4b-q4_K_M` is 3.3 GB versus the project's 2.7 GB. The project's GGUF is probably a text-only build without the vision projector. This is unverified.
- **Fallback ladder:** NVIDIA CUDA → Vulkan (AMD or Intel) → CPU with the 4B model and a "this will be slow" warning → optional `qwen3.5:2b` (1.9 GB, roughly 1.5–2× faster on CPU by the bandwidth estimate).
  - Keep the Docker test sandbox as the quality gate, so a weaker model fails visibly rather than producing a bad patch.
  - Offer Claude Code escalation when tests fail.
- **Pinning recommendation for unattended runs:**
  1. Turn off "Auto-download updates".
  2. Before a run, check for a staged update (`upgrade.log`, staged files in `%LOCALAPPDATA%\Ollama`).
  3. For full control, use the standalone zip pinned to a version and start `ollama serve` from AeroPatch. Alternatively, install a known-good version with `$env:OLLAMA_VERSION="<x.y.z>"; irm https://ollama.com/install.ps1 | iex` (section 1). That pins only the install; the tray updater still runs afterwards.
  4. `winget pin add --id Ollama.Ollama` would only stop winget upgrades, not the tray updater.

### Gaps
- No credible measured tok/s was found for a 4B Q4_K_M model on a typical laptop CPU, Intel or AMD. Measure on target hardware with `ollama run --verbose` (eval rate) or `llama-bench -m <model>.gguf -p 512 -n 128`.
- No independent benchmarks were found for Ollama's Vulkan path on Intel Arc or Intel/AMD iGPUs in 2026, and Ollama's Windows doc does not mention Intel.
- No evaluation was found of a 1–2B model's quality on security-patch generation. Treat a 2B fallback as unproven.
- It is unclear which Ollama version first shipped the "Auto-download updates" toggle, and whether the update can be applied without the user clicking, as the project's 2026-10-21 experience suggests.
- `winget pin` behaviour was not verified in this pass.

## 5. UI surfaces for non-experts: effort, fit, and reuse of the existing MCP server

### Takeaway
- **Smallest set:**
  1. A doctor command plus a PowerShell bootstrap. The bootstrap also creates a Start-menu or desktop shortcut that opens the local page.
  2. A stdlib `http.server` page (zero new dependencies) as the default surface. It is the only option that keeps the whole conversation local and needs no account or other app.
  3. A Claude Desktop MCP Bundle (`.mcpb`, `uv` server type) as the one-click extra for people who already use Claude Desktop. It reuses the stdio MCP server as-is.
- **What would promote the MCPB:** two open questions keep it from being the default: whether Claude Desktop ships uv itself, and whether the free Claude plan allows local extensions. MCPB could move up if both resolve favourably, but Claude Desktop would still send the chat to a hosted model.
- **Fully local conversations:** Claude Desktop sends the conversation to a hosted model. For a fully local conversation, the existing MCP server already works in VS Code (signed out, with a local model), LM Studio and Open WebUI (via mcpo).
- **Poor fits for non-experts:** GitHub Actions, which have no GPU on free runners. Pre-commit hooks and a Windows 11 top-level context-menu entry, which needs a signed sparse package and a native COM DLL.

### Cited Findings
**(a) Claude Desktop MCP Bundles (.mcpb, formerly .dxt):**
- **Format** ([github.com/modelcontextprotocol/mcpb](https://github.com/modelcontextprotocol/mcpb)): a ZIP containing a local MCP server and a `manifest.json`, the only required file.
- **CLI:** `npm install -g @anthropic-ai/mcpb`, then `mcpb init` and `mcpb pack`.
- **Releases (measured via `gh api`):** latest tag v2.1.2, 2025-12-04. Last commits on main are from 2026-04-22.
- **Rename:** "Claude Desktop Extensions now use the .mcpb (MCP Bundle) file extension instead of .dxt", dated 2025-09-11 ([Anthropic engineering post](https://www.anthropic.com/engineering/desktop-extensions)).
- **Server types:** `node`, `python`, `binary` and `uv` ([MANIFEST.md](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md); spec text says "Current version: 0.3", last updated 2025-12-02, while its uv example uses `"manifest_version": "0.4"`, an inconsistency).
  - `python` bundles packages in `server/lib` or `server/venv`, but "cannot portably bundle compiled dependencies (e.g., pydantic, which the MCP Python SDK requires)".
  - `uv` declares dependencies in `pyproject.toml`, which are "installed by the host application using UV". It needs "UV Runtime (v0.4+)" and must not include `server/lib` or `server/venv`.
- **The uv example** ([examples/hello-world-uv](https://github.com/modelcontextprotocol/mcpb/tree/main/examples/hello-world-uv), read 2026-10-22):
  - Manifest: `"server": {"type": "uv", "entry_point": "src/server.py", "mcp_config": {"command": "uv", "args": ["run", "--directory", "${__dirname}", "src/server.py"]}}`, with `"compatibility": {"platforms": ["darwin","linux","win32"], "runtimes": {"python": ">=3.10"}}`.
  - Its README says the uv runtime "Downloads the correct Python version", "Creates an isolated virtual environment", "Installs dependencies from pyproject.toml", and has a "Small bundle size (~2 KB)".
- **`user_config` types** ([MANIFEST.md](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)): `string`, `number`, `boolean`, `directory` (folder picker), `file`, and `sensitive` (masked, stored securely).
  - Variables: `${__dirname}`, `${HOME}`, `${DOCUMENTS}`, `${user_config.KEY}`.
  - `platform_overrides` is keyed by `win32` or `darwin`.
- **Install UX** ([claude.com docs, Build a desktop extension with MCPB](https://claude.com/docs/connectors/building/mcpb)):
  - Three routes: double-click the `.mcpb`, drag it into Claude Desktop, or use Settings > Extensions > Advanced settings > Install Extension….
  - Each route opens a review, configure and permissions screen.
  - Installation is per-user.
- **Directory status:** "Desktop extension listings in the directory are deprecated, and the directory no longer accepts MCPB submissions. To distribute a local MCP server through the directory, include it in a plugin." Node.js is "strongly recommended" because it is bundled with Claude Desktop.
- **Support article** ([Getting Started with Local MCP Servers on Claude Desktop](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop), "updated over 3 weeks ago"):
  - Claude Desktop includes a built-in Node.js. Python and uv runtimes are not mentioned.
  - "Extensions from the official directory update automatically"; privately distributed ones need a manual reinstall.
  - Sensitive fields are encrypted with Windows Credential Manager.
- **Enterprise allowlist:** enabling it force-deletes existing desktop-extension installs ([support.claude.com allowlist article](https://support.claude.com/en/articles/12592343-enabling-and-using-the-desktop-extension-allowlist)).
- **Third-party Claude Desktop build:** end users cannot install `.mcpb` files themselves ([claude.com 3P docs](https://claude.com/docs/third-party/claude-desktop/extensions)).
- **Platforms (conflict):** the MCPB doc says Claude Desktop runs on macOS and Windows, while [modelcontextprotocol.io](https://modelcontextprotocol.io/docs/develop/connect-local-servers) says macOS, Windows and Linux.

**(b) Claude Code plugins** ([Claude Code docs: plugins, MCP](https://code.claude.com/docs/en/plugins/install); [manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference)):
- MCP servers are declared in `.mcp.json` at the plugin root, or inline under `mcpServers` in `plugin.json`. The value can be a `.json` file, an inline map, or a packaged `.mcpb`/`.dxt` (local path or URL).
- Paths: `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}`.
- Install: `/plugin marketplace add …`, then `/plugin install <name>@<marketplace>`. `--config <server>.<key>=<value>` needs Claude Code v2.1.285 or later.
- Tool names take the form `mcp__plugin_<plugin>_<server>__<tool>`.

**(c) A local web page:**
- **Dependency counts** (measured 2026-10-22, `uv pip compile --python 3.12`; counts include the package itself):

| Option | Packages |
|---|---|
| Gradio | 54 |
| NiceGUI | 48 |
| Streamlit | 35 |
| FastAPI + uvicorn | 14 |
| FastAPI | 11 |
| pywebview | 8 |
| stdlib `http.server` | 0 |

**(d) VS Code:**
- **Adding a server** ([VS Code docs, MCP servers](https://code.visualstudio.com/docs/copilot/customization/mcp-servers), page dated 2026-10-21):
  - Command Palette > MCP: Add Server > Command (stdio).
  - Personal servers go under "Copilot Global" (`~/.copilot/mcp-config.json`).
  - `.vscode/mcp.json` and the user-profile `mcp.json` remain only as deprecated compatibility locations.
  - There is an MCP gallery in the Extensions view (`@mcp`, Preview).
  - The page does not cover `vscode:mcp/install` links.
- **Local models without a Copilot plan:** models added with your own key or endpoint "work without signing into a GitHub account and without a Copilot plan", which enables "fully offline workflows with local models like Ollama" ([VS Code 1.122 release notes](https://code.visualstudio.com/updates/v1_122); [AI language models in VS Code](https://code.visualstudio.com/docs/agent-customization/language-models)).
  - The built-in Ollama provider is deprecated in favour of the official Ollama extension.
  - BYOK models don't power inline completions.
  - Older notes said BYOK was for Copilot Free and Pro users ([GitHub changelog, 2026-04-22](https://github.blog/changelog/2026-04-22-bring-your-own-language-model-key-in-vs-code-now-available/)); superseded.

**(e) GitHub Actions** ([GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners); [larger runners](https://docs.github.com/en/actions/reference/runners/larger-runners)):
- Standard Linux and Windows runners have 4 CPUs, 16 GB RAM and a 14 GB SSD. They are free and unlimited for public repositories.
- GPU runners (4 CPU, 1× Tesla T4 with 16 GB VRAM, 28 GB RAM, 176 GB SSD) are larger runners. They are always billed per minute, even for public repositories, and are available only on the Team or Enterprise Cloud plans.

**(g) Windows context menu:**
- An entry in Windows 11's modern (top-level) context menu needs a COM class implementing `IExplorerCommand`, registered with package identity. Unpackaged Win32 apps get identity through a sparse package ([Microsoft Learn, integrate packaged app with File Explorer](https://learn.microsoft.com/en-my/WINDOWS/APPS/desktop/modernize/integrate-packaged-app-with-file-explorer); [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/832880/adding-an-item-to-windows-11-context-menu)).
- Steps reported by one developer: build a sparse `AppxManifest.xml` with MakeAppX, sign it with signtool, and register it via the PackageManager API ([Mp3tag forum](https://community.mp3tag.de/t/context-menu-on-windows-11/54629/7)).
- Advanced Installer automates this, but it is commercial ([Advanced Installer](https://www.advancedinstaller.com/adding-items-to-windows-11-context-menu.html)).

### Inferences
**Which surfaces reuse what:**
- **The existing stdio MCP server:** MCPB (via the uv type), Claude Code plugins (`.mcp.json`, or point at the `.mcpb`), VS Code, Cursor, Windsurf, LM Studio, and Open WebUI via mcpo.
- **The CLI instead:** the web page, GitHub Action, pre-commit hook and context menu.
- **Neither:** ChatGPT. It only accepts remote HTTPS MCP (section 6), so it would need a new transport plus a tunnel.

**Effort and fit for non-experts:**

| Surface | Effort | Fit | Notes |
|---|---|---|---|
| (a) MCPB, `uv` type | Low: a manifest and `mcpb pack`, ~2 KB bundle, no new runtime dependencies | Best for existing Claude Desktop users (the chat runs on a hosted model) | A `directory` user_config gives a native folder picker for "which project to fix". Docker and Ollama must already be installed, so the doctor still matters. Private bundles don't auto-update. |
| (b) Claude Code plugin | Low | Weak for non-experts | Fits the escalation path; Claude Code is a developer tool. |
| (c) stdlib web page | Medium | Good | Zero new dependencies. Shows doctor status, finding list, diff view and "Apply / Discard" buttons. Gradio/Streamlit/NiceGUI add 35–54 packages against the "minimal dependencies" constraint. |
| (d) VS Code | Low (config only) | Developer-ish | The only mainstream editor route that keeps the whole conversation local without an account. |
| (e) GitHub Action | Medium | Poor as primary | A 4B model on 4 shared CPUs is slow (about 8–12 tok/s by the estimate in section 4), and Docker-in-runner is the sandbox. Workable as an opt-in "open a PR" job for public repos. |
| (f) pre-commit hook | Low | Poor | Non-technical users rarely use git hooks, and a multi-minute LLM run is a poor pre-commit fit. |
| (g) context menu | High for the Win11 top level | Poor | Needs a native DLL plus a signed sparse package. The classic HKCU registry verb is cheap but sits under "Show more options". |

**The deciding constraint: where the conversation runs.**
- Claude Desktop, Cursor, Windsurf and ChatGPT send the chat itself to a hosted model and need an account. With them, only the patch generation stays on the local Ollama.
- Fully local conversations come only from the stdlib web page, LM Studio (0.3.17+), Open WebUI + mcpo, and VS Code with BYOK and the Ollama extension.
- So the "free and local by default" promise should name either the web page or one of these local clients as the default.

**Two more points:**
- **Getting a double-click without a signed exe:** the bootstrap can create a `.lnk` shortcut to `aeropatch ui`, which starts the local page and opens the browser. Because the script creates the shortcut on the machine, it carries no Mark-of-the-Web and should raise no SmartScreen prompt. This is inferred, not verified.
- **Which manifest version to declare:** "UV Runtime (v0.4+)" in MANIFEST.md most likely means manifest_version 0.4, not uv version 0.4. The uv example declares `"manifest_version": "0.4"`, and the repo has `src/schemas/0.4.ts`. An AeroPatch uv bundle should declare 0.4, not the "current 0.3" from the spec text.

### Gaps
- Whether Claude Desktop ships its own uv, or needs uv on PATH, for `server.type: "uv"` bundles is unconfirmed. The example runs `uv` directly, the README says the host manages Python, and the support article mentions only built-in Node.
- Whether the Claude Free plan allows installing local `.mcpb` extensions was not found.
- The pre-commit hook format (`.pre-commit-hooks.yaml`) and any LLM-in-pre-commit precedent were not researched.
- The GitHub App route (a webhook server that opens PRs) was not researched. It would need hosting, which conflicts with local-first.
- The classic context-menu registry verb (`HKCU\Software\Classes\Directory\shell\...`) was not verified from a primary source in this pass.
- `vscode:mcp/install` one-click links and the `registerMcpServerDefinitionProvider` extension API were not covered by the fetched VS Code page.

## 6. Other MCP clients a non-technical user might have, and how a local stdio server is added in each

### Takeaway
- **Same stdio entry everywhere:** Claude Desktop, Cursor, Windsurf, LM Studio and VS Code all take the same `command`/`args` entry, pointing at `uv`/`aeropatch` with the `mcp` argument.
- **One-click installs:** only Claude Desktop (`.mcpb`) and LM Studio (an "Add to LM Studio" link) have them.
- **Bridge needed:** Open WebUI needs mcpo, because its native support is Streamable HTTP only.
- **Not possible:** ChatGPT cannot use a local stdio server at all.

### Cited Findings
- **Claude Desktop** ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/develop/connect-local-servers)):
  - Settings > Developer > Edit Config opens `%APPDATA%\Claude\claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`).
  - Format: `{"mcpServers": {"name": {"command": ..., "args": [...], "env": {...}}}}`. Paths must be absolute; quit and restart Claude Desktop fully after edits.
  - Windows gotcha: `${APPDATA}` ENOENT errors are fixed by adding the expanded `APPDATA` to `env`.
  - The `.mcpb` route is in section 5(a). winget ID `Anthropic.Claude` (measured).
- **ChatGPT** ([OpenAI Help, Developer mode and MCP apps](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)):
  - "ChatGPT connects only to remote MCP servers, not local ones." The server needs a public HTTPS endpoint, or a Secure MCP Tunnel for private networks.
  - Custom MCP servers are on ChatGPT web for Business and Enterprise/Edu.
  - Pro users get read/fetch-only MCP in Developer Mode ([Tagalog version of the article](https://help.openai.com/fil-ph/articles/12584461-developer-mode-at-mga-mcp-app-sa-chatgpt)).
  - Full MCP Developer Mode beta dates from 2025-10-17; workspace agents gained custom MCP servers on 2026-04-22 ([ChatGPT Business release notes](https://help.openai.com/en/articles/11391654-chatgpt-business-release-notes)).
  - Conflict: the current article and the older Developer Mode guidance differ on whether Developer Mode is still required per plan.
- **LM Studio** ([lmstudio.ai/docs/app/mcp](https://lmstudio.ai/docs/app/mcp)):
  - An MCP host since 0.3.17 (b10). It uses Cursor's `mcp.json` notation, edited via the right sidebar's Program tab > Install > Edit mcp.json.
  - The install button is a link of the form `https://lmstudio.ai/install-mcp?name=<name>&config=<base64 JSON>`.
  - Warnings: some servers "can run arbitrary code", and servers designed for cloud models "may use excessive tokens", which can cause context overflows on local models.
- **Cursor** ([cursor.com/docs/mcp](https://cursor.com/docs/mcp); [forum reply on the Windows path](https://forum.cursor.com/t/looking-in-wrong-spot-to-discover-mcp-servers/159930/11)):
  - Project config: `.cursor/mcp.json`. Global config: `~/.cursor/mcp.json` (Windows `C:\Users\<user>\.cursor\mcp.json`).
  - The two are merged, and the project file wins. Variables are resolved in `command`, `args` and `env`.
- **Windsurf** ([docs.windsurf.com, Cascade MCP](https://docs.windsurf.com/plugins/cascade/mcp)), conflicting paths:
  - The "Open MCP config file" action opens `%AppData%/devin/mcp_config.json` (macOS/Linux `~/.config/devin/mcp_config.json`).
  - Editor discovery reads `~/.codeium/windsurf/mcp_config.json`.
  - Check which one the installed build reads.
- **Open WebUI** ([docs.openwebui.com/features/mcp](https://docs.openwebui.com/features/mcp); [mcpo on PyPI](https://pypi.org/project/mcpo/)):
  - Native MCP since v0.6.31, Streamable HTTP only and admin-only. The docs say "OpenAPI remains the preferred integration path".
  - Stdio servers go through mcpo, e.g. `mcpo --port 8000 --api-key "top-secret" -- uvx mcp-server-time --local-timezone=America/New_York`.
- **VS Code:** MCP: Add Server > Command (stdio), saved to `~/.copilot/mcp-config.json`. Works signed out with a BYOK or Ollama model (section 5(d)).

### Inferences
- **One shared snippet:** `{"mcpServers": {"aeropatch": {"command": "uvx", "args": ["--from", "git+https://github.com/<owner>/aeropatch@vX", "aeropatch", "mcp"]}}}`, or `aeropatch mcp` once installed with `uv tool install`. It covers Claude Desktop, Cursor, LM Studio and Windsurf. For VS Code, the fetched page says portable files use `mcpServers` and the VS Code format uses `servers`. It does not show which key the new `~/.copilot/mcp-config.json` takes, so verify that before generating it. An `aeropatch mcp-config <client>` subcommand could print or merge the right file.
- **LM Studio link:** a ready-made "Add to LM Studio" link is cheap to generate and gives LM Studio users the closest thing to one click with a fully local conversation.
- **Local-model warning:** LM Studio's token-use warning matters for a 4 GB GPU. Keep the MCP tool descriptions and outputs short, so the local chat model's context isn't swamped while the patch model also needs VRAM.
- **Open WebUI:** it runs in Docker or as a Python app, and adding MCP is admin-gated. For a non-technical user that means two more moving parts, so document it rather than support it.

### Gaps
- No official source was found on whether the ChatGPT desktop apps (Windows or macOS) differ from ChatGPT web on MCP. The help article describes web only.
- Whether Cursor or Windsurf offer one-click deep-links for adding an MCP server in 2026 was not verified.
- Whether LM Studio's `install-mcp` link accepts stdio `command`/`args` configs was not verified; its docs show only a remote example.
