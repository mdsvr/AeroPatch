"""Read-only check of any folder: triage, plain-language cards, the HTML page and dismissals
(doc 17 part 3, Phase 1a).

`check` writes nothing inside the folder it checks; its results go to runs/folders/<name>-<hash8>/.
Only `dismiss` writes there, into .aeropatch/dismissed.json. A secret's value never reaches any
output: Bandit's B105-B107 messages quote it, so every message is replaced or redacted as soon as
the scan returns, and a secret card never shows its code line.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import html
import json
import math
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from string import Template

from aeropatch import config, judge
from aeropatch.agent import prompts
from aeropatch.agent.gates import _forbidden
from aeropatch.contracts import Finding
from aeropatch.tools import advisories, redos, scanners

CARDS_PATH = config.ROOT / "rules" / "cards.json"
SHOW = 5
MERGE_LINES = 3
TEST_GLOBS = ["tests/**", "test_*.py", "*_test.py", "conftest.py"]
# Part 4 §2's staging list; `*.egg-info` is matched by suffix below.
EXCLUDED_DIRS = [".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".tox", ".mypy_cache",
                 ".pytest_cache", "dist", "build"]
SECRET_RULES = {"B105", "B106", "B107"}
SECRET_MESSAGE = "Possible hard-coded password or key (the value is not shown)."
# docs/results/test/07-resolved-per-cwe.csv, the two untuned repair-local test runs (20261013-170329
# and 20261014-124302): fixed in both, and fixed in neither.
ALWAYS_FIXED_CWES = {"CWE-79", "CWE-209", "CWE-327", "CWE-338", "CWE-502", "CWE-601", "CWE-611", "CWE-798",
                     "CWE-1333"}
OFTEN_MISSED_CWES = {"CWE-22", "CWE-328", "CWE-918"}
OFTEN_MISSED_NOTE = ("AeroPatch's local model often missed this kind of problem on its tests, so give any "
                     "suggested change a careful look.")
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
IN_TESTS, IN_TOOLS = "in test code", "in a tools or build folder"
UNSURE = "Bandit is unsure about this one"
LOWER = "ranked below the five shown"
JUDGED = "the local model judged it a likely false alarm"
JUDGE_MAX = 2 * SHOW  # findings the model is asked about, at most: the shown ones and the next few
NO_JUDGE = "The local model is not running, so it did not review the findings. `aeropatch doctor` shows how to start it."
NO_OPENGREP = ("Only Bandit ran: Opengrep was not found, so AeroPatch's own rules were skipped and some "
               "problems may be missing. `aeropatch doctor` shows what to install.")

CARD_KEYS = ("headline", "what_could_happen", "when_it_matters", "the_change", "try_yourself")
GENERIC_CARD = {
    "headline": "The scanner flagged a possible problem that AeroPatch has no plain-language note for yet",
    "what_could_happen": "AeroPatch has no plain-language note for this rule yet, so it cannot say what "
                         "could happen. The scanner's own message is shown with this card.",
    "when_it_matters": "That depends on the rule and on how this code is used.",
    "the_change": "AeroPatch has no prepared explanation of a change for this rule yet.",
    "try_yourself": ["Look up the rule ID shown in the details.",
                     "Read the line it points to and ask whether input from outside can reach it."],
}
SECRET_CARD = {
    "headline": "If this is a real password or key, anyone who can read this file can use it",
    "what_could_happen": "Whoever gets a copy of this file, from a shared folder, a backup or a public "
                         "repository, can sign in or spend as if they were you.",
    "when_it_matters": "If this is a real password or key. Scanners often flag harmless strings such as "
                       "test values, so check which it is first.",
    "the_change": "1. Change the key at the provider first, on the site or service that issued it. "
                  "Editing the code does not undo an exposure: copies of the old file may already exist.\n"
                  "2. Move the value into an environment variable, so the code only names it:\n"
                  "    import os\n"
                  "    API_KEY = os.environ[\"API_KEY\"]",
    "try_yourself": ["Check on the provider's site when the key was last used, and from where.",
                     "Search your other files and backups for the same value.",
                     ("Set the environment variable where the app starts, then run the app once to see "
                      "that it still signs in.")],
}


@dataclass
class Card:
    n: int
    kind: str  # finding | secret
    finding: Finding
    headline: str
    what_could_happen: str
    when_it_matters: str
    the_change: str
    try_yourself: list[str]
    generic: bool
    also: list[Finding]  # the other tool's findings merged into this one
    note: str = ""


@dataclass
class CheckResult:
    folder: Path
    run_dir: Path
    shown: list[Card]
    parked: list[tuple[Finding, str]]
    dismissed: list[tuple[Finding, str]]
    opengrep: bool
    advisories: list[advisories.Advisory] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # what ran, or did not, beyond the scanners


def _usable(card) -> bool:
    return (isinstance(card, dict) and all(isinstance(card.get(k), str) for k in CARD_KEYS[:-1])
            and isinstance(card.get("try_yourself"), list))


def load_cards(path: Path = CARDS_PATH) -> dict:
    """rules/cards.json with the built-in generic and secret cards wherever it is missing,
    half-written or incomplete. An incomplete rule card is dropped, so that rule gets the generic card."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data = data if isinstance(data, dict) else {}
    rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
    return {"version": 1,
            "generic": data["generic"] if _usable(data.get("generic")) else GENERIC_CARD,
            "secret": data["secret"] if _usable(data.get("secret")) else SECRET_CARD,
            "rules": {k: v for k, v in rules.items() if _usable(v)}}


