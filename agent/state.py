"""Shared state for the ORFS LangGraph loop."""

from __future__ import annotations

from typing import Any, TypedDict


OBJECTIVE = (
    "Smallest _SDC_CLK_PERIOD that satisfies DRC count = 0, "
    "setup WNS >= 0, and hold WNS >= 0."
)
CLOCK_PARAMETER = "_SDC_CLK_PERIOD"
CONVERGENCE_GAP = 0.05


class AgentState(TypedDict):
    design: str
    platform: str
    objective: str
    run_budget: int
    remaining_runs: int
    history: list[dict[str, Any]]
    current_metrics: dict[str, Any] | None
    best_run: dict[str, Any] | None
    decision_log: list[dict[str, Any]]
    iteration: int
    diagnosis: str
    proposal: dict[str, Any] | None
    validation_result: str
    validation_message: str
    validation_attempts: int
    accepted_params: dict[str, float]
    last_run_id: str | None
    last_status: str | None
    last_runtime: float | None
    run_message: str
    ran_this_iteration: bool
    report_summaries: dict[str, str]
    clock_low: float
    clock_high: float
    catalog: list[dict[str, Any]]
    stop_reason: str
    advisor: str
    proposal_error: str


def signoff_passed(metrics: dict[str, Any] | None, flow_status: str | None) -> bool:
    """Pass only a clean, finished flow with non-negative setup and hold slack."""

    if flow_status != "ok" or metrics is None:
        return False
    drc = metrics.get("drc_count")
    setup = metrics.get("setup_wns")
    hold = metrics.get("hold_wns")
    if drc is None or setup is None or hold is None:
        return False
    return drc == 0 and setup >= 0 and hold >= 0


def clock_period(parameters: dict[str, float], default: float | None) -> float | None:
    if CLOCK_PARAMETER in parameters:
        return float(parameters[CLOCK_PARAMETER])
    return default


def is_better_run(candidate: dict[str, Any], incumbent: dict[str, Any] | None) -> bool:
    """Prefer a passing run, then the smaller passing clock, then closer slack."""

    if incumbent is None:
        return True
    if candidate["passed"] != incumbent["passed"]:
        return bool(candidate["passed"])
    if candidate["passed"] and incumbent["passed"]:
        return _clock_or_inf(candidate) < _clock_or_inf(incumbent)
    return _failure_key(candidate) < _failure_key(incumbent)


def _clock_or_inf(run: dict[str, Any]) -> float:
    clock = run.get("clock_period")
    if clock is None:
        return 1e9
    return float(clock)


def _failure_key(run: dict[str, Any]) -> tuple[float, float, float]:
    metrics = run.get("metrics") or {}
    drc = metrics.get("drc_count")
    setup = metrics.get("setup_wns")
    hold = metrics.get("hold_wns")
    return (
        float(drc) if drc is not None else 1e9,
        -(float(setup) if setup is not None else -1e9),
        -(float(hold) if hold is not None else -1e9),
    )
