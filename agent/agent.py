"""LangGraph loop for unattended ORFS design-space decisions.

analyse and propose may call a chat model. validate, run, and check are code.
The model cannot execute commands, invent metrics, or skip validation.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from agent.proposal_models import Diagnosis, ParameterChange, Proposal
from agent.state import (
    CLOCK_PARAMETER,
    CONVERGENCE_GAP,
    OBJECTIVE,
    AgentState,
    clock_period,
    is_better_run,
    signoff_passed,
)
from eda_pilot.config import REPO_ROOT, ConfigurationError, Settings, load_settings
from mcp_tools.metrics import get_metrics
from mcp_tools.reports import read_report
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError, list_params, validate_params

Diagnoser = Callable[[AgentState], str]
Proposer = Callable[[AgentState], Proposal]

SYSTEM_PROMPT = """You are the diagnosis and proposal stage of an OpenROAD Flow Scripts agent.
You may only diagnose the metrics and report tails you are given, and propose at most 3 parameter changes.
You must not execute commands, invent metrics, or override validation.
Use only catalog parameters whose executable field is true.
Every new value must lie inside that parameter's minimum and maximum.
If validation_message is set, discard the rejected value and propose a legal one.
Do not propose _FR_LAYER_ADJUST.
The objective is the smallest _SDC_CLK_PERIOD with DRC count 0, setup WNS >= 0, and hold WNS >= 0.
"""


def run_session(
    *,
    design: str = "gcd",
    platform: str = "sky130hd",
    run_budget: int = 10,
    settings: Settings | None = None,
    diagnoser: Diagnoser | None = None,
    proposer: Proposer | None = None,
    log_path: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the analyse-propose-validate-run-check loop until it stops."""

    active = settings or load_settings()
    if run_budget < 1:
        raise ConfigurationError("validation error: run_budget must be at least 1")
    if run_budget > active.max_runs:
        raise ConfigurationError(
            "validation error: agent run_budget "
            f"{run_budget} exceeds the server run budget {active.max_runs}. "
            "Set EDA_PILOT_MAX_RUNS at least as high as the agent budget."
        )
    catalog = list_params(design, platform, settings=active)
    knobs = [item.model_dump() for item in catalog.parameters]
    clock = _knob(knobs, CLOCK_PARAMETER)
    if clock is None or not clock["executable"]:
        raise ConfigurationError(
            "validation error: _SDC_CLK_PERIOD is not an executable parameter"
        )
    destination = log_path or (active.runs_dir / "decision_log.jsonl")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("", encoding="utf-8")

    if diagnoser is None or proposer is None:
        loaded_diagnoser, loaded_proposer, advisor = load_advisor(model)
        diagnoser = diagnoser or loaded_diagnoser
        proposer = proposer or loaded_proposer
    else:
        advisor = "injected"

    graph = build_graph(active, diagnoser, proposer, destination)
    final = graph.invoke(
        _initial_state(
            design=design,
            platform=platform,
            run_budget=run_budget,
            knobs=knobs,
            clock=clock,
            advisor=advisor,
        ),
        {"recursion_limit": 250},
    )
    return {
        "stop_reason": final["stop_reason"],
        "iterations": len(final["decision_log"]),
        "best_run": final["best_run"],
        "decision_log": final["decision_log"],
        "log_path": str(destination),
        "advisor": advisor,
        "remaining_runs": final["remaining_runs"],
    }


