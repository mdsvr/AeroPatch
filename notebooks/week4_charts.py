"""Week 4 charts for the README (doc 12 §6), drawn from the run files only.

    .venv-notebook\\Scripts\\python.exe notebooks\\week4_charts.py

Writes docs/results/{cost-accuracy,repair-curve,failure-attribution}.png. Every number comes
from the runs named in RUNS; the README table beside each chart names the same files.
"""

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["text.parse_math"] = False  # "$0.023" is money, not mathtext

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "results"

# test split, 27 scenarios per run. Two runs per local row and per cascade, one for the frontier.
RUNS = {
    "Untuned Qwen3.5-4B, local": ["20261013-170329-repair-local-test", "20261014-124302-repair-local-test"],
    "Fine-tuned v2, local": ["20261014-123112-repair-local-test", "20261014-125354-repair-local-test"],
    "Cascade: local, then Opus 5.5": ["20261016-c1-cascade-claude-code-test", "20261016-c2-cascade-claude-code-test"],
    "Opus 5.5 alone": ["20261016-f1-repair-claude-code-test"],
}

# Reference palette, light mode (dataviz skill); slots in fixed order, validated. A model keeps
# its colour in every chart; the failure causes are their own categorical set.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
COLOUR = dict(zip(RUNS, SERIES))
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"


def load(run_id: str) -> tuple[list[dict], list[dict]]:
    recs = [json.loads(line) for line in (ROOT / "runs" / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()]
    return [r for r in recs if r.get("type") == "attempt"], [r for r in recs if r.get("type") == "result"]


def summary(run_ids: list[str]) -> dict:
    n = resolved = 0
    at = [0, 0, 0]
    cost = seconds = 0.0
    causes: Counter = Counter()
    for run_id in run_ids:
        attempts, results = load(run_id)
        n += len(results)
        resolved += sum(r["resolved"] for r in results)
        for a in attempts:
            if a["label"] == "RESOLVED":
                for k in range(a["n"] - 1, 3):
                    at[k] += 1
        cost += sum(a.get("cost_usd") or 0 for a in attempts)
        seconds += sum(r.get("duration_s") or 0 for r in results)
        causes.update(r["label"] for r in results if not r["resolved"])
    return {"n": n, "resolved": resolved, "at": at, "cost_per": cost / resolved, "s_per": seconds / resolved,
            "causes": causes}


def style(ax, title: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", color=INK, fontsize=12, pad=12)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.yaxis.label.set_color(INK_2)
    ax.xaxis.label.set_color(INK_2)


def figure(width: float, height: float):
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def cost_accuracy(s: dict) -> None:
    rows = [k for k in RUNS if k != "Fine-tuned v2, local"]
    fig, ax = figure(7, 3.8)
    style(ax, "Cost and resolve rate on test (27 scenarios)")
    # Label offsets per point: the cascade and Opus sit close together at 100%.
    place = {rows[0]: ((10, -4), "left"), rows[1]: ((-12, -34), "right"), rows[2]: ((8, -34), "left")}
    for name in rows:
        m = s[name]
        x, y = m["cost_per"], m["resolved"] / m["n"]
        ax.scatter([x], [y], s=90, color=COLOUR[name], edgecolor=SURFACE, linewidth=2, zorder=3, label=name)
        # No seconds for the local model: its first run shared the GPU with another program (D20).
        note = "$0, on the laptop" if x == 0 else f"${x:.3f} per resolved"
        (dx, dy), ha = place[name]
        ax.annotate(f"{name}\n{m['resolved']}/{m['n']}, {note}", (x, y), xytext=(dx, dy),
                    textcoords="offset points", fontsize=8.5, color=INK, ha=ha)
    ax.set_xlabel("API-equivalent $ per resolved scenario (local model: $0)")
    ax.set_ylabel("Resolved")
    ax.set_ylim(0.5, 1.05)
    ax.set_xlim(-0.002, 0.034)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(OUT / "cost-accuracy.png", facecolor=SURFACE)


def repair_curve(s: dict) -> None:
    fig, ax = figure(7, 3.8)
    style(ax, "Resolved by attempt on test (repair loop, cumulative)")
    labelled = set()
    for name, m in s.items():
        ys = [k / m["n"] for k in m["at"]]
        ax.plot([1, 2, 3], ys, color=COLOUR[name], linewidth=2, marker="o", markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2, label=name, zorder=3)
        if round(ys[-1], 3) not in labelled:  # the cascade and Opus both end at 100%: one label
            labelled.add(round(ys[-1], 3))
            ax.annotate(f"{ys[-1]:.0%}", (3, ys[-1]), xytext=(8, 0), textcoords="offset points",
                        va="center", fontsize=8.5, color=INK)
    ax.text(2.0, 0.89, "the cascade's attempt 3 goes to Opus", ha="center", fontsize=8, color=INK_2)
    ax.set_xticks([1, 2, 3], ["Attempt 1", "Attempt 2", "Attempt 3"])
    ax.set_xlim(0.8, 3.4)
    ax.set_ylim(0.3, 1.05)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(OUT / "repair-curve.png", facecolor=SURFACE)


def failure_attribution(s: dict) -> None:
    rows = [k for k, m in s.items() if m["causes"]]
    causes = [c for c, _ in sum((s[k]["causes"] for k in rows), Counter()).most_common()]
    fig, ax = figure(7, 3.0)
    style(ax, "Why the local runs failed on test (54 runs per model)")
    for j, name in enumerate(rows):
        left = 0
        for i, cause in enumerate(causes):
            k = s[name]["causes"][cause]
            if not k:
                continue
            ax.barh(j, k, left=left, height=0.55, color=SERIES[i % len(SERIES)], edgecolor=SURFACE, linewidth=2,
                    label=cause if j == 0 or cause not in s[rows[0]]["causes"] else None)
            ax.text(left + k / 2, j, str(k), ha="center", va="center", fontsize=8.5, color=INK)
            left += k
    ax.set_yticks(range(len(rows)), rows)
    ax.invert_yaxis()
    ax.set_xlabel("Failed scenario runs")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.4, -0.3),
              labelcolor=INK)
    fig.tight_layout()
    fig.savefig(OUT / "failure-attribution.png", facecolor=SURFACE)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    s = {name: summary(ids) for name, ids in RUNS.items()}
    for name, m in s.items():
        print(f"{name}: {m['resolved']}/{m['n']} at {m['at']} ${m['cost_per']:.3f}/resolved "
              f"{m['s_per']:.0f} s/resolved {dict(m['causes'])}")
    cost_accuracy(s)
    repair_curve(s)
    failure_attribution(s)
    print("wrote", *sorted(p.name for p in OUT.glob("*.png")))
