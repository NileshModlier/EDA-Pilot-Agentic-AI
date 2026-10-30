"""Re-draw the EDA Pilot AI release plots from the finalized results file.

This script reads results and writes PNGs. It never runs a flow and adds no
benchmark data.

usage:
    python scripts/make_release_plots.py [results.json] [out_dir]

defaults: results/final_benchmark_results.json and plots/, relative to the
repository root. Requires matplotlib. Uses the Inter font when it is installed
and falls back to DejaVu Sans otherwise.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Patch
from matplotlib.lines import Line2D
from matplotlib.path import Path as MPath

REPO = Path(__file__).resolve().parent.parent
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "final_benchmark_results.json"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "plots"
with open(RESULTS, encoding="utf-8") as handle:
    SRC = json.load(handle)
OUT.mkdir(parents=True, exist_ok=True)

# ---- tokens (reference palette, light mode; validated: 3 slots, all pairs) ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#85837d"
GRID = "#e8e7e2"
BASE = "#bdbbb3"
COL = {"agent": "#2a78d6", "random": "#eb6834", "default": "#1baf7a"}
NAME = {"agent": "EDA Pilot agent", "random": "Random search", "default": "Default ORFS"}
ORDER = ["default", "random", "agent"]
DESIGNS = ["gcd", "aes", "ibex"]
DNAME = {"gcd": "gcd", "aes": "aes", "ibex": "ibex"}
FOOT = "Source: results/final_benchmark_results.json  ·  sky130hd  ·  budget 10  ·  seed 1"

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": BASE, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "hatch.linewidth": 1.1,
})

runs = SRC["runs"]


def trials(design, method):
    return [r for r in runs if r["design"] == design and r["method"] == method]


def best(design, method):
    rr = trials(design, method)
    so = [r for r in rr if r["signoff"]]
    return (min(so, key=lambda r: r["clock_period_ns"]), True) if so else (rr[0], False)


# ---------------------------------------------------------------- helpers
def figure(w=8.0, h=4.6):
    return plt.figure(figsize=(w, h), dpi=200)


def header(fig, title, subtitle):
    fig.text(0.04, 0.955, title, fontsize=14.5, fontweight="bold", color=INK, va="top")
    fig.text(0.04, 0.895, subtitle, fontsize=9.6, color=INK2, va="top")
    fig.text(0.04, 0.03, FOOT, fontsize=7.6, color=MUTED, va="bottom")


def legend(fig, methods, extra=None, y=0.955, x=0.96):
    handles = [Patch(facecolor=COL[m], edgecolor="none", label=NAME[m]) for m in methods]
    if extra:
        handles += extra
    lg = fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(x, y), ncol=len(handles), frameon=False,
                    fontsize=8.6, handlelength=1.1, handleheight=1.1, columnspacing=1.3, handletextpad=0.5)
    for t in lg.get_texts():
        t.set_color(INK2)
    return lg


def style_axis(ax, ygrid=True):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.spines["bottom"].set_linewidth(1)
    ax.tick_params(axis="both", length=0, labelsize=8.6)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)


def rbar(ax, x, h, w, color, hatch=None, radius_px=4.0, base=0.0, horizontal=False):
    """Bar with a 4px rounded data-end and a square baseline end."""
    fig = ax.figure
    bbox = ax.get_window_extent()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    px = fig.dpi / 72.0 * radius_px * 0.75  # 4 css px ~ 3pt
    if horizontal:
        # x is the row position (y in data), h the value along x
        ry = px * (y1 - y0) / bbox.height
        rx = px * (x1 - x0) / bbox.width
        top = base + h
        sgn = 1 if h >= 0 else -1
        rx = min(rx, abs(h) / 2)
        ry = min(ry, w / 2)
        yb, yt = x - w / 2, x + w / 2
        verts = [(base, yb), (top - sgn * rx, yb), (top, yb), (top, yb + ry), (top, yt - ry), (top, yt), (top - sgn * rx, yt), (base, yt), (base, yb)]
    else:
        rx = px * (x1 - x0) / bbox.width
        ry = px * (y1 - y0) / bbox.height
        top = base + h
        sgn = 1 if h >= 0 else -1
        ry = min(ry, abs(h) / 2) if h != 0 else 0
        rx = min(rx, w / 2)
        xl, xr = x - w / 2, x + w / 2
        verts = [(xl, base), (xl, top - sgn * ry), (xl, top), (xl + rx, top), (xr - rx, top), (xr, top), (xr, top - sgn * ry), (xr, base), (xl, base)]
    codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CLOSEPOLY]
    patch = PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", linewidth=0)
    ax.add_patch(patch)
    if hatch:
        hp = PathPatch(MPath(verts, codes), facecolor="none", edgecolor=SURFACE, linewidth=0, hatch=hatch)
        ax.add_patch(hp)
    return patch


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", name)


NOSIGN = Patch(facecolor=COL["default"], edgecolor=SURFACE, hatch="////", label="hatched = no signoff")


def small_multiples(metric, title, subtitle, unit_label, fmt, scale=1.0, name=None, note=None):
    fig = figure(8.0, 4.4)
    header(fig, title, subtitle)
    legend(fig, ORDER, [NOSIGN], y=0.845, x=0.965)
    axes = [fig.add_axes([0.07 + i * 0.31, 0.15, 0.25, 0.52]) for i in range(3)]
    for ax, ds in zip(axes, DESIGNS):
        vals = []
        for m in ORDER:
            r, ok = best(ds, m)
            vals.append((m, r[metric] * scale, ok))
        top = max(v for _, v, _ in vals) * 1.22
        ax.set_xlim(-0.6, 2.6)
        ax.set_ylim(0, top)
        style_axis(ax)
        for i, (m, v, ok) in enumerate(vals):
            rbar(ax, i, v, 0.56, COL[m], hatch=None if ok else "////")
            ax.text(i, v + top * 0.02, fmt(v), ha="center", va="bottom", fontsize=8.4, color=INK, fontweight="semibold")
        ax.set_xticks(range(3))
        ax.set_xticklabels(["Default", "Random", "Agent"], fontsize=8.4)
        ax.set_title(DNAME[ds], loc="left", fontsize=11, fontweight="bold", color=INK, pad=8)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: compact(v)))
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4))
    axes[0].set_ylabel(unit_label, fontsize=8.6)
    if note:
        fig.text(0.965, 0.03, note, fontsize=7.6, color=MUTED, va="bottom", ha="right")
    save(fig, name)


def compact(v):
    if abs(v) >= 1000:
        s = f"{v/1000:.0f}K" if abs(v) >= 10000 else f"{v/1000:.1f}K"
        return s.replace(".0K", "K")
    if v == int(v):
        return f"{int(v)}"
    return f"{v:g}"


# ---------------------------------------------------------------- 1. leaderboard
def leaderboard():
    fig = figure(8.0, 4.7)
    header(fig, "Smallest passing clock period",
           "Signoff = DRC 0, setup WNS ≥ 0, hold WNS ≥ 0. Lower is better. Default ORFS never signed off.")
    target = Line2D([0], [0], marker="D", color="none", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=6.5,
                    label="Default target (fails setup)")
    legend(fig, ["random", "agent"], [target], y=0.835, x=0.965)
    ax = fig.add_axes([0.1, 0.15, 0.84, 0.6])
    rows = []
    for k, ds in enumerate(DESIGNS):
        ra, _ = best(ds, "random")
        ag, _ = best(ds, "agent")
        dflt = SRC.get("ibex_default_sdc_period_ns") if ds == "ibex" else best(ds, "default")[0]["clock_period_ns"]
        rows.append((ds, ra["clock_period_ns"], ag["clock_period_ns"], dflt))
    ax.set_xlim(0, 13.4)
    ax.set_ylim(-0.6, 2.6)
    style_axis(ax, ygrid=False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(BASE)
    h = 0.3
    for k, (ds, rv, av, dv) in enumerate(rows):
        y = 2 - k
        rbar(ax, y + 0.17, rv, h, COL["random"], horizontal=True)
        rbar(ax, y - 0.17, av, h, COL["agent"], horizontal=True)
        ax.text(rv + 0.12, y + 0.17, f"{rv:.3f} ns", va="center", fontsize=8.4, color=INK2)
        ax.text(av + 0.12, y - 0.17, f"{av:.3f} ns", va="center", fontsize=8.4, color=INK, fontweight="semibold")
        gain = 100 * (rv - av) / rv
        ax.text(13.35, y, f"−{gain:.1f}%", va="center", ha="right", fontsize=12.5, fontweight="bold", color=INK)
        ax.text(13.35, y - 0.3, "tighter than random", va="center", ha="right", fontsize=7.4, color=MUTED)
        ax.plot([dv, dv], [y - 0.4, y + 0.4], color=INK2, linewidth=1.2, linestyle=(0, (2, 2)), zorder=5)
        ax.plot([dv], [y + 0.4], marker="D", markersize=6.5, markerfacecolor=SURFACE, markeredgecolor=INK2, markeredgewidth=1.4, zorder=6)
        ax.text(dv + 0.14, y + 0.4, f"default {dv:g} ns", ha="left", va="center", fontsize=7.4, color=MUTED)
    ax.set_yticks([2, 1, 0])
    ax.set_yticklabels([r[0] for r in rows], fontsize=11, fontweight="bold", color=INK)
    ax.set_xlabel("Clock period (ns)", fontsize=8.6)
    ax.set_xticks(range(0, 12, 2))
    save(fig, "leaderboard_summary.png")


# ---------------------------------------------------------------- 2. success rate
def success_rate():
    fig = figure(8.0, 4.6)
    header(fig, "Signoff rate per method", "Signoff runs ÷ scored runs. Labels show the count; the IBEX agent rate is a single run.")
    legend(fig, ORDER, y=0.835, x=0.965)
    ax = fig.add_axes([0.08, 0.15, 0.88, 0.58])
    groups = DESIGNS + ["pooled"]
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylim(0, 118)
    style_axis(ax)
    w = 0.22
    for g, ds in enumerate(groups):
        for j, m in enumerate(ORDER):
            if ds == "pooled":
                so = sum(1 for r in runs if r["method"] == m and r["signoff"])
                n = sum(1 for r in runs if r["method"] == m)
            else:
                rr = trials(ds, m)
                so, n = sum(1 for r in rr if r["signoff"]), len(rr)
            v = 100 * so / n
            x = g + (j - 1) * (w + 0.02)
            if v > 0:
                rbar(ax, x, v, w, COL[m])
            else:
                ax.plot([x - w / 2, x + w / 2], [0.6, 0.6], color=COL[m], linewidth=2.2, solid_capstyle="butt")
            ax.text(x, v + 2.2, f"{so}/{n}", ha="center", va="bottom", fontsize=8.2, color=INK, fontweight="semibold")
            if ds == "ibex" and m == "agent":
                ax.text(x, v + 9.2, "n = 1", ha="center", va="bottom", fontsize=7.2, color=MUTED, style="italic")
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(["gcd", "aes", "ibex", "All designs"], fontsize=10, fontweight="bold", color=INK)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.axvline(2.5, color=GRID, linewidth=1)
    save(fig, "success_rate_comparison.png")


# ---------------------------------------------------------------- 3-4-5. QoR small multiples
def area():
    small_multiples("area", "Area at the best passing clock",
                    "Best signoff run per method; Default is its single run, which missed setup (hatched).",
                    "Instance area (µm²)", lambda v: f"{v:,.0f}", name="area_comparison.png",
                    note="Random signs off at a slower clock, so it needs less area.")


def power():
    small_multiples("power", "Total power at the best passing clock",
                    "Best signoff run per method; Default is its single run, which missed setup (hatched).",
                    "Total power (mW)", lambda v: f"{v:,.1f}" if v < 100 else f"{v:,.0f}", scale=1000.0, name="power_comparison.png",
                    note="Power rises with the tighter agent clock.")


def runtime():
    small_multiples("runtime_s", "Flow runtime of the best passing run",
                    "Wall-clock time of one ORFS finish run. Default is its single run (hatched).",
                    "Runtime (minutes)", lambda v: f"{v:,.1f}" if v < 10 else f"{v:,.0f}", scale=1 / 60.0, name="runtime_comparison.png",
                    note="Agent ÷ random: 1.47× gcd, 1.65× aes, 5.53× ibex.")


# ---------------------------------------------------------------- 6-7. slack
def slack(metric, title, subtitle, name):
    fig = figure(8.0, 4.6)
    header(fig, title, subtitle)
    legend(fig, ORDER, [NOSIGN], y=0.835, x=0.965)
    ax = fig.add_axes([0.09, 0.15, 0.87, 0.58])
    vals = {(ds, m): best(ds, m) for ds in DESIGNS for m in ORDER}
    lo = min(0, min(r[metric] for r, _ in vals.values()))
    hi = max(r[metric] for r, _ in vals.values())
    pad = (hi - lo) * 0.16
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(lo - (pad if lo < 0 else 0), hi + pad)
    style_axis(ax)
    w = 0.24
    for g, ds in enumerate(DESIGNS):
        for j, m in enumerate(ORDER):
            r, ok = vals[(ds, m)]
            v = r[metric]
            x = g + (j - 1) * (w + 0.02)
            rbar(ax, x, v, w, COL[m], hatch=None if ok else "////")
            lab = f"{v:+.3f}" if abs(v) >= 0.001 else f"{v:+.5f}"
            off = (hi - lo) * 0.025
            ax.text(x, v + (off if v >= 0 else -off), lab, ha="center", va="bottom" if v >= 0 else "top", fontsize=7.8, color=INK,
                    fontweight="semibold")
    ax.axhline(0, color=INK2, linewidth=1)
    ax.set_xticks(range(3))
    ax.set_xticklabels(DESIGNS, fontsize=10.5, fontweight="bold", color=INK)
    ax.spines["bottom"].set_visible(False)
    ax.set_ylabel(f"{'Setup' if 'setup' in metric else 'Hold'} WNS (ns)", fontsize=8.6)
    save(fig, name)


# ---------------------------------------------------------------- 8. search trajectory
def trajectory():
    fig = figure(8.0, 4.7)
    header(fig, "How each method spent its 10-run budget",
           "Clock period tried at every scored run. Filled = signoff, hollow = finished but missed timing, × = flow error or timeout.")
    h = [Line2D([0], [0], color=COL["agent"], marker="o", markersize=6, linewidth=2, label="EDA Pilot agent"),
         Line2D([0], [0], color="none", marker="o", markerfacecolor=COL["random"], markeredgecolor=COL["random"], markersize=6, label="Random search"),
         Line2D([0], [0], color=MUTED, linestyle=(0, (3, 2)), linewidth=1.2, label="Default target")]
    lg = fig.legend(handles=h, loc="upper right", bbox_to_anchor=(0.965, 0.845), ncol=3, frameon=False, fontsize=8.6)
    for t in lg.get_texts():
        t.set_color(INK2)
    axes = [fig.add_axes([0.07 + i * 0.31, 0.15, 0.255, 0.52]) for i in range(3)]
    for ax, ds in zip(axes, DESIGNS):
        style_axis(ax)
        ax.xaxis.grid(False)
        allc = [r["clock_period_ns"] for r in runs if r["design"] == ds and r["clock_period_ns"] is not None]
        dflt = SRC.get("ibex_default_sdc_period_ns") if ds == "ibex" else best(ds, "default")[0]["clock_period_ns"]
        allc.append(dflt)
        lo, hi = min(allc), max(allc)
        pad = (hi - lo) * 0.12
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_xlim(0.4, 10.6)
        ax.axhline(dflt, color=MUTED, linestyle=(0, (3, 2)), linewidth=1.1)
        for m, z in (("random", 3), ("agent", 4)):
            tt = trials(ds, m)
            xs = [r["index"] for r in tt]
            ys = [r["clock_period_ns"] for r in tt]
            c = COL[m]
            if m == "agent":
                ax.plot(xs, ys, color=c, linewidth=2, solid_joinstyle="round", solid_capstyle="round", zorder=z)
            for r in tt:
                x, y = r["index"], r["clock_period_ns"]
                if r["outcome"] in ("flow_error", "timeout"):
                    ax.plot([x], [y], marker="x", markersize=6.5, markeredgewidth=1.8, color=c, zorder=z + 1)
                elif r["signoff"]:
                    ax.plot([x], [y], marker="o", markersize=6.5, markerfacecolor=c, markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=z + 1)
                else:
                    ax.plot([x], [y], marker="o", markersize=6, markerfacecolor=SURFACE, markeredgecolor=c, markeredgewidth=1.6, zorder=z + 1)
        b, _ = best(ds, "agent")
        early = b["index"] <= 2
        ax.annotate(f"best {b['clock_period_ns']:g} ns", (b["index"], b["clock_period_ns"]), xytext=(8, 4) if early else (0, 11), textcoords="offset points",
                    ha="left" if early else "center", fontsize=7.6, color=INK, fontweight="semibold", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.18", fc=SURFACE, ec="none", alpha=0.92))
        ax.set_title(ds, loc="left", fontsize=11, fontweight="bold", color=INK, pad=8)
        ax.set_xticks([1, 5, 10])
        ax.set_xlabel("Run", fontsize=8.4)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
    axes[0].set_ylabel("Clock period (ns)", fontsize=8.6)
    save(fig, "search_trajectory.png")


leaderboard()
success_rate()
area()
power()
runtime()
slack("setup_wns", "Setup slack (WNS) of the best passing run",
      "Above zero meets setup. Default ORFS (hatched) misses setup on every design.", "setup_wns_comparison.png")
slack("hold_wns", "Hold slack (WNS) of the best passing run",
      "Above zero meets hold. Every best run, including the failing defaults, holds positive slack.", "hold_wns_comparison.png")
trajectory()