def build_graph(
    settings: Settings,
    diagnoser: Diagnoser,
    proposer: Proposer,
    log_path: Path,
):
    """Compile the five-node loop. Routing after validate and check is code."""

    def analyse(state: AgentState) -> dict[str, Any]:
        summaries = _read_summaries(state, settings)
        diagnosed = _call_diagnoser(diagnoser, {**state, "report_summaries": summaries})
        return {
            "iteration": state["iteration"] + 1,
            "diagnosis": diagnosed,
            "report_summaries": summaries,
            "validation_attempts": 0,
            "validation_result": "",
            "validation_message": "",
            "ran_this_iteration": False,
            "run_message": "",
        }

    def propose(state: AgentState) -> dict[str, Any]:
        try:
            proposal = proposer(state)
            checked = Proposal.model_validate(proposal.model_dump())
        except Exception as exc:
            return {"proposal": None, "proposal_error": str(exc)}
        return {"proposal": checked.model_dump(), "proposal_error": ""}

    def validate(state: AgentState) -> dict[str, Any]:
        attempts = state["validation_attempts"] + 1
        if state["remaining_runs"] <= 0:
            return _validation_fail(attempts, "validation error: run budget exceeded")
        proposal = state["proposal"]
        if not proposal:
            return _validation_fail(attempts, "validation error: proposal is empty")
        try:
            parsed = Proposal.model_validate(proposal)
        except Exception as exc:
            return _validation_fail(attempts, f"validation error: {exc}")
        if not parsed.changes:
            return _validation_fail(attempts, "validation error: proposal has no changes")
        merged, duplicate = _merge_changes(state["accepted_params"], parsed)
        if duplicate:
            return _validation_fail(
                attempts,
                f"validation error: duplicate parameter '{duplicate}'",
            )
        try:
            validated = validate_params(
                state["design"],
                state["platform"],
                merged,
                settings=settings,
            )
        except FlowValidationError as exc:
            return _validation_fail(attempts, str(exc))
        return {
            "validation_attempts": attempts,
            "validation_result": "ok",
            "validation_message": "",
            "accepted_params": validated.recorded_params,
        }

    def run(state: AgentState) -> dict[str, Any]:
        try:
            started = run_flow(
                state["design"],
                state["platform"],
                state["accepted_params"],
                settings=settings,
            )
        except FlowValidationError as exc:
            return {
                "ran_this_iteration": True,
                "remaining_runs": state["remaining_runs"] - 1,
                "last_status": "error",
                "last_runtime": 0.0,
                "last_run_id": None,
                "current_metrics": None,
                "run_message": str(exc),
            }
        metrics = _metrics_for(started.run_id, settings)
        return {
            "ran_this_iteration": True,
            "remaining_runs": state["remaining_runs"] - 1,
            "last_status": started.status,
            "last_runtime": started.runtime,
            "last_run_id": started.run_id,
            "current_metrics": metrics,
            "run_message": started.message or "",
        }

    def check(state: AgentState) -> dict[str, Any]:
        if not state["ran_this_iteration"]:
            record = _log_record(state, passed=False, metrics=None, run_id=None)
            record["parameters"] = _rejected_parameters(state)
            record["duration"] = None
            record["flow_status"] = None
            record["validation_message"] = state["validation_message"]
            return _finish_iteration(
                state,
                record,
                log_path,
                stop_reason="proposal rejected by validation",
                clock_low=state["clock_low"],
                clock_high=state["clock_high"],
                best_run=state["best_run"],
            )
        metrics = state["current_metrics"]
        passed = signoff_passed(metrics, state["last_status"])
        record = _log_record(
            state,
            passed=passed,
            metrics=metrics,
            run_id=state["last_run_id"],
        )
        best = _consider_best(state, record, passed)
        low, high = _update_clock_bounds(state, record["parameters"], passed, metrics)
        stop = ""
        if state["remaining_runs"] <= 0:
            stop = "run budget exhausted"
        elif best is not None and best["passed"] and (high - low) < CONVERGENCE_GAP:
            stop = "clock search converged"
        return _finish_iteration(
            state,
            record,
            log_path,
            stop_reason=stop,
            clock_low=low,
            clock_high=high,
            best_run=best,
        )

    graph = StateGraph(AgentState)
    graph.add_node("analyse", analyse)
    graph.add_node("propose", propose)
    graph.add_node("validate", validate)
    graph.add_node("run", run)
    graph.add_node("check", check)
    graph.add_edge(START, "analyse")
    graph.add_edge("analyse", "propose")
    graph.add_edge("propose", "validate")
    graph.add_conditional_edges(
        "validate",
        _route_after_validate,
        {"run": "run", "propose": "propose", "check": "check"},
    )
    graph.add_edge("run", "check")
    graph.add_conditional_edges(
        "check",
        _route_after_check,
        {"analyse": "analyse", "end": END},
    )
    return graph.compile()


def load_advisor(model_name: str | None) -> tuple[Diagnoser, Proposer, str]:
    """Use a chat model when one is named. Otherwise use the offline search."""

    selected = model_name if model_name is not None else os.environ.get("EDA_PILOT_MODEL", "")
    selected = selected.strip()
    if not selected:
        return diagnose_offline, propose_offline, "offline"
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise ConfigurationError(
            "validation error: EDA_PILOT_MODEL is set but langchain is not installed"
        ) from exc
    chat = init_chat_model(selected)
    return _llm_diagnoser(chat), _llm_proposer(chat), "llm"


