# 07 — Ephemeral Docker Sandbox and Test Runner (Week 1)

Maps to: `src/sandbox/`, `docker/sandbox.Dockerfile`. Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. Threat being handled

Running a repository's tests means running **arbitrary code**: the repo's own code, its test
fixtures, its `conftest.py`, and now also code written by a model. Treat every sandbox run as
hostile. The sandbox has to stop four things: network egress (exfiltration, downloads), host
filesystem writes, resource exhaustion (fork bombs, memory, disk, infinite loops), and
privilege escalation to the container host.

## 2. Two-phase design: build with network, run without

`network_mode="none"` breaks `pip install` at test time. The fix is to separate the phases:

| Phase | Network | What happens | Trust |
|---|---|---|---|
| **Build** (once per scenario) | On | `pip install` from a **hash-pinned** lockfile into the image; copy the repo at a pinned commit | Only your pinned inputs |
| **Run** (every attempt) | **None** | Mount source + candidate patch read-only, copy to tmpfs, run PoC + regression tests, lint, re-scan | Untrusted code, fully locked down |

Build the images in Week 1 and tag them `aeropatch-sandbox:<scenario_id>`. After that, runs
start in about a second, because nothing is installed at run time.

## 3. Base image (`docker/sandbox.Dockerfile`, outline)

- `FROM python:3.12-slim` pinned **by digest**, not by tag, so benchmark runs are reproducible.
- Create an unprivileged user (`uid 10001`) and `WORKDIR /work`.
- Preinstall the harness tools: `git` (the slim image lacks it; `run.sh` uses `git apply`),
  `pytest`, `pytest-timeout`, `opengrep`/`bandit`, and a linter (`ruff`). Pin versions.
- Per-scenario layer: `COPY requirements.lock` and run `pip install --require-hashes`.
- No compilers or package managers beyond what the scenario's dependencies require.

## 4. Run-phase hardening flags

```text
docker run --rm --network none --read-only \
  -v <scratch_copy>:/src:ro \
  --tmpfs /work:rw,exec,size=512m --tmpfs /tmp:rw,size=256m \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 256 --memory 2g --memory-swap 2g --cpus 2 \
  --user 10001:10001 --ulimit nofile=1024 --stop-timeout 5 \
  aeropatch-sandbox:<id> /harness/run.sh
```

What each flag buys:

| Flag | Blocks |
|---|---|
| `--network none` | Exfiltration, dependency confusion at run time, callbacks |
| `--read-only` + `--tmpfs` | Persisting or tampering with the image; writes go to RAM-backed, size-capped dirs |
| `--cap-drop ALL` + `no-new-privileges` | Most privilege-escalation paths (setuid, raw sockets, mounts) |
| `--pids-limit` | Fork bombs |
| `--memory` = `--memory-swap` | Memory exhaustion with no swap thrash |
| `--cpus` | Starving the model server |
| non-root `--user` | Root-in-container escalation chains |
| outer `timeout` + `pytest-timeout` | Infinite loops; per-test and total wall-clock limits |

Also leave out `--privileged`, the Docker socket mount, host bind mounts of the real repo,
and `--env-file` with keys. The Docker default seccomp profile stays on; don't pass
`seccomp=unconfined`.

## 5. Getting code in and results out (no writable host mounts)

- **In**: for each attempt, the harness makes a **scratch copy** of the scenario source (pinned commit) plus the candidate `fix.patch` on WSL
  ext4 (never the real checkout, never NTFS). It's mounted **read-only** at `/src`, and
  `/harness/run.sh` (baked into the image) copies it into the tmpfs `/work` before running anything.
- Why not `put_archive()` / `docker cp`? Docker can't copy into tmpfs mounts, and a read-only
  root filesystem leaves nowhere else to put the files. The `:ro` mount of a throwaway copy is
  simpler and just as safe.
- **Out**: `run.sh` prints the JUnit XML and the scanner/linter JSON to stdout between fixed
  markers (e.g. `===AEROPATCH-JUNIT===`), capped at ~1 MB. The harness reads `logs()` and splits
  on the markers. There's no writable host mount, so there's nothing on the host to fill up or tamper with.
- **Cleanup**: `--rm`, plus `remove(force=True)` in a `finally` block so a crash doesn't leave
  containers running; delete the scratch copy afterwards. Label containers `aeropatch=1` and
  prune any leftovers at startup.
