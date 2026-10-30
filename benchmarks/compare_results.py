"""Score benchmark trials on the shared signoff objective.

The primary objective is the smallest clock period whose flow finished with
DRC = 0, setup WNS >= 0, and hold WNS >= 0. Area, power, and runtime are
reported for that trial. They break ties only when two passing clocks match.
Failing runs are compared on setup slack, then DRC, then hold slack.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PRIMARY_OBJECTIVE = (
    "Smallest clock period with DRC = 0, setup WNS >= 0, and hold WNS >= 0."
)
METHODS = ("default", "random", "autotuner", "agent")


def make_trial(
    *,
    index: int,
    parameters: dict[str, float],
    metrics: dict[str, Any] | None,
    flow_status: str | None,
    clock_period: float | None,
    runtime: float | None,
) -> dict[str, Any]:
    """One finished or attempted flow, with the fields the comparison reads."""

    from agent.state import signoff_passed

    metric_view = _metric_view(metrics)
    measured = runtime if runtime is not None else metric_view.get("runtime")
    return {
        "index": index,
        "parameters": parameters,
        "metrics": metric_view,
        "flow_status": flow_status,
        "passed": signoff_passed(metric_view, flow_status),
        "clock_period": clock_period,
        "area": metric_view.get("area"),
        "power": metric_view.get("power"),
        "runtime": measured,
        "drc_count": metric_view.get("drc_count"),
        "setup_wns": metric_view.get("setup_wns"),
        "hold_wns": metric_view.get("hold_wns"),
    }


def select_best(trials: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the trial with the lowest primary key. Equal keys keep the earlier trial."""

    best: dict[str, Any] | None = None
    for trial in trials:
        if best is None or _primary_key(trial) < _primary_key(best):
            best = trial
    return best


def build_record(
    *,
    method: str,
    design: str,
    platform: str,
    budget: int | None,
    status: str,
    message: str,
    trials: list[dict[str, Any]],
    runs_completed: int,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    """A method result. ``best`` is omitted unless the method actually ran."""

    best = select_best(trials) if status == "ok" and trials else None
    return {
        "method": method,
        "design": design,
        "platform": platform,
        "budget": budget,
        "status": status,
        "message": message,
        "runs_completed": runs_completed,
        "stop_reason": stop_reason,
        "trials": trials,
        "best": best,
    }


def compare(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Join default (run once) into every budget and rank the four methods."""

    tables: list[dict[str, Any]] = []
    groups = _design_groups(records)
    for design, platform in groups:
        group = groups[(design, platform)]
        budgets = sorted({item["budget"] for item in group if item["budget"] is not None})
        baseline = next((item for item in group if item["method"] == "default"), None)
        for budget in budgets:
            rows = []
            for method in METHODS:
                if method == "default":
                    record = baseline
                else:
                    record = next(
                        (
                            item
                            for item in group
                            if item["method"] == method and item["budget"] == budget
                        ),
                        None,
                    )
                rows.append(_row(method, record))
            tables.append(
                {
                    "design": design,
                    "platform": platform,
                    "budget": budget,
                    "rows": rows,
                    "finding": _finding(rows),
                }
            )
    return {"objective": PRIMARY_OBJECTIVE, "tables": tables}


def render(comparison: dict[str, Any]) -> str:
    """Plain-text report for the console and for a saved summary."""

    lines = [comparison["objective"], ""]
    if not comparison["tables"]:
        lines.append("No completed budget tables.")
        return "\n".join(lines)
    for table in comparison["tables"]:
        lines.append(
            f"{table['design']} / {table['platform']} / budget {table['budget']}"
        )
        for row in table["rows"]:
            lines.append(f"  {_format_row(row)}")
        lines.append(f"  {table['finding']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records.extend(payload)
        elif isinstance(payload, dict) and "tables" in payload:
            continue
        else:
            records.append(payload)
    return records


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare Default, random search, AutoTuner, and EDA Pilot."
    )
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    comparison = compare(load_records(args.results))
    text = render(comparison)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
        args.out.with_suffix(".txt").write_text(text, encoding="utf-8")
    print(text, end="")


def _metric_view(metrics: dict[str, Any] | None) -> dict[str, Any]:
    if not metrics:
        return {}
    keys = (
        "setup_wns",
        "setup_tns",
        "hold_wns",
        "hold_tns",
        "power",
        "area",
        "utilization",
        "drc_count",
        "runtime",
    )
    return {key: metrics.get(key) for key in keys}


def _primary_key(trial: dict[str, Any]) -> tuple[Any, ...]:
    area = _ascending(trial.get("area"))
    power = _ascending(trial.get("power"))
    runtime = _ascending(trial.get("runtime"))
    if trial.get("passed"):
        clock = _ascending(trial.get("clock_period"))
        return (0, clock, area, power, runtime)
    setup = trial.get("setup_wns")
    setup_key = -(setup if isinstance(setup, (int, float)) else -1e9)
    drc = _ascending(trial.get("drc_count"))
    hold = trial.get("hold_wns")
    hold_key = -(hold if isinstance(hold, (int, float)) else -1e9)
    return (1, setup_key, drc, hold_key)


def _ascending(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 1e18


def _design_groups(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["design"], record["platform"])
        groups.setdefault(key, []).append(record)
    return groups


def _row(method: str, record: dict[str, Any] | None) -> dict[str, Any]:
    if record is None:
        return {
            "method": method,
            "status": "unavailable",
            "message": "No result file for this method.",
            "runs_completed": 0,
            "best": None,
        }
    return {
        "method": method,
        "status": record["status"],
        "message": record.get("message") or "",
        "runs_completed": record.get("runs_completed", 0),
        "stop_reason": record.get("stop_reason"),
        "best": record.get("best"),
    }


def _finding(rows: list[dict[str, Any]]) -> str:
    completed = [row for row in rows if row["status"] == "ok" and row.get("best")]
    missing = [row["method"] for row in rows if row["status"] != "ok"]
    if not completed:
        return "No method completed a flow, so the primary objective is unresolved."
    ordered = sorted(
        completed,
        key=lambda row: (_primary_key(row["best"]), METHODS.index(row["method"])),
    )
    leader = ordered[0]
    tied = [
        row["method"]
        for row in ordered
        if _primary_key(row["best"]) == _primary_key(leader["best"])
    ]
    note = ""
    if missing:
        note = " Unavailable methods are " + ", ".join(missing) + "."
    if len(tied) == len(completed):
        return (
            "The completed methods are tied on the primary objective and on "
            "area, power, and runtime."
            + note
        )
    best = leader["best"]
    if best.get("passed"):
        return (
            f"{leader['method']} has the smallest passing clock, "
            f"{best['clock_period']} ns."
            + note
        )
    return (
        f"{leader['method']} is closest on failing slack and DRC. "
        "No completed method met signoff."
        + note
    )


def _format_row(row: dict[str, Any]) -> str:
    if row["status"] != "ok" or not row.get("best"):
        detail = row.get("message") or row["status"]
        return f"{row['method']}: {row['status']} ({detail})"
    best = row["best"]
    signoff = "yes" if best.get("passed") else "no"
    return (
        f"{row['method']}: {row['runs_completed']} runs, signoff {signoff}, "
        f"clock {best.get('clock_period')}, setup {best.get('setup_wns')}, "
        f"hold {best.get('hold_wns')}, DRC {best.get('drc_count')}, "
        f"area {best.get('area')}, power {best.get('power')}, "
        f"runtime {best.get('runtime')}"
    )


if __name__ == "__main__":
    main()