def diagnose_offline(state: AgentState) -> str:
    """Describe only metrics and report tails already stored in state."""

    metrics = state.get("current_metrics")
    if not metrics:
        return (
            "No completed run yet. Starting from the design default clock period "
            "and the parameter catalog."
        )
    setup = metrics.get("setup_wns")
    hold = metrics.get("hold_wns")
    drc = metrics.get("drc_count")
    if drc == 0:
        drc_text = "DRC is clean"
    elif drc is None:
        drc_text = "DRC was not reported"
    else:
        drc_text = f"DRC count is {drc:g}"
    if setup is not None and setup < 0:
        text = f"Timing failing because setup WNS is {setup:.3f} ns while {drc_text}."
    elif hold is not None and hold < 0:
        text = f"Timing failing because hold WNS is {hold:.3f} ns while {drc_text}."
    elif setup is not None and hold is not None and drc == 0 and setup >= 0 and hold >= 0:
        text = (
            f"Signoff targets are met with setup WNS {setup:.3f} ns "
            f"and hold WNS {hold:.3f} ns while {drc_text}."
        )
    else:
        text = f"Latest metrics are setup WNS {setup}, hold WNS {hold}, while {drc_text}."
    timing = state.get("report_summaries", {}).get("timing", "")
    if "setup slack" in timing:
        text += " The timing summary reports setup slack."
    return text


def propose_offline(state: AgentState) -> Proposal:
    """Search the legal clock range. This does not launch a flow."""

    if state.get("validation_message") and state.get("proposal"):
        return _clamp_previous(state)
    clock = _knob(state["catalog"], CLOCK_PARAMETER)
    if clock is None:
        raise FlowValidationError("validation error: clock parameter is not in the catalog")
    metrics = state.get("current_metrics")
    if not state["history"]:
        value = _clamp(float(clock["default"] if clock["default"] is not None else clock["minimum"]), clock)
        return Proposal(
            changes=[
                ParameterChange(
                    parameter=CLOCK_PARAMETER,
                    value=value,
                    reason=f"Start at the design default clock period of {value:g} ns.",
                )
            ]
        )
    low = float(state["clock_low"])
    high = float(state["clock_high"])
    last = clock_period(state["accepted_params"], clock.get("default"))
    midpoint = (low + high) / 2
    if last is not None and abs(midpoint - last) < 0.01:
        if metrics and signoff_passed(metrics, state.get("last_status")):
            midpoint = last - max(0.05, (last - low) / 2)
        else:
            midpoint = last + max(0.05, (high - last) / 2)
    value = _clamp(midpoint, clock)
    changes = [
        ParameterChange(
            parameter=CLOCK_PARAMETER,
            value=value,
            reason=_clock_reason(state, value),
        )
    ]
    drc = None if metrics is None else metrics.get("drc_count")
    if drc is not None and drc > 0:
        utilization = _relax_utilization(state)
        if utilization is not None:
            changes.append(utilization)
    return Proposal(changes=changes[:3])


def _llm_diagnoser(model: Any) -> Diagnoser:
    def diagnose(state: AgentState) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        structured = model.with_structured_output(Diagnosis)
        result = structured.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(_advisor_context(state))),
            ]
        )
        if isinstance(result, Diagnosis):
            return result.diagnosis
        if isinstance(result, dict) and result.get("diagnosis"):
            return str(result["diagnosis"])
        raise FlowValidationError("validation error: the model returned an empty diagnosis")

    return diagnose


def _llm_proposer(model: Any) -> Proposer:
    def propose(state: AgentState) -> Proposal:
        from langchain_core.messages import HumanMessage, SystemMessage

        structured = model.with_structured_output(Proposal)
        result = structured.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(_advisor_context(state))),
            ]
        )
        if isinstance(result, Proposal):
            return result
        if isinstance(result, dict):
            return Proposal.model_validate(result)
        raise FlowValidationError("validation error: the model returned an unusable proposal")

    return propose


def _advisor_context(state: AgentState) -> dict[str, Any]:
    return {
        "objective": state["objective"],
        "design": state["design"],
        "platform": state["platform"],
        "remaining_runs": state["remaining_runs"],
        "diagnosis": state.get("diagnosis", ""),
        "current_metrics": state.get("current_metrics"),
        "report_summaries": {
            name: text[-1500:]
            for name, text in state.get("report_summaries", {}).items()
        },
        "accepted_params": state.get("accepted_params", {}),
        "validation_message": state.get("validation_message", ""),
        "catalog": [
            {
                "name": item["name"],
                "type": item["type"],
                "minimum": item["minimum"],
                "maximum": item["maximum"],
                "default": item["default"],
                "executable": item["executable"],
            }
            for item in state["catalog"]
        ],
    }


