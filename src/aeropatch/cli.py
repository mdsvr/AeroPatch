"""`aeropatch` command line. Nothing here commits, pushes or opens PRs (doc 08 part 2, §5)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aeropatch import bench, metrics, scenario
from aeropatch.config import CONFIGS, RUNS_DIR, load_config


def _ids(args) -> list[str]:
    return scenario.list_ids(args.split) if args.all or not args.ids else args.ids


def cmd_build_base(args) -> int:
    from aeropatch.sandbox import sandbox

    print(sandbox.build_base(RUNS_DIR / "builds" / "base.log"))
    return 0


def cmd_build(args) -> int:
    for sid in _ids(args):
        print(sid, scenario.ensure_image(sid, rebuild=True))
    return 0


def cmd_validate(args) -> int:
    bad = 0
    for sid in _ids(args):
        v = scenario.validate(sid, rebuild=args.rebuild)
        print(f"{sid}: {'OK' if v.ok else 'INVALID'}")
        for name, res in v.checks.items():
            print(f"    {name}: {res}")
        bad += not v.ok
    return 1 if bad else 0


def cmd_scan(args) -> int:
    from aeropatch.tools import scanners

    res = scanners.scan(Path(args.repo))
    if not res["opengrep"]:
        print("note: opengrep not found; Bandit only", file=sys.stderr)
    for f in res["findings"]:
        print(f"{f.path}:{f.line} [{f.tool} {f.rule_id} {f.cwe} {f.severity}] {f.message}")
    return 0


def cmd_context(args) -> int:
    from aeropatch.tools.context import get_context

    ctx = get_context(Path(args.repo), args.path, args.line)
    print(f"# target: {ctx.target or '-'}  (~{ctx.token_count} tokens)")
    for path, snippet in ctx.files.items():
        print(f"--- {path}\n{snippet}\n")
    return 0


def cmd_remediate(args) -> int:
    from aeropatch.agent import loop

    cfg = load_config(args.config, local_model=args.local_model, frontier_model=args.frontier_model)
    task = scenario.load(args.scenario)
    if cfg.get("run_tests", True):  # the Suggest level needs no Docker (doc 17)
        scenario.ensure_image(args.scenario)
    run_dir = RUNS_DIR / f"remediate-{args.scenario}-{cfg['name']}"
    result = loop.run(task, cfg, run_dir)
    print(f"{task.id}: {result.label} in {result.duration_s}s -> {run_dir / task.id / 'report.md'}")
    if result.final_diff:
        print(result.final_diff)
    return 0 if result.resolved else 1


def cmd_bench(args) -> int:
    cfg = load_config(args.config, local_model=args.local_model, frontier_model=args.frontier_model)
    path = bench.run_benchmark(cfg, args.split, args.run_id, args.ids or None, args.jobs, folder=args.folder)
    print(metrics.report([path]))
    return 0


def cmd_report(args) -> int:
    print(metrics.report([Path(p) for p in args.jsonl], Path(args.csv) if args.csv else None))
    return 0


def cmd_mcp(args) -> int:
    from aeropatch import mcp_server

    mcp_server.server.run("stdio")
    return 0


def cmd_doctor(args) -> int:
    from aeropatch import doctor

    return doctor.main()


def _folder(arg: str) -> Path | None:
    folder = Path(arg)
    if not folder.is_dir():
        print(f"There is no folder at {folder}. Check the path and try again.", file=sys.stderr)
        return None
    return folder


def cmd_check(args) -> int:
    from aeropatch import check

    folder = _folder(args.folder)
    if folder is None:
        return 2
    res = check.check_folder(folder, offline=args.offline, extra_rules=args.extra_rules, use_judge=args.judge)
    print(check.format_text(res, show_all=args.all))
    if args.open:
        import webbrowser

        page = check.write_html(res)
        webbrowser.open(page.resolve().as_uri())
        print(f"\nThe same results are open in your browser: {page}")
    return 0


def cmd_dismiss(args) -> int:
    from aeropatch import check

    folder = _folder(args.folder)
    if folder is None:
        return 2
    try:
        f = check.dismiss(folder, args.n, args.reason, extra_rules=args.extra_rules, use_judge=args.judge)
    except (IndexError, ValueError) as e:
        print(f"Could not dismiss problem {args.n}: {e}", file=sys.stderr)
        return 2
    print(f"Dismissed {f.path}:{f.line}. It stays hidden until that code changes.")
    return 0


def cmd_prune(args) -> int:
    from aeropatch.sandbox import sandbox

    print(f"removed {sandbox.prune_leftovers()} leftover containers")
    if args.images:
        from aeropatch import folder

        print(f"removed {folder.prune_images()} folder images")
    return 0


def cmd_fix(args) -> int:
    from aeropatch import folder as fp
    from aeropatch.models.base import LocalServerDown

    folder = _folder(args.folder)
    if folder is None:
        return 2
    try:
        rec = fp.fix(folder, args.n, level="suggest" if args.suggest else "auto", extra_rules=args.extra_rules)
    except (IndexError, ValueError, fp.FolderError) as e:
        print(f"Could not fix problem {args.n}: {e}", file=sys.stderr)
        return 2
    except LocalServerDown:
        print("The local model is not running. `aeropatch doctor` shows how to start it.", file=sys.stderr)
        return 2
    print(f"{rec['n']}. {rec['headline']}")
    for note in rec["notes"]:
        print(f"   {note}")
    print(f"   Result: {rec['label']}")
    if rec["diff"]:
        print("\n" + rec["diff"])
        print(f"Nothing in your folder has changed yet. To make this change: aeropatch apply {args.folder} "
              f"{rec['n']}")
    return 0


def cmd_apply(args) -> int:
    from aeropatch import folder as fp

    folder = _folder(args.folder)
    if folder is None:
        return 2
    try:
        backup = fp.apply(folder, args.n)
    except (FileNotFoundError, ValueError) as e:
        print(f"Could not apply fix {args.n}: {e}", file=sys.stderr)
        return 2
    print(f"Applied fix {args.n}. The original files are kept in {backup}; `aeropatch undo {args.folder} {args.n}` "
          "puts them back.")
    return 0


def cmd_undo(args) -> int:
    from aeropatch import folder as fp

    folder = _folder(args.folder)
    if folder is None:
        return 2
    try:
        fp.undo(folder, args.n)
    except (FileNotFoundError, ValueError) as e:
        print(f"Could not undo fix {args.n}: {e}", file=sys.stderr)
        return 2
    print(f"Undid fix {args.n}: the files are as they were before it.")
    return 0


def main(argv: list[str] | None = None) -> int:
    # A Windows console is often cp1252; a diff of real code (a "→" in a comment) crashed printing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    p = argparse.ArgumentParser(prog="aeropatch", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build-base", help="build the sandbox base image").set_defaults(fn=cmd_build_base)
    for name, fn, hlp in (("build", cmd_build, "build scenario images"),
                          ("validate", cmd_validate, "run the 4 scenario validation checks")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("ids", nargs="*")
        s.add_argument("--all", action="store_true")
        s.add_argument("--split", default=None)
        if name == "validate":
            s.add_argument("--rebuild", action="store_true")
        s.set_defaults(fn=fn)

    s = sub.add_parser("scan", help="run Opengrep + Bandit on a repo")
    s.add_argument("repo")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("context", help="print the scoped context for path:line")
    s.add_argument("repo")
    s.add_argument("path")
    s.add_argument("line", type=int)
    s.set_defaults(fn=cmd_context)

    for name, fn in (("remediate", cmd_remediate), ("bench", cmd_bench)):
        s = sub.add_parser(name)
        if name == "remediate":
            s.add_argument("scenario")
            s.add_argument("--config", default="baseline-qwen3.5-4b", choices=sorted(CONFIGS))
        else:
            s.add_argument("--config", required=True, choices=sorted(CONFIGS))
            s.add_argument("--split", default="dev")
            s.add_argument("--run-id", default=None)
            s.add_argument("--ids", nargs="*")
            s.add_argument("--jobs", type=int, default=1, choices=(1, 2),
                           help="tasks run at once; local generation stays one at a time (doc 11 §8)")
            s.add_argument("--folder", action="store_true",
                           help="run each scenario through the `fix` path: folder image, baseline, hidden PoC")
        s.add_argument("--local-model", default=None)
        s.add_argument("--frontier-model", default=None)
        s.set_defaults(fn=fn)

    s = sub.add_parser("report", help="CIs, resolve@k, McNemar, per-CWE and failure attribution (doc 12)")
    s.add_argument("jsonl", nargs="+")
    s.add_argument("--csv", default=None, help="also write each table as a CSV into this folder")
    s.set_defaults(fn=cmd_report)

    sub.add_parser("doctor", help="check that what AeroPatch needs is installed and running (doc 17)"
                   ).set_defaults(fn=cmd_doctor)
    s = sub.add_parser("check", help="read-only check of a folder: up to five problems, explained (doc 17)")
    s.add_argument("folder")
    s.add_argument("--all", action="store_true", help="also list the problems set aside as likely false alarms")
    s.add_argument("--open", action="store_true", help="also open the results as a page in your browser")
    s.add_argument("--offline", action="store_true",
                   help="skip the advisory lookup at osv.dev (it sends package names and versions, no code)")
    check_options = (
        (("--extra-rules",), {"action": "store_true",
                              "help": "also run the extra taint rules (rules-extra/; not yet measured on real repos)"}),
        (("--judge",), {"action": "store_true",
                        "help": "let the local model set aside likely false alarms near the top (needs Ollama; "
                                "it reads code without comments or docstrings; what it sets aside is listed with --all)"}))
    for flags, kw in check_options:
        s.add_argument(*flags, **kw)
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("dismiss", help="hide one problem from later checks, with a reason")
    s.add_argument("folder")
    s.add_argument("n", type=int, help="the problem's number in the last check")
    s.add_argument("--reason", required=True)
    for flags, kw in check_options:  # the same options as that check, so n is the same card
        s.add_argument(*flags, **kw)
    s.set_defaults(fn=cmd_dismiss)

    sub.add_parser("mcp", help="serve the tools over MCP on stdio (doc 06)").set_defaults(fn=cmd_mcp)
    s = sub.add_parser("prune", help="remove leftover sandbox containers")
    s.add_argument("--images", action="store_true", help="also remove folder images (each about 1-1.5 GB)")
    s.set_defaults(fn=cmd_prune)
    s = sub.add_parser("fix", help="propose a change for one problem of the last check; your folder is not touched")
    s.add_argument("folder")
    s.add_argument("n", type=int, help="the problem's number in the check")
    s.add_argument("--suggest", action="store_true", help="do not run your tests (no Docker needed)")
    s.add_argument("--extra-rules", action="store_true", help="the check ran with --extra-rules")
    s.set_defaults(fn=cmd_fix)
    for name, fn, hlp in (("apply", cmd_apply, "make the proposed change in your folder, keeping a backup"),
                          ("undo", cmd_undo, "put back the files an apply changed")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("folder")
        s.add_argument("n", type=int, help="the problem's number")
        s.set_defaults(fn=fn)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
