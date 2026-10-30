"""Run the existing LangGraph session and map its log onto benchmark trials.

The session is the P2 agent. This module only chooses a budget, a private log
path, and a private runs directory. It does not change how the agent proposes
or how the MCP tools validate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent.agent import run_session
from agent.state import clock_period
from eda_pilot.config import ConfigurationError, Settings, load_settings
from mcp_tools.validation import FlowValidationError, list_params

from benchmarks.compare_results import build_record, make_trial


def run_agent(
    design: str,
    platform: str,
    budget: int,
    *,
    settings: Settings,
    log_path: Path,
) -> dict[str, Any]:
    """One agent session whose ORFS calls cannot exceed ``budget``."""

    if budget < 1:
        raise ValueError("budget must be at least 1")
    try:
        listed = list_params(design, platform, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return build_record(
            method="agent",
            design=design,
            platform=platform,
            budget=budget,
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
        update={
            "runs_dir": settings.runs_dir / "agent" / f"b{budget}",
            "max_runs": budget,
        }
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        session = run_session(
            design=design,
            platform=platform,
            run_budget=budget,
            settings=method_settings,
            log_path=log_path,
        )
    except (FlowValidationError, ConfigurationError) as exc:
        return build_record(
            method="agent",
            design=design,
            platform=platform,
            budget=budget,
            status="error",
            message=str(exc),
            trials=[],
            runs_completed=0,
        )
    trials = []
    for entry in session["decision_log"]:
        if entry.get("flow_status") is None:
            continue
        parameters = dict(entry.get("parameters") or {})
        trials.append(
            make_trial(
                index=len(trials) + 1,
                parameters=parameters,
                metrics=entry.get("metrics"),
                flow_status=entry.get("flow_status"),
                clock_period=clock_period(parameters, default_clock),
                runtime=entry.get("duration"),
            )
        )
    return build_record(
        method="agent",
        design=design,
        platform=platform,
        budget=budget,
        status="ok",
        message="",
        trials=trials,
        runs_completed=len(trials),
        stop_reason=session.get("stop_reason"),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark one EDA Pilot agent session.")
    parser.add_argument("--design", default="gcd")
    parser.add_argument("--platform", default="sky130hd")
    parser.add_argument("--budget", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--log", type=Path, default=None)
    args = parser.parse_args(argv)
    log_path = args.log or args.out.with_suffix(".jsonl")
    record = run_agent(
        args.design,
        args.platform,
        args.budget,
        settings=load_settings(),
        log_path=log_path,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