- The **tests come from the image** (copied from the pristine scenario at build time), not from
  `/src`, so a patch can't change the tests it's judged by (doc 08 part 2).

## 6. What a run executes (in order)

1. `git apply --check` then `git apply` on the diff. If this fails, the result is `applied=false`,
   and the rest is skipped.
2. **PoC tests**: the vulnerability test. It must fail on the original code and pass on the fix.
3. **Regression tests**: the project's relevant tests. They must pass both before and after.
4. **Lint**: `ruff check` on the changed files only. Style warnings are informational; syntax
   errors fail the run.
5. **Re-scan**: Opengrep/Bandit on the changed files. The original finding should be gone.

Run the unpatched baseline once at build time and cache it. Confirm the PoC fails and the
regressions pass on the vulnerable code. A scenario that doesn't show this pattern is broken
and must not enter the benchmark (doc 11).

## 7. Test-output parser (`runner.py`)

Small models get lost in 300-line tracebacks. The parser turns raw output into a compact
repair context:
- Parse JUnit XML: failed test IDs, assertion messages, and exception types.
- For each failure, keep the **last 15 lines** of the traceback frames that sit inside the
  repo (drop site-packages frames) and the assertion diff.
- Replace absolute paths with repo-relative ones; strip ANSI codes; cap the total at ~1.5k tokens.
- Classify the failure: `POC_FAIL`, `REGRESSION`, `IMPORT_ERROR`, `SYNTAX_ERROR`, `TIMEOUT`,
  `COLLECTION_ERROR`. The loop and the metrics both use this label.
- Keep the full raw output in `runs/` for humans. Only the trimmed version goes to the model.

## 8. Isolation strength: honest statement for the README

- Hardened runc containers inside the Docker Desktop WSL2 VM. Linux namespaces and cgroups,
  capabilities dropped, no network, read-only root.
- The containers share the VM's kernel, so a kernel exploit could escape the container
  (though not necessarily reach Windows).
- gVisor (`runsc`) isn't supported on Docker Desktop for Windows. Enhanced Container Isolation
  requires a paid Docker Business plan.
- Upgrade path: install native Docker Engine inside the WSL2 distro and register `runsc` as a
  runtime, or run sandboxes on a Linux host/VM with gVisor or Firecracker. Once a runtime is
  available, switching is a one-line change: `runtime="runsc"`.
- This level suits the threat model of your own scenarios plus public OSS repos at pinned
  commits. It's not suitable for running arbitrary unknown repos from the internet unattended.

## 9. Resource plan on this laptop

- At most **2 concurrent sandboxes** (2 CPUs / 2 GB each). The model server keeps ~4 CPUs.
- Image size: slim base (~150 MB) plus deps. 40 scenarios × ~300 MB ≈ 12 GB. Put Docker's
  disk image on a drive with room, and prune images between experiments.
- Typical run: 2–20 s. Set a 300 s hard cap, and treat a timeout as a failure with its own label.

## 10. Image build and cache management

- Build every scenario image once, with `docker build --pull=false` against the pinned base
  digest. Record the image digest in `scenario.json` after the build; the run header copies it.
- Keep the **baseline results** (vulnerable-code PoC/regression outcomes) next to the image
  digest. If the digest changes, rerun the scenario validator before using the image.
- Housekeeping between experiments: `docker container prune -f --filter label=aeropatch=1`,
  then remove dangling images. Never run a global `docker system prune -a` while a benchmark
  is running.
- Disk check before overnight runs: at least 20 GB free on the Docker disk image's drive.
- Build logs go in `runs/builds/<scenario>.log`. A build that needs network at *run* time
  is a bug in the scenario, not a sandbox exception to allow.

## 11. Tests for the sandbox itself (write these first)

- [ ] A test that tries `socket.create_connection(("1.1.1.1", 53))` fails inside the sandbox.
- [ ] Writing to `/usr` or `/` fails; writing to `/tmp` beyond 256 MB fails.
- [ ] A fork bomb is contained by `pids-limit`, and the host stays responsive.
- [ ] `while True: pass` is killed at the timeout and labelled `TIMEOUT`.
- [ ] Env vars inside the container contain no API keys (assert on `os.environ`).
- [ ] Container count returns to zero after a crash mid-run (`finally` cleanup works).

Next: [08-orchestration-part1.md](08-orchestration-part1.md)