def _run_dir(folder: Path) -> Path:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", folder.name) or "folder"
    return config.RUNS_DIR / "folders" / f"{name}-{hashlib.sha1(str(folder).encode()).hexdigest()[:8]}"


def _set_aside(path: str) -> str | None:
    if any(p in EXCLUDED_DIRS or p.endswith(".egg-info") for p in PurePosixPath(path).parts[:-1]):
        return IN_TOOLS
    return IN_TESTS if _forbidden(path, TEST_GLOBS) else None


def _is_secret(folder: Path, f: Finding, also: list[Finding]) -> bool:
    return (any(x.rule_id in SECRET_RULES for x in [f, *also])
            or prompts._secret_reason(scanners._snippet(folder, f.path, f.line)) is not None)


def _function_size(folder: Path, f: Finding, spans: dict) -> float:
    """Lines in the innermost function around the finding, decorators included; module level is inf."""
    if f.path not in spans:
        try:
            tree = ast.parse((folder / f.path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            tree = None
        spans[f.path] = [(min([n.lineno, *(d.lineno for d in n.decorator_list)]), n.end_lineno)
                         for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                         ] if tree else []
    return min((end - start + 1 for start, end in spans[f.path] if start <= f.line <= end), default=math.inf)


def _load_dismissed(folder: Path) -> dict:
    try:
        data = json.loads((folder / ".aeropatch" / "dismissed.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _card(n: int, f: Finding, also: list[Finding], secret: bool, cards: dict) -> Card:
    text = cards["secret"] if secret else cards["rules"].get(f.rule_id)
    # The rule cards for these classes already say so in the_change; only the generic card needs the note.
    card = Card(n=n, kind="secret" if secret else "finding", finding=f, also=also, generic=text is None,
                **{k: (text or cards["generic"])[k] for k in CARD_KEYS[:-1]},
                try_yourself=list((text or cards["generic"])["try_yourself"]),
                note=OFTEN_MISSED_NOTE if text is None and f.cwe in OFTEN_MISSED_CWES else "")
    if secret and "os.environ" not in card.the_change:  # part 3 §3: the two-line example is always shown
        card.the_change += '\n    import os\n    API_KEY = os.environ["API_KEY"]'
    return card


def _judge(folder: Path, candidates: list, ask=None) -> tuple[list, list[tuple[Finding, str]], list[str]]:
    """Phase C: the model may set aside a near-top finding, never delete one. Secrets are not sent,
    and Ollama being down keeps everything. (kept candidates, set aside, notes)"""
    ask = ask or judge.ask
    kept, aside, asked, seconds = [], [], 0, 0.0
    for i, c in enumerate(candidates):
        if c[2] or len(kept) >= SHOW or asked >= JUDGE_MAX:
            kept.append(c)
            continue
        try:
            v = ask(folder, c[0])
        except judge.LocalServerDown:
            return kept + candidates[i:], aside, [NO_JUDGE]
        asked, seconds = asked + 1, seconds + v.seconds
        if v.keep:
            kept.append(c)
        else:
            aside.append((c[0], f"{JUDGED}: {v.reason}" if v.reason else JUDGED))
    note = (f"The local model reviewed {asked} findings and set {len(aside)} aside ({seconds:.0f} s)"
            + ("; they are listed with --all." if aside else "."))
    return kept, aside, [note] if asked else []


def triage(folder: Path, findings: list[Finding], opengrep: bool = True, use_judge: bool = False) -> CheckResult:
    """Part 3 §2, steps 2-7, over the findings of `scanners.scan(folder)`; with `use_judge`, the
    local model reviews the top of the ranking before the five are cut (Phase C)."""
    folder = Path(folder).resolve()
    findings = [dataclasses.replace(f, message=SECRET_MESSAGE if f.rule_id in SECRET_RULES
                                    else prompts.redact(f.message)) for f in findings]
    # One scanner can report the same rule twice on one line (two matching patterns): one card.
    findings = list({(f.tool, f.rule_id, f.path, f.line): f for f in findings}.values())
    parked: list[tuple[Finding, str]] = []
    kept = []
    for f in findings:  # 2. test code, tools and build folders
        reason = _set_aside(f.path)
        if reason:
            parked.append((f, reason))
        else:
            kept.append(f)

    heads = [(f, []) for f in kept if f.tool == "opengrep"]  # 3. merge across tools, keep Opengrep's
    groups = list(heads)
    for b in (f for f in kept if f.tool != "opengrep"):
        near = [h for h in heads if h[0].path == b.path and abs(h[0].line - b.line) <= MERGE_LINES]
        if near:
            min(near, key=lambda h: abs(h[0].line - b.line))[1].append(b)
        else:
            groups.append((b, []))

    saved = _load_dismissed(folder)
    dismissed: list[tuple[Finding, str]] = []
    candidates = []
    for f, also in groups:
        secret = _is_secret(folder, f, also)
        # 4. Bandit unsure. B105-B107 are always LOW severity, so a secret is kept: its card opens
        # with "If this is a real password or key".
        if f.tool == "bandit" and "low" in (f.confidence, f.severity) and not secret:
            parked.append((f, UNSURE))
        elif f.fingerprint in saved:  # 5. dismissed, with the saved reason
            entry = saved[f.fingerprint] if isinstance(saved[f.fingerprint], dict) else {}
            dismissed.append((f, f"{entry.get('reason', '')} (dismissed {entry.get('date', '')})"))
        else:
            candidates.append((f, also, secret))

    spans: dict = {}  # 6. severity, then function size, then the CWEs the local model always fixed
    candidates.sort(key=lambda c: (SEVERITY_RANK.get(c[0].severity, 1), _function_size(folder, c[0], spans),
                                   c[0].cwe not in ALWAYS_FIXED_CWES, c[0].path, c[0].line))
    notes = []
    if use_judge:
        candidates, aside, notes = _judge(folder, candidates)
        parked += aside
    cards = load_cards(CARDS_PATH)
    shown = [_card(n, f, also, secret, cards) for n, (f, also, secret) in enumerate(candidates[:SHOW], 1)]
    parked += [(f, LOWER) for f, _, _ in candidates[SHOW:]]  # 7. the rest stay one --all away
    return CheckResult(folder=folder, run_dir=_run_dir(folder), shown=shown, parked=parked,
                       dismissed=dismissed, opengrep=opengrep, notes=notes)


def python_files(folder: Path) -> list[str]:
    """Folder-relative .py files outside the excluded folders, which are never walked."""
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not d.endswith(".egg-info"))
        out += [(Path(root) / f).relative_to(folder).as_posix() for f in sorted(files) if f.endswith(".py")]
    return out


def check_folder(folder: Path, offline: bool = False, extra_rules: bool = False, use_judge: bool = False) -> CheckResult:
    """`offline`: skip the advisory lookup, the one step that uses the network (package names and
    versions only). `extra_rules`: also run rules-extra/ with taint analysis. `use_judge`: Phase C."""
    folder = Path(folder).resolve()
    scan = scanners.scan(folder, extra=extra_rules)
    py = python_files(folder)
    result = triage(folder, scan["findings"] + redos.scan(folder, py), scan["opengrep"], use_judge)
    if not offline:
        result.advisories, n, error = advisories.audit(folder, py)
        result.notes.insert(0, error or (f"Looked up {n} pinned packages in the OSV advisory database at osv.dev "
                                         "(package names and versions only; no code was sent)." if n else ""))
        result.notes = [x for x in result.notes if x]
    result.run_dir.mkdir(parents=True, exist_ok=True)
    (result.run_dir / "check.json").write_text(json.dumps(asdict(result), indent=2, default=str) + "\n",
                                               encoding="utf-8")
    return result


def _fields(c: Card) -> list[tuple[str, str]]:
    return [("What could happen", c.what_could_happen), ("When it matters", c.when_it_matters),
            ("What the change does", c.the_change)]


def _more_line(result: CheckResult) -> str:
    lower = sum(r == LOWER for _, r in result.parked)
    counts = [(lower, "ranked lower"), (len(result.parked) - lower, "more set aside (likely not a problem)"),
              (len(result.dismissed), "dismissed earlier")]
    return ", ".join(f"{n} {text}" for n, text in counts if n)


ADVISORY_HEADLINE = "A package this project pins has published security problems"


def advisory_fields(a: advisories.Advisory) -> list[tuple[str, str]]:
    """The fixed card for a vulnerable pin (Phase B1): no model, and the user edits the pin."""
    p = a.pin
    change = (f"In {p.path}, change {p.name}=={p.version} to {p.name}=={a.fixed}, reinstall, and run your tests."
              if a.fixed else "")
    if a.unfixed:
        change += ((" " if change else "") + f"No newer version fixes {', '.join(a.unfixed[:3])} yet: read "
                   + ("that advisory" if len(a.unfixed) == 1 else "those advisories")
                   + " to see whether the problem reaches your app.")
    used = (f"Imported in {', '.join(a.imported_in[:3])}{' and more' if len(a.imported_in) > 3 else ''}."
            if a.imported_in else
            "AeroPatch found no import of it in your code, but another package you use may still use it.")
    return [("Advisories", ", ".join(a.ids[:6]) + (f" and {len(a.ids) - 6} more" if len(a.ids) > 6 else "")
             + (f": {a.summary}" if a.summary else "")),
            ("Used here", used), ("What the change does", change)]


def format_text(result: CheckResult, show_all: bool = False) -> str:
    out = [f"AeroPatch checked {result.folder}"]
    if not result.opengrep:
        out.append(NO_OPENGREP)
    out += result.notes
    for a in result.advisories:
        out += ["", f"* {ADVISORY_HEADLINE}: {a.pin.name} {a.pin.version}", f"   {a.pin.path}:{a.pin.line}"]
        out += [f"   {label}: {text}" for label, text in advisory_fields(a)]
    if not result.shown:
        out.append("\nNo problems to show.")
    for c in result.shown:
        f = c.finding
        out += ["", f"{c.n}. {c.headline}", f"   {f.path}:{f.line}"]
        out += [f"   {label}: " + text.replace("\n", "\n      ") for label, text in _fields(c)]
        if c.generic:
            out.append(f"   The scanner says: {f.message}")
        out += ["   Try it yourself:", *(f"     - {t}" for t in c.try_yourself)]
        if c.note:
            out.append(f"   Note: {c.note}")
    more = _more_line(result)
    if more and not show_all:
        out += ["", f"{more}: show with --all"]
    for title, items in (("Set aside", result.parked), ("Dismissed earlier", result.dismissed)):
        if show_all and items:
            out += ["", f"{title}:", *(f"  {f.path}:{f.line}  {f.rule_id}: {f.message} ({r})" for f, r in items)]
    return "\n".join(out)


CSS = """\
:root{--bg:#f6f6f4;--card:#fff;--fg:#1f2328;--muted:#59636e;--line:#d0d7de;--accent:#9a3412;--note:#fff4d6;--code:#eff1f3}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--card:#1b1f24;--fg:#e6e8eb;--muted:#9da7b3;--line:#30363d;\
--accent:#fdba74;--note:#33290f;--code:#0d1117}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:46rem;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.5rem;margin:0 0 4px}
.sub{color:var(--muted);margin:0 0 20px;overflow-wrap:anywhere}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px;margin:0 0 16px}
.card h2{font-size:1.15rem;margin:0 0 4px}
.n{color:var(--accent);margin-right:.4em}
.where,code,pre{font-family:ui-monospace,Consolas,monospace}
.where{color:var(--muted);margin:0 0 8px;overflow-wrap:anywhere}
dt{font-weight:600;margin-top:10px}
dd{margin:2px 0 0;white-space:pre-wrap;overflow-wrap:anywhere}
.note{background:var(--note);padding:8px 12px;border-radius:6px}
details{margin-top:12px}
summary{cursor:pointer;color:var(--muted)}
pre{background:var(--code);padding:8px 12px;border-radius:6px;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}
ul{padding-left:1.2em}
"""
PAGE = Template("""\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>AeroPatch check</title>
<style>
$css</style>
</head>
<body>
<main>
<h1>AeroPatch check</h1>
<p class="sub">$folder</p>
$body
</main>
</body>
</html>
""")


def _card_html(c: Card, folder: Path) -> str:
    e, f = html.escape, c.finding
    # ponytail: a secret card never shows its line; redact misses short values.
    code = "" if c.kind == "secret" else prompts.redact(scanners._snippet(folder, f.path, f.line)).strip()
    details = [("Rule", f"{f.tool} {f.rule_id}"), ("CWE", f.cwe or "none given"), ("Scanner says", f.message)]
    details += [("Also found by", ", ".join(f"{a.tool} {a.rule_id} (line {a.line})" for a in c.also))] if c.also else []
    rows = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in details)
    rows += (f"<dt>Code</dt><dd><pre><code>{e(code)}</code></pre></dd>" if code else
             "<dt>Code</dt><dd>Hidden, because it may contain the password or key.</dd>" if c.kind == "secret" else "")
    return "\n".join(filter(None, [
        '<article class="card">',
        f'<h2><span class="n">{c.n}.</span>{e(c.headline)}</h2>',
        f'<p class="where">{e(f.path)}:{f.line}</p>',
        "<dl>" + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in _fields(c)) + "</dl>",
        f"<p>The scanner says: {e(f.message)}</p>" if c.generic else "",
        "<p>Try it yourself:</p><ul>" + "".join(f"<li>{e(t)}</li>" for t in c.try_yourself) + "</ul>",
        f'<p class="note">{e(c.note)}</p>' if c.note else "",
        f"<details><summary>Details</summary><dl>{rows}</dl></details>",
        "</article>"]))


def render_html(result: CheckResult) -> str:
    e = html.escape
    body = [f'<p class="note">{e(NO_OPENGREP)}</p>'] if not result.opengrep else []
    body += [f'<p class="sub">{e(n)}</p>' for n in result.notes]
    body += ['<article class="card">'
             f'<h2>{e(ADVISORY_HEADLINE)}: {e(a.pin.name)} {e(a.pin.version)}</h2>'
             f'<p class="where">{e(a.pin.path)}:{a.pin.line}</p>'
             "<dl>" + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in advisory_fields(a)) + "</dl></article>"
             for a in result.advisories]
    body += [_card_html(c, result.folder) for c in result.shown] or ["<p>No problems to show.</p>"]
    for title, items in (("Set aside", result.parked), ("Dismissed earlier", result.dismissed)):
        if items:
            body.append(f"<details><summary>{e(title)}: {len(items)}</summary><ul>" + "".join(
                f"<li><code>{e(f.path)}:{f.line}</code> {e(f.rule_id)}: {e(f.message)} ({e(r)})</li>"
                for f, r in items) + "</ul></details>")
    return PAGE.substitute(css=CSS, folder=e(str(result.folder)), body="\n".join(body))


def write_html(result: CheckResult) -> Path:
    page = result.run_dir / "report.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(render_html(result), encoding="utf-8")
    return page


def dismiss(folder: Path, n: int, reason: str, extra_rules: bool = False, use_judge: bool = False) -> Finding:
    """Hide shown card n from later checks. The fingerprint includes the code line, so the
    dismissal lapses when that code changes. Pass the options the check ran with, so n means
    the same card; advisory cards are not numbered, so no lookup is needed."""
    if not reason.strip():
        raise ValueError("give a reason, so you know later why it was hidden")
    result = check_folder(folder, offline=True, extra_rules=extra_rules, use_judge=use_judge)
    if not 1 <= n <= len(result.shown):
        raise IndexError(f"the check shows {len(result.shown)} problems, so there is no number {n}")
    f = result.shown[n - 1].finding
    path = result.folder / ".aeropatch" / "dismissed.json"
    # A file that will not parse raises here rather than being overwritten.
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    saved[f.fingerprint] = {"reason": reason.strip(), "date": datetime.now(UTC).date().isoformat(), "rule_id": f.rule_id,
                            "path": f.path}
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return f
