# MCP transcript

One session with `uv run aeropatch mcp` over stdio, recorded on 2026-10-16 with the `mcp` Python
client (2.2.0). The local model is the library `qwen3.5:4b`. The calls: the context of a finding,
`validate` with the scenario's reference fix and with the same fix plus a `# nosec` marker, one
`remediate`, and a `scan` outside the allowlisted root. Diffs are shown split into lines; the
tools take them as one string.

Results are candidate fixes that need human review. Nothing here commits, pushes or opens pull
requests.

Server: `aeropatch`. Instructions: "Security-fix tools for Python repositories. Results are
candidate fixes that need human review. Nothing here commits, pushes or opens pull requests."

## tools/list

- `scan`: Run Opengrep and Bandit on a repository and return the normalized findings.
- `get_context`: Scoped code context for a finding at path:line (enclosing function, imports, call sites).
- `validate`: Check a unified diff against a benchmark scenario: safety gates, then the PoC and regression tests in the sandbox. Works on a scratch copy; nothing on the host changes.
- `remediate`: Run the full remediation loop on a benchmark scenario and return the outcome with the candidate diff. Calls the model route of the named config, which may be a remote API.

## tools/call `get_context` (0.0 s)

Arguments:

```json
{
  "repo": "evaluations/scenarios/A-089-01/repo",
  "path": "app/db.py",
  "line": 18
}
```

Result:

```json
[
  {
    "files": {
      "app/db.py": "\"\"\"User directory backed by SQLite.\"\"\"\n\nimport sqlite3\n\n\ndef connect(path=\":memory:\"):\n    conn = sqlite3.connect(path)\n    conn.execute(\"CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)\")\n    return conn\n\n\ndef add_user(conn, name):\n    conn.execute(\"INSERT INTO users (name) VALUES (?)\", (name,))\n    conn.commit()\n\n\ndef find_user(conn, name):\n    cur = conn.execute(f\"SELECT id, name FROM users WHERE name = '{name}'\")\n    return cur.fetchall()"
    },
    "token_count": 118,
    "target": "find_user"
  }
]
```

## tools/call `validate` (1.8 s)

Arguments:

```json
{
  "task_id": "A-089-01",
  "diff": [
    "diff --git a/app/db.py b/app/db.py",
    "index ccbdec5..6dd9499 100644",
    "--- a/app/db.py",
    "+++ b/app/db.py",
    "@@ -15,5 +15,5 @@ def add_user(conn, name):",
    " ",
    " ",
    " def find_user(conn, name):",
    "-    cur = conn.execute(f\"SELECT id, name FROM users WHERE name = '{name}'\")",
    "+    cur = conn.execute(\"SELECT id, name FROM users WHERE name = ?\", (name,))",
    "     return cur.fetchall()"
  ]
}
```

Result:

```json
[
  {
    "resolved": true,
    "gate": {
      "ok": true,
      "violations": [],
      "details": []
    },
    "sandbox": {
      "applied": true,
      "poc_passed": true,
      "regressions_passed": true,
      "poc_total": 2,
      "regression_total": 3,
      "lint_ok": true,
      "rescan_clean": null,
      "original_rule_present": null,
      "failures": [],
      "label": "RESOLVED",
      "duration_s": 1.36,
      "timed_out": false,
      "apply_error": ""
    }
  }
]
```

## tools/call `validate` (0.5 s)

Arguments:

```json
{
  "task_id": "A-089-01",
  "diff": [
    "diff --git a/app/db.py b/app/db.py",
    "index ccbdec5..6dd9499 100644",
    "--- a/app/db.py",
    "+++ b/app/db.py",
    "@@ -15,5 +15,5 @@ def add_user(conn, name):",
    " ",
    " ",
    " def find_user(conn, name):",
    "-    cur = conn.execute(f\"SELECT id, name FROM users WHERE name = '{name}'\")",
    "+    cur = conn.execute(\"SELECT id, name FROM users WHERE name = ?\", (name,))  # nosec",
    "     return cur.fetchall()"
  ]
}
```

Result:

```json
[
  {
    "resolved": false,
    "gate": {
      "ok": false,
      "violations": [
        "SUPPRESSES_CHECKS"
      ],
      "details": [
        "SUPPRESSES_CHECKS: app/db.py adds a check-suppression marker"
      ]
    },
    "sandbox": null
  }
]
```

## tools/call `remediate` (4.9 s)

Arguments:

```json
{
  "task_id": "A-089-01",
  "config": "repair-local"
}
```

Result:

```json
[
  {
    "task_id": "A-089-01",
    "resolved": true,
    "label": "RESOLVED",
    "attempts": [
      {
        "n": 1,
        "route": "local",
        "label": "RESOLVED"
      }
    ],
    "diff": "diff --git a/app/db.py b/app/db.py\nindex ccbdec5..6dd9499 100644\n--- a/app/db.py\n+++ b/app/db.py\n@@ -15,5 +15,5 @@ def add_user(conn, name):\n \n \n def find_user(conn, name):\n-    cur = conn.execute(f\"SELECT id, name FROM users WHERE name = '{name}'\")\n+    cur = conn.execute(\"SELECT id, name FROM users WHERE name = ?\", (name,))\n     return cur.fetchall()\n",
    "duration_s": 4.86
  }
]
```

## tools/call `scan` (0.0 s, error)

Arguments:

```json
{
  "repo": "C:/Windows"
}
```

Result:

```json
[
  "Error executing tool scan: repo is not under an allowlisted root"
]
```
