"""Ten-run agent sessions and validation guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.agent import run_session
from agent.proposal_models import ParameterChange, Proposal
from eda_pilot.config import ConfigurationError, Settings
from mcp_tools.run_flow import run_flow as real_run_flow


def test_ten_run_session_stops_at_the_budget(flow_settings: Settings, tmp_path: Path) -> None:
    settings = flow_settings.model_copy(update={"max_runs": 12})
    log_path = tmp_path / "decision_log.jsonl"
    result = run_session(
        design="gcd",
        platform="sky130hd",
        run_budget=10,
        settings=settings,
        log_path=log_path,
    )

    assert result["stop_reason"] == "run budget exhausted"
    assert result["iterations"] == 10
    assert result["remaining_runs"] == 0
    assert result["best_run"] is not None
    assert result["best_run"]["passed"] is False
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 10
    periods = []
    for entry in result["decision_log"]:
        assert entry["result"] == "fail"
        assert entry["metrics"]["drc_count"] == 0
        assert entry["metrics"]["setup_wns"] < 0
        period = entry["parameters"]["_SDC_CLK_PERIOD"]
        assert 0.8 <= period <= 5.0
        periods.append(period)
    assert periods == sorted(periods)
    assert len(set(periods)) == 10
    assert "setup WNS" in result["decision_log"][1]["diagnosis"]


def test_out_of_range_proposal_does_not_run(
    flow_settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0, "params": []}

    def spy(design: str, platform: str, params: object = None, *, settings: Settings | None = None):
        calls["count"] += 1
        calls["params"].append(dict(params or {}))
        return real_run_flow(design, platform, params, settings=settings)

    monkeypatch.setattr("agent.agent.run_flow", spy)
    attempts = {"n": 0}

    def propose(state: dict) -> Proposal:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return Proposal(
                changes=[
                    ParameterChange(
                        parameter="_SDC_CLK_PERIOD",
                        value=9.5,
                        reason="Too small a period for this design.",
                    )
                ]
            )
        return Proposal(
            changes=[
                ParameterChange(
                    parameter="_SDC_CLK_PERIOD",
                    value=1.5,
                    reason="Use a legal clock after the previous value was rejected.",
                )
            ]
        )

    result = run_session(
        design="gcd",
        platform="sky130hd",
        run_budget=1,
        settings=flow_settings,
        log_path=tmp_path / "decision_log.jsonl",
        proposer=propose,
        diagnoser=lambda state: "No completed run yet.",
    )

    assert calls["count"] == 1
    assert calls["params"][0]["_SDC_CLK_PERIOD"] == 1.5
    assert result["iterations"] == 1
    assert result["decision_log"][0]["result"] == "fail"
    assert 9.5 not in calls["params"][0].values()


def test_duplicate_changes_never_start_a_flow(
    flow_settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("run_flow was called for a duplicate proposal")

    monkeypatch.setattr("agent.agent.run_flow", fail)

    def propose(state: dict) -> Proposal:
        return Proposal(
            changes=[
                ParameterChange(parameter="_SDC_CLK_PERIOD", value=1.2, reason="First clock."),
                ParameterChange(parameter="_SDC_CLK_PERIOD", value=1.4, reason="Second clock."),
            ]
        )

    result = run_session(
        design="gcd",
        platform="sky130hd",
        run_budget=1,
        settings=flow_settings,
        log_path=tmp_path / "decision_log.jsonl",
        proposer=propose,
        diagnoser=lambda state: "No completed run yet.",
    )

    assert result["stop_reason"] == "proposal rejected by validation"
    assert result["iterations"] == 1
    text = tmp_path.joinpath("decision_log.jsonl").read_text(encoding="utf-8")
    assert "duplicate parameter '_SDC_CLK_PERIOD'" in text


def test_passing_run_is_the_best_run(
    flow_settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from eda_pilot.models import MetricsResult, RunResult

    submitted: list[dict[str, float]] = []

    def spy(design: str, platform: str, params: object = None, *, settings: Settings | None = None):
        submitted.append(dict(params or {}))
        return RunResult(
            run_id="ab" * 16,
            status="ok",
            runtime=0.01,
            flow_variant="p1" + ("ab" * 16),
            message=None,
        )

    def metrics(run_id: str, *, settings: Settings | None = None) -> MetricsResult:
        period = submitted[-1]["_SDC_CLK_PERIOD"]
        setup = 0.02 if period >= 2.0 else -0.2
        return MetricsResult(
            run_id=run_id,
            setup_wns=setup,
            setup_tns=0.0,
            hold_wns=0.01,
            hold_tns=0.0,
            power=0.001,
            area=100.0,
            utilization=30.0,
            drc_count=0,
            runtime=0.01,
            missing=[],
        )

    monkeypatch.setattr("agent.agent.run_flow", spy)
    monkeypatch.setattr("agent.agent.get_metrics", metrics)

    result = run_session(
        design="gcd",
        platform="sky130hd",
        run_budget=6,
        settings=flow_settings.model_copy(update={"max_runs": 6}),
        log_path=tmp_path / "decision_log.jsonl",
    )

    assert result["best_run"]["passed"] is True
    assert result["best_run"]["clock_period"] >= 2.0
    assert result["best_run"]["clock_period"] == min(
        entry["parameters"]["_SDC_CLK_PERIOD"]
        for entry in result["decision_log"]
        if entry["result"] == "pass"
    )
    assert all(0.8 <= period <= 5.0 for period in (item["_SDC_CLK_PERIOD"] for item in submitted))


def test_budget_cannot_exceed_the_server_limit(flow_settings: Settings, tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="server run budget"):
        run_session(
            design="gcd",
            platform="sky130hd",
            run_budget=10,
            settings=flow_settings,
            log_path=tmp_path / "decision_log.jsonl",
        )
