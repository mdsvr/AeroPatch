"""`aeropatch` command line. Nothing here commits, pushes or opens PRs (doc 08 part 2, §5)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aeropatch import bench, scenario
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
    scenario.ensure_image(args.scenario)
    run_dir = RUNS_DIR / f"remediate-{args.scenario}-{cfg['name']}"
    result = loop.run(task, cfg, run_dir)
    print(f"{task.id}: {result.label} in {result.duration_s}s -> {run_dir / task.id / 'report.md'}")
    if result.final_diff:
        print(result.final_diff)
    return 0 if result.resolved else 1


def cmd_bench(args) -> int:
    cfg = load_config(args.config, local_model=args.local_model, frontier_model=args.frontier_model)
    path = bench.run_benchmark(cfg, args.split, args.run_id, args.ids or None)
    print(bench.table([path]))
    return 0


def cmd_report(args) -> int:
    print(bench.table([Path(p) for p in args.jsonl]))
    if args.json:
        for p in args.jsonl:
            print(json.dumps(bench.summarize(Path(p)), indent=2))
    return 0


def cmd_prune(args) -> int:
    from aeropatch.sandbox import sandbox

    print(f"removed {sandbox.prune_leftovers()} leftover containers")
    return 0


def main(argv: list[str] | None = None) -> int:
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
        s.add_argument("--local-model", default=None)
        s.add_argument("--frontier-model", default=None)
        s.set_defaults(fn=fn)

    s = sub.add_parser("report", help="baseline table from run JSONL files")
    s.add_argument("jsonl", nargs="+")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_report)

    sub.add_parser("prune", help="remove leftover sandbox containers").set_defaults(fn=cmd_prune)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
