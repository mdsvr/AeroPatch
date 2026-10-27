"""Phase B1's plumbing check (reports/Real bug detection and model mix.md): an app that pins the
vulnerable version of each Tier B library gets that advisory with a fixed version, and the same app
pinned at the advisory's fixed version does not get it. Uses the network (api.osv.dev).

    python evaluations/tools/advisory_plumbing.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeropatch.tools import advisories


def main() -> int:
    ok = 0
    sids = sorted(p.parent.name for p in (ROOT / "evaluations" / "scenarios").glob("B-*/scenario.json"))
    for sid in sids:
        meta = json.loads((ROOT / "evaluations" / "scenarios" / sid / "scenario.json").read_text(encoding="utf-8"))
        ghsa = meta["source_url"].rstrip("/").rsplit("/", 1)[1]
        vuln = advisories._get(f"{advisories.OSV}/vulns/{ghsa}")
        aff = next(a for a in vuln["affected"] if a["package"]["ecosystem"] == "PyPI")
        name = advisories._norm(aff["package"]["name"])
        vulnerable = aff["versions"][-1]  # the newest affected release
        fixed = advisories._fixed_above(vuln, name, vulnerable)
        rows = []
        for pin in (vulnerable, fixed):
            with tempfile.TemporaryDirectory() as d:
                Path(d, "requirements.txt").write_text(f"{name}=={pin}\n", encoding="utf-8")
                adv, _, err = advisories.audit(Path(d), [])
                hit = next((a for a in adv if meta["cve"] in a.ids or ghsa in a.ids), None)
                rows.append((pin, hit, err))
        (v_pin, v_hit, v_err), (f_pin, f_hit, f_err) = rows
        passed = bool(v_hit and v_hit.fixed and fixed and f_hit is None and not v_err and not f_err)
        ok += passed
        print(f"{sid:10} {name:15} {v_pin:>10} flagged={bool(v_hit)!s:5} offers={v_hit.fixed if v_hit else '-':>8} | "
              f"{f_pin:>8} flagged={bool(f_hit)!s:5} {'PASS' if passed else 'FAIL'} {v_err or f_err}")
    print(f"\n{ok} of {len(sids)} pass")
    return 0 if ok == len(sids) else 1


if __name__ == "__main__":
    raise SystemExit(main())
