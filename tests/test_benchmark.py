"""Benchmark scoring, random search bounds, and the stand-in matrix."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from benchmarks.benchmark import run_default, run_matrix
from benchmarks.compare_results import build_record, compare, make_trial
from benchmarks.run_autotuner import (
    build_autotuner_argv,
    collect_autotuner_trials,
    run_autotuner,
)
from benchmarks.run_random import run_random
from eda_pilot.config import Settings
from mcp_tools.validation import list_params


def test_random_stays_inside_allowlist_and_repeats_a_seed(
    flow_settings: Settings, tmp_path: Path
) -> None:
    catalog = list_params("gcd", "sky130hd", settings=flow_settings)
    bounds = {item.name: item for item in catalog.parameters}
    first = run_random(
        "gcd",
        "sky130hd",
        2,
        settings=flow_settings.model_copy(update={"runs_dir": tmp_path / "a"}),
        seed=5,
    )
    second = run_random(
        "gcd",
        "sky130hd",
        2,
        settings=flow_settings.model_copy(update={"runs_dir": tmp_path / "b"}),
        seed=5,
    )
    other = run_random(
        "gcd",
        "sky130hd",
        2,
        settings=flow_settings.model_copy(update={"runs_dir": tmp_path / "c"}),
        seed=6,
    )

    assert first["status"] == "ok"
    assert first["runs_completed"] == 2
    assert first["trials"][0]["parameters"] == second["trials"][0]["parameters"]
    assert first["trials"][0]["parameters"] != other["trials"][0]["parameters"]
    for trial in first["trials"]:
        assert "_FR_LAYER_ADJUST" not in trial["parameters"]
        for name, value in trial["parameters"].items():
            knob = bounds[name]
            assert knob.executable
            assert knob.minimum <= value <= knob.maximum


def test_default_is_a_single_unmodified_run(flow_settings: Settings) -> None:
    record = run_default("gcd", "sky130hd", settings=flow_settings)

    assert record["runs_completed"] == 1
    assert record["trials"][0]["parameters"] == {}
    assert record["trials"][0]["clock_period"] == 1.1
    assert record["best"]["metrics"]["drc_count"] == 0
    assert record["best"]["metrics"]["setup_wns"] == -0.012
    assert record["best"]["passed"] is False


def test_autotuner_argv_uses_the_run_budget() -> None:
    argv = build_autotuner_argv(
        "openroad_autotuner",
        "gcd",
        "sky130hd",
        Path("designs") / "sky130hd" / "gcd" / "autotuner.json",
        20,
        7,
    )

    assert isinstance(argv, list)
    assert argv[argv.index("--samples") + 1] == "20"
    assert argv[argv.index("--algorithm") + 1] == "hyperopt"
    assert "--jobs" in argv


def test_missing_autotuner_records_no_metrics(
    flow_settings: Settings, monkeypatch
) -> None:
    design = flow_settings.orfs_flow_dir / "designs" / "sky130hd" / "gcd"
    (design / "autotuner.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.delenv("ORFS_AUTOTUNER", raising=False)
    monkeypatch.setattr("benchmarks.run_autotuner.find_autotuner", lambda: None)

    record = run_autotuner("gcd", "sky130hd", 10, settings=flow_settings, seed=1)

    assert record["status"] == "unavailable"
    assert record["trials"] == []
    assert record["best"] is None
    assert "No AutoTuner metrics" in record["message"]


def test_autotuner_collection_keeps_the_budget(tmp_path: Path) -> None:
    root = tmp_path / "flow" / "reports" / "sky130hd" / "gcd"
    clocks = [1.5, 1.2, 0.9]
    for index, clock in enumerate(clocks):
        variant = root / f"trial{index}"
        variant.mkdir(parents=True)
        metadata = {
            "finish__timing__setup__ws": 0.01,
            "finish__timing__hold__ws": 0.01,
            "finish__power__total": 0.2,
            "finish__design__instance__area": 1000 + index,
            "detailedroute__route__drc_errors": 0,
            "finish__runtime__total": 4.0,
            "_SDC_CLK_PERIOD": clock,
        }
        (variant / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        stamp = time.time() - 50 + index
        os.utime(variant / "metadata.json", (stamp, stamp))

    trials = collect_autotuner_trials(
        tmp_path / "flow",
        "sky130hd",
        "gcd",
        budget=2,
        started=time.time() - 80,
    )

    assert [trial["clock_period"] for trial in trials] == [1.5, 1.2]
    assert all(trial["passed"] for trial in trials)


def test_compare_ranks_the_smaller_passing_clock() -> None:
    failing = make_trial(
        index=1,
        parameters={"_SDC_CLK_PERIOD": 1.1},
        metrics={
            "drc_count": 0,
            "setup_wns": -0.012,
            "hold_wns": 0.005,
            "area": 10,
            "power": 1,
            "runtime": 1,
        },
        flow_status="ok",
        clock_period=1.1,
        runtime=1,
    )
    wide = _passing_trial(2.0, area=10, power=1)
    tight = _passing_trial(1.2, area=50, power=3)
    records = [
        build_record(
            method="default",
            design="gcd",
            platform="sky130hd",
            budget=None,
            status="ok",
            message="",
            trials=[failing],
            runs_completed=1,
        ),
        build_record(
            method="random",
            design="gcd",
            platform="sky130hd",
            budget=10,
            status="ok",
            message="",
            trials=[wide],
            runs_completed=10,
        ),
        build_record(
            method="autotuner",
            design="gcd",
            platform="sky130hd",
            budget=10,
            status="unavailable",
            message="OpenROAD AutoTuner executable was not found.",
            trials=[],
            runs_completed=0,
        ),
        build_record(
            method="agent",
            design="gcd",
            platform="sky130hd",
            budget=10,
            status="ok",
            message="",
            trials=[tight],
            runs_completed=4,
        ),
    ]

    table = compare(records)["tables"][0]

    assert table["rows"][3]["method"] == "agent"
    assert "agent has the smallest passing clock, 1.2 ns." in table["finding"]
    assert "autotuner" in table["finding"]


def test_equal_failing_metrics_stay_tied() -> None:
    slow = make_trial(
        index=1,
        parameters={},
        metrics={"drc_count": 0, "setup_wns": -0.012, "hold_wns": 0.005, "area": 10, "power": 1},
        flow_status="ok",
        clock_period=1.1,
        runtime=20,
    )
    fast = make_trial(
        index=1,
        parameters={},
        metrics={"drc_count": 0, "setup_wns": -0.012, "hold_wns": 0.005, "area": 99, "power": 8},
        flow_status="ok",
        clock_period=4.0,
        runtime=1,
    )
    records = [
        _ok("default", None, slow),
        _ok("random", 10, fast),
    ]
    finding = compare(records)["tables"][0]["finding"]
    assert "tied on the primary objective" in finding


def test_matrix_skips_unknown_designs_and_leaves_the_agent_log(
    flow_settings: Settings, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("benchmarks.run_autotuner.find_autotuner", lambda: None)
    demo = Path(__file__).resolve().parents[1] / "runs" / "decision_log.jsonl"
    before = demo.read_bytes() if demo.is_file() else None
    out = tmp_path / "bench"

    comparison = run_matrix(
        ["gcd", "jpeg"],
        "sky130hd",
        [2],
        settings=flow_settings,
        out_dir=out,
        seed=1,
    )

    by_design = {table["design"]: table for table in comparison["tables"]}
    assert by_design["jpeg"]["rows"][0]["status"] == "unavailable"
    assert all(row["status"] == "unavailable" for row in by_design["jpeg"]["rows"])
    gcd_rows = {row["method"]: row for row in by_design["gcd"]["rows"]}
    assert gcd_rows["default"]["runs_completed"] == 1
    assert gcd_rows["random"]["runs_completed"] == 2
    assert gcd_rows["agent"]["runs_completed"] == 2
    assert gcd_rows["autotuner"]["status"] == "unavailable"
    assert gcd_rows["autotuner"]["best"] is None
    assert "tied on the primary objective" in by_design["gcd"]["finding"]
    assert (out / "comparison.txt").is_file()
    if before is not None:
        assert demo.read_bytes() == before


def _passing_trial(clock: float, area: float, power: float) -> dict:
    return make_trial(
        index=1,
        parameters={"_SDC_CLK_PERIOD": clock},
        metrics={
            "drc_count": 0,
            "setup_wns": 0.01,
            "hold_wns": 0.02,
            "area": area,
            "power": power,
            "runtime": 3,
        },
        flow_status="ok",
        clock_period=clock,
        runtime=3,
    )


def _ok(method: str, budget: int | None, trial: dict) -> dict:
    return build_record(
        method=method,
        design="gcd",
        platform="sky130hd",
        budget=budget,
        status="ok",
        message="",
        trials=[trial],
        runs_completed=1 if budget is None else budget,
    )