def _initial_state(
    *,
    design: str,
    platform: str,
    run_budget: int,
    knobs: list[dict[str, Any]],
    clock: dict[str, Any],
    advisor: str,
) -> AgentState:
    return {
        "design": design,
        "platform": platform,
        "objective": OBJECTIVE,
        "run_budget": run_budget,
        "remaining_runs": run_budget,
        "history": [],
        "current_metrics": None,
        "best_run": None,
        "decision_log": [],
        "iteration": 0,
        "diagnosis": "",
        "proposal": None,
        "validation_result": "",
        "validation_message": "",
        "validation_attempts": 0,
        "accepted_params": {},
        "last_run_id": None,
        "last_status": None,
        "last_runtime": None,
        "run_message": "",
        "ran_this_iteration": False,
        "report_summaries": {},
        "clock_low": float(clock["minimum"]),
        "clock_high": float(clock["maximum"]),
        "catalog": knobs,
        "stop_reason": "",
        "advisor": advisor,
        "proposal_error": "",
    }


def _route_after_validate(state: AgentState) -> str:
    if state["validation_result"] == "ok":
        return "run"
    if state["validation_attempts"] < 3:
        return "propose"
    return "check"


def _route_after_check(state: AgentState) -> str:
    if state["stop_reason"] or state["remaining_runs"] <= 0:
        return "end"
    return "analyse"


def _validation_fail(attempts: int, message: str) -> dict[str, Any]:
    return {
        "validation_attempts": attempts,
        "validation_result": "fail",
        "validation_message": message,
    }


def _merge_changes(
    previous: Mapping[str, float],
    proposal: Proposal,
) -> tuple[dict[str, float], str | None]:
    merged = dict(previous)
    seen: set[str] = set()
    for change in proposal.changes:
        if change.parameter in seen:
            return merged, change.parameter
        seen.add(change.parameter)
        merged[change.parameter] = change.value
    return merged, None


def _metrics_for(run_id: str, settings: Settings) -> dict[str, Any] | None:
    try:
        return get_metrics(run_id, settings=settings).model_dump()
    except FlowValidationError:
        return None


def _read_summaries(state: AgentState, settings: Settings) -> dict[str, str]:
    run_id = state.get("last_run_id")
    if not run_id:
        return {}
    summaries: dict[str, str] = {}
    for name in ("timing", "drc", "congestion"):
        try:
            report = read_report(run_id, name, settings=settings)
        except FlowValidationError as exc:
            summaries[name] = f"unavailable: {exc}"
            continue
        summaries[name] = report.text
    return summaries


def _call_diagnoser(diagnoser: Diagnoser, state: AgentState) -> str:
    text = diagnoser(state).strip()
    if not text:
        raise FlowValidationError("validation error: diagnosis is empty")
    return text


def _log_record(
    state: AgentState,
    *,
    passed: bool,
    metrics: dict[str, Any] | None,
    run_id: str | None,
) -> dict[str, Any]:
    return {
        "iteration": state["iteration"],
        "diagnosis": state["diagnosis"],
        "proposal": state["proposal"],
        "parameters": state["accepted_params"],
        "metrics": metrics,
        "duration": state["last_runtime"],
        "result": "pass" if passed else "fail",
        "run_id": run_id,
        "flow_status": state["last_status"],
        "advisor": state["advisor"],
    }


def _finish_iteration(
    state: AgentState,
    record: dict[str, Any],
    log_path: Path,
    *,
    stop_reason: str,
    clock_low: float,
    clock_high: float,
    best_run: dict[str, Any] | None,
) -> dict[str, Any]:
    history = [*state["history"], record]
    decision_log = [*state["decision_log"], record]
    _append_log(log_path, record)
    return {
        "history": history,
        "decision_log": decision_log,
        "best_run": best_run,
        "clock_low": clock_low,
        "clock_high": clock_high,
        "stop_reason": stop_reason,
        "current_metrics": record["metrics"],
    }


def _append_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _consider_best(
    state: AgentState,
    record: dict[str, Any],
    passed: bool,
) -> dict[str, Any] | None:
    clock = _knob(state["catalog"], CLOCK_PARAMETER)
    default = None if clock is None else clock.get("default")
    candidate = {
        "iteration": record["iteration"],
        "run_id": record["run_id"],
        "parameters": record["parameters"],
        "metrics": record["metrics"],
        "clock_period": clock_period(record["parameters"], default),
        "passed": passed,
        "duration": record["duration"],
    }
    if is_better_run(candidate, state["best_run"]):
        return candidate
    return state["best_run"]


