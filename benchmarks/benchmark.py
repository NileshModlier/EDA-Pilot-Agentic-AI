"""Run Default, random search, AutoTuner, and the agent under the same budgets.

Default ORFS is one configuration, so it is executed once and then joined into
every budget table. The other three methods each receive the requested budget.
Designs that ``list_params`` rejects are recorded as unavailable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eda_pilot.config import REPO_ROOT, ConfigurationError, Settings, load_settings
from mcp_tools.metrics import get_metrics
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError, list_params

from benchmarks.compare_results import METHODS, build_record, compare, make_trial, render
from benchmarks.run_agent import run_agent
from benchmarks.run_autotuner import run_autotuner
from benchmarks.run_random import run_random

TARGET_DESIGNS = ("gcd", "aes", "ibex")
TARGET_BUDGETS = (10, 20)


def run_matrix(
    designs: list[str],
    platform: str,
    budgets: list[int],
    *,
    settings: Settings,
    out_dir: Path,
    seed: int = 1,
    methods: tuple[str, ...] = METHODS,
) -> dict[str, Any]:
    """Write one JSON record per method and a comparison across budgets."""

    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for design in designs:
        records.extend(
            _design_records(
                design,
                platform,
                budgets,
                settings=settings,
                out_dir=out_dir,
                seed=seed,
                methods=methods,
            )
        )
    for record in records:
        _write_record(out_dir, record)
    comparison = compare(records)
    (out_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = render(comparison)
    (out_dir / "comparison.txt").write_text(summary, encoding="utf-8")
    return comparison


def run_default(
    design: str,
    platform: str,
    *,
    settings: Settings,
) -> dict[str, Any]:
    """One ORFS run with no parameter overrides."""

    try:
        listed = list_params(design, platform, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return build_record(
            method="default",
            design=design,
            platform=platform,
            budget=None,
            status="unavailable",
            message=str(exc),
            trials=[],
            runs_completed=0,
        )
    default_clock = next(
        (item.default for item in listed.parameters if item.name == "_SDC_CLK_PERIOD"),
        None,
    )
    method_settings = settings.model_copy(
        update={"runs_dir": settings.runs_dir / "default", "max_runs": 1}
    )
    try:
        result = run_flow(design, platform, None, settings=method_settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return build_record(
            method="default",
            design=design,
            platform=platform,
            budget=None,
            status="error",
            message=str(exc),
            trials=[],
            runs_completed=0,
        )
    metrics = None
    if result.status == "ok":
        metrics = get_metrics(result.run_id, settings=method_settings).model_dump()
    trial = make_trial(
        index=1,
        parameters={},
        metrics=metrics,
        flow_status=result.status,
        clock_period=default_clock,
        runtime=result.runtime,
    )
    return build_record(
        method="default",
        design=design,
        platform=platform,
        budget=None,
        status="ok" if result.status == "ok" else "error",
        message=result.message or "",
        trials=[trial],
        runs_completed=1,
        stop_reason="default configuration",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark EDA Pilot against default ORFS, random search, and AutoTuner."
    )
    parser.add_argument("--designs", nargs="+", default=list(TARGET_DESIGNS))
    parser.add_argument("--platform", default="sky130hd")
    parser.add_argument("--budgets", nargs="+", type=int, default=list(TARGET_BUDGETS))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "benchmarks" / "results")
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    args = parser.parse_args(argv)
    comparison = run_matrix(
        args.designs,
        args.platform,
        args.budgets,
        settings=load_settings(),
        out_dir=args.out,
        seed=args.seed,
        methods=tuple(args.methods),
    )
    print(render(comparison), end="")


def _design_records(
    design: str,
    platform: str,
    budgets: list[int],
    *,
    settings: Settings,
    out_dir: Path,
    seed: int,
    methods: tuple[str, ...],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if "default" in methods:
        records.append(run_default(design, platform, settings=settings))
    for budget in budgets:
        if "random" in methods:
            records.append(
                run_random(design, platform, budget, settings=settings, seed=seed)
            )
        if "autotuner" in methods:
            records.append(
                run_autotuner(design, platform, budget, settings=settings, seed=seed)
            )
        if "agent" in methods:
            log_path = out_dir / "logs" / f"{design}_{platform}_agent_b{budget}.jsonl"
            records.append(
                run_agent(
                    design,
                    platform,
                    budget,
                    settings=settings,
                    log_path=log_path,
                )
            )
    return records


def _write_record(out_dir: Path, record: dict[str, Any]) -> None:
    budget = record["budget"]
    label = "base" if budget is None else f"b{budget}"
    path = out_dir / f"{record['design']}_{record['platform']}_{record['method']}_{label}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