def _update_clock_bounds(
    state: AgentState,
    parameters: dict[str, float],
    passed: bool,
    metrics: dict[str, Any] | None,
) -> tuple[float, float]:
    low = float(state["clock_low"])
    high = float(state["clock_high"])
    period = parameters.get(CLOCK_PARAMETER)
    if period is None or state["last_status"] != "ok":
        return low, high
    if passed:
        return low, min(high, float(period))
    setup = None if metrics is None else metrics.get("setup_wns")
    hold = None if metrics is None else metrics.get("hold_wns")
    if (setup is not None and setup < 0) or (hold is not None and hold < 0):
        return max(low, float(period)), high
    return low, high


def _rejected_parameters(state: AgentState) -> dict[str, float]:
    proposal = state.get("proposal") or {}
    rejected: dict[str, float] = {}
    for change in proposal.get("changes", []):
        parameter = change.get("parameter")
        if isinstance(parameter, str) and parameter not in rejected:
            rejected[parameter] = change.get("value")
    return rejected


def _clock_reason(state: AgentState, value: float) -> str:
    metrics = state.get("current_metrics") or {}
    setup = metrics.get("setup_wns")
    hold = metrics.get("hold_wns")
    drc = metrics.get("drc_count")
    if signoff_passed(state.get("current_metrics"), state.get("last_status")):
        return (
            f"Reduce _SDC_CLK_PERIOD to {value:g} because the last run met "
            "DRC, setup, and hold."
        )
    if setup is not None and setup < 0:
        drc_text = "DRC is clean" if drc == 0 else f"DRC count is {drc}"
        return (
            f"Increase _SDC_CLK_PERIOD to {value:g} because setup WNS is {setup:.3f} ns "
            f"and {drc_text}."
        )
    if hold is not None and hold < 0:
        return f"Increase _SDC_CLK_PERIOD to {value:g} because hold WNS is {hold:.3f} ns."
    return f"Set _SDC_CLK_PERIOD to {value:g} inside the allowlisted range."


def _relax_utilization(state: AgentState) -> ParameterChange | None:
    knob = _knob(state["catalog"], "CORE_UTILIZATION")
    if knob is None or not knob["executable"]:
        return None
    current = state["accepted_params"].get("CORE_UTILIZATION", knob.get("default") or knob["minimum"])
    value = _clamp(float(current) - 4, knob)
    if value == float(current):
        return None
    return ParameterChange(
        parameter="CORE_UTILIZATION",
        value=value,
        reason="Lower CORE_UTILIZATION because DRC count is above zero.",
    )


def _clamp_previous(state: AgentState) -> Proposal:
    raw = Proposal.model_validate(state["proposal"])
    changes: list[ParameterChange] = []
    for change in raw.changes:
        knob = _knob(state["catalog"], change.parameter)
        if knob is None or not knob["executable"]:
            continue
        value = _clamp(change.value, knob)
        changes.append(
            ParameterChange(
                parameter=change.parameter,
                value=value,
                reason=f"Clamped {change.parameter} to {value:g} after validation rejected the previous value.",
            )
        )
    if not changes:
        raise FlowValidationError("validation error: proposal has no executable parameter")
    return Proposal(changes=changes[:3])


def _clamp(value: float, knob: dict[str, Any]) -> float:
    bounded = min(max(float(value), float(knob["minimum"])), float(knob["maximum"]))
    if knob["type"] == "int":
        return float(int(round(bounded)))
    return round(bounded, 3)


def _knob(catalog: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in catalog:
        if item["name"] == name:
            return item
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EDA Pilot ORFS agent loop.")
    parser.add_argument("--design", default="gcd")
    parser.add_argument("--platform", default="sky130hd")
    parser.add_argument("--budget", type=int, default=10)
    parser.add_argument("--model", default=os.environ.get("EDA_PILOT_MODEL", ""))
    parser.add_argument("--log", default="")
    args = parser.parse_args()
    result = run_session(
        design=args.design,
        platform=args.platform,
        run_budget=args.budget,
        model=args.model or None,
        log_path=Path(args.log) if args.log else None,
    )
    print(f"stop: {result['stop_reason']}")
    print(f"iterations: {result['iterations']}")
    print(f"advisor: {result['advisor']}")
    print(f"log: {result['log_path']}")
    print("best_run:")
    print(json.dumps(result["best_run"], indent=2))


if __name__ == "__main__":
    main()
