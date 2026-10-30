"""Continue the P3.3 campaign from finished aes and gcd runs.

Completed flows are reloaded. An interrupted aes trial is recorded as failed.
Later random samples and the agent session are the only new aes work.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from agent.agent import _consider_best, _initial_state, _update_clock_bounds, build_graph, load_advisor
from agent.state import clock_period
from eda_pilot.config import REPO_ROOT, load_settings
from mcp_tools.metrics import get_metrics
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError, list_params

from benchmarks.compare_results import build_record, compare, make_trial, render
from benchmarks.run_agent import run_agent
from benchmarks.run_autotuner import AUTOTUNER_MISSING, run_autotuner
from benchmarks.run_random import _method_settings, _sample_until_valid

CAMPAIGN = REPO_ROOT / "results" / "benchmark_campaign"
CHECKPOINT = REPO_ROOT / "results" / "campaign_checkpoint.json"
RESULTS = REPO_ROOT / "results" / "benchmark_results.json"
SUMMARY = REPO_ROOT / "reports" / "benchmark_summary.md"
AES_BOARD = REPO_ROOT / "reports" / "aes_leaderboard.md"
PLOTS = REPO_ROOT / "plots"
AES_RUNS = REPO_ROOT / "results" / "p33_aes_runs_v2"
IBEX_RUNS = REPO_ROOT / "results" / "p33_ibex_runs"
PLATFORM = "sky130hd"
BUDGET = 10
SEED = 1


def _load_checkpoint() -> dict[str, Any]:
    if not CHECKPOINT.is_file():
        return {}
    payload = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("campaign checkpoint is not a JSON object")
    return payload

INTERRUPTED_CAUSE = (
    "The benchmark process exited during floorplan repair_timing. "
    "Synthesis had finished. Placement, CTS, routing, and GDS were not produced."
)


def main() -> None:
    checkpoint = _load_checkpoint()
    settings = load_settings().model_copy(update={"timeout_seconds": 7200, "max_runs": BUDGET})
    if "aes" not in checkpoint:
        checkpoint["aes"] = _seed_aes(settings)
        _store(checkpoint)
    _finish_aes_random(checkpoint, settings)
    _finish_aes_agent(checkpoint, settings)
    _store(checkpoint)
    if not _design_ready(checkpoint["aes"]):
        raise SystemExit("aes results are incomplete; ibex was not started")
    _write_aes_board(checkpoint)
    if "ibex" not in checkpoint:
        checkpoint["ibex"] = {"default": None, "random_trials": [], "agent": None, "autotuner": None}
        _store(checkpoint)
    _finish_fresh_design("ibex", checkpoint, settings, IBEX_RUNS)
    _store(checkpoint)


def _seed_aes(settings: Any) -> dict[str, Any]:
    samples = _replay_samples("aes", settings)
    manifests = _aes_manifests()
    _require_same_params(samples[0], manifests["ok"]["params"], "random trial 1")
    _require_same_params(samples[1], manifests["error"]["params"], "random trial 2")
    _require_same_params(samples[2], manifests["interrupted"]["params"], "random trial 3")
    default_settings = settings.model_copy(update={"runs_dir": AES_RUNS / "default", "max_runs": 1})
    random_settings = _method_settings(settings.model_copy(update={"runs_dir": AES_RUNS}), BUDGET)
    default_manifest = manifests["default"]
    default_metrics = get_metrics(default_manifest["run_id"], settings=default_settings).model_dump()
    default_clock = next(
        item.default
        for item in list_params("aes", PLATFORM, settings=settings).parameters
        if item.name == "_SDC_CLK_PERIOD"
    )
    default_trial = make_trial(
        index=1,
        parameters={},
        metrics=default_metrics,
        flow_status="ok",
        clock_period=default_clock,
        runtime=default_manifest["runtime"],
    )
    ok_metrics = get_metrics(manifests["ok"]["run_id"], settings=random_settings).model_dump()
    trial_ok = make_trial(
        index=1,
        parameters=manifests["ok"]["params"],
        metrics=ok_metrics,
        flow_status="ok",
        clock_period=manifests["ok"]["params"].get("_SDC_CLK_PERIOD"),
        runtime=manifests["ok"]["runtime"],
    )
    trial_error = make_trial(
        index=2,
        parameters=manifests["error"]["params"],
        metrics=None,
        flow_status="error",
        clock_period=manifests["error"]["params"].get("_SDC_CLK_PERIOD"),
        runtime=manifests["error"]["runtime"],
    )
    trial_interrupted = make_trial(
        index=3,
        parameters=manifests["interrupted"]["params"],
        metrics=None,
        flow_status="error",
        clock_period=manifests["interrupted"]["params"].get("_SDC_CLK_PERIOD"),
        runtime=None,
    )
    autotuner = run_autotuner("aes", PLATFORM, BUDGET, settings=settings, seed=SEED)
    return {
        "samples": samples,
        "default": _record(
            "default",
            "aes",
            None,
            [default_trial],
            "default configuration",
        ),
        "random_trials": [trial_ok, trial_error, trial_interrupted],
        "failures": [
            _failure("aes", "random", 2, manifests["error"]["run_id"], _placement_cause()),
            _failure("aes", "random", 3, manifests["interrupted"]["run_id"], INTERRUPTED_CAUSE),
        ],
        "agent": None,
        "autotuner": autotuner,
    }


def _finish_aes_random(checkpoint: dict[str, Any], settings: Any) -> None:
    aes = checkpoint["aes"]
    done = {trial["index"] for trial in aes["random_trials"]}
    method_settings = _method_settings(
        settings.model_copy(update={"runs_dir": AES_RUNS}), BUDGET
    ).model_copy(update={"max_runs": 30})
    for index in range(1, BUDGET + 1):
        if index in done:
            continue
        _run_one_random("aes", aes, index, method_settings)
        _store(checkpoint)


def _finish_aes_agent(checkpoint: dict[str, Any], settings: Any) -> None:
    if checkpoint["aes"].get("agent"):
        return
    _note_lost_agent_run(checkpoint)
    log_path = CAMPAIGN / "logs" / "aes_sky130hd_agent_b10.jsonl"
    records = _load_agent_log(log_path)
    if records:
        checkpoint["aes"]["agent"] = _continue_agent("aes", records, settings, log_path)
    else:
        checkpoint["aes"]["agent"] = run_agent(
            "aes",
            PLATFORM,
            BUDGET,
            settings=settings.model_copy(update={"runs_dir": AES_RUNS, "max_runs": BUDGET}),
            log_path=log_path,
        )
    _store(checkpoint)


def _note_lost_agent_run(checkpoint: dict[str, Any]) -> None:
    run_id = "62ec77a66e2b42208a45effc1ba0b6d6"
    failures = checkpoint["aes"].setdefault("failures", [])
    if any(item.get("run_id") == run_id for item in failures):
        return
    failures.append(
        {
            "design": "aes",
            "method": "agent",
            "index": 5,
            "run_id": run_id,
            "cause": (
                "The paused benchmark process exited during detailed routing. "
                "This attempt was not scored. The same clock search continued in a new flow."
            ),
        }
    )


def _load_agent_log(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("flow_status") is None:
            continue
        records.append(record)
    return records


def _continue_agent(
    design: str,
    records: list[dict[str, Any]],
    settings: Any,
    log_path: Path,
) -> dict[str, Any]:
    """Keep the finished agent iterations and run the rest of the same search."""

    method_settings = settings.model_copy(
        update={"runs_dir": AES_RUNS / "agent" / f"b{BUDGET}", "max_runs": 16}
    )
    listed = list_params(design, PLATFORM, settings=method_settings)
    knobs = [item.model_dump() for item in listed.parameters]
    clock = next(item for item in knobs if item["name"] == "_SDC_CLK_PERIOD")
    diagnoser, proposer, advisor = load_advisor(None)
    state = _initial_state(
        design=design,
        platform=PLATFORM,
        run_budget=BUDGET,
        knobs=knobs,
        clock=clock,
        advisor=advisor,
    )
    for record in records:
        passed = record.get("result") == "pass"
        state["last_status"] = record.get("flow_status")
        state["last_run_id"] = record.get("run_id")
        state["last_runtime"] = record.get("duration")
        state["accepted_params"] = dict(record.get("parameters") or {})
        state["current_metrics"] = record.get("metrics")
        state["iteration"] = int(record.get("iteration") or len(state["history"]))
        low, high = _update_clock_bounds(state, state["accepted_params"], passed, state["current_metrics"])
        state["clock_low"] = low
        state["clock_high"] = high
        state["best_run"] = _consider_best(state, record, passed)
        state["history"] = [*state["history"], record]
        state["decision_log"] = [*state["decision_log"], record]
        state["remaining_runs"] = state["remaining_runs"] - 1
    state["stop_reason"] = ""
    state["proposal"] = None
    state["validation_message"] = ""
    state["ran_this_iteration"] = False
    graph = build_graph(method_settings, diagnoser, proposer, log_path)
    final = graph.invoke(state, {"recursion_limit": 250})
    default_clock = clock.get("default")
    trials = []
    for entry in final["decision_log"]:
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
        platform=PLATFORM,
        budget=BUDGET,
        status="ok",
        message="",
        trials=trials,
        runs_completed=len(trials),
        stop_reason=final.get("stop_reason"),
    )


def _finish_fresh_design(
    design: str,
    checkpoint: dict[str, Any],
    settings: Any,
    runs_root: Path,
) -> None:
    block = checkpoint[design]
    design_settings = settings.model_copy(update={"runs_dir": runs_root, "max_runs": BUDGET})
    if block.get("default") is None:
        from benchmarks.benchmark import run_default

        block["default"] = run_default(design, PLATFORM, settings=design_settings)
        _store(checkpoint)
    if not block.get("samples"):
        block["samples"] = _replay_samples(design, design_settings)
        block["random_trials"] = []
        block["failures"] = list(block.get("failures") or [])
        _store(checkpoint)
    method_settings = _method_settings(design_settings, BUDGET).model_copy(
        update={"max_runs": 30}
    )
    done = {trial["index"] for trial in block["random_trials"]}
    for index in range(1, BUDGET + 1):
        if index in done:
            continue
        _run_one_random(design, block, index, method_settings)
        _store(checkpoint)
    if not block.get("autotuner"):
        block["autotuner"] = run_autotuner(
            design, PLATFORM, BUDGET, settings=design_settings, seed=SEED
        )
        _store(checkpoint)
    if not block.get("agent"):
        log_path = CAMPAIGN / "logs" / f"{design}_sky130hd_agent_b10.jsonl"
        block["agent"] = run_agent(
            design,
            PLATFORM,
            BUDGET,
            settings=design_settings,
            log_path=log_path,
        )
        _store(checkpoint)


def _run_one_random(design: str, block: dict[str, Any], index: int, settings: Any) -> None:
    params = block["samples"][index - 1]
    try:
        result = run_flow(design, PLATFORM, params, settings=settings)
    except (FlowValidationError, OSError) as exc:
        trial = make_trial(
            index=index,
            parameters=params,
            metrics=None,
            flow_status="error",
            clock_period=params.get("_SDC_CLK_PERIOD"),
            runtime=None,
        )
        block["random_trials"].append(trial)
        block.setdefault("failures", []).append(
            _failure(design, "random", index, None, str(exc))
        )
        return
    metrics = None
    cause = None
    if result.status == "ok":
        try:
            metrics = get_metrics(result.run_id, settings=settings).model_dump()
        except FlowValidationError as exc:
            cause = str(exc)
    else:
        cause = _cause_from_logs(settings.runs_dir / result.run_id) or result.message
    trial = make_trial(
        index=index,
        parameters=params,
        metrics=metrics,
        flow_status=result.status,
        clock_period=params.get("_SDC_CLK_PERIOD"),
        runtime=result.runtime,
    )
    block["random_trials"].append(trial)
    if result.status != "ok" or cause:
        block.setdefault("failures", []).append(
            _failure(design, "random", index, result.run_id, cause or result.message or result.status)
        )


def _replay_samples(design: str, settings: Any) -> list[dict[str, float]]:
    import random

    listed = list_params(design, PLATFORM, settings=settings)
    knobs = [item for item in listed.parameters if item.executable]
    rng = random.Random(SEED)
    samples = []
    for _ in range(BUDGET):
        params = _sample_until_valid(design, PLATFORM, knobs, rng, settings)
        if params is None:
            raise SystemExit(f"could not draw a valid {design} sample")
        samples.append(params)
    return samples


def _aes_manifests() -> dict[str, dict[str, Any]]:
    return {
        "default": _read_manifest(AES_RUNS / "default" / "1a2a58146ed04cbb9addb95e59acf2a5"),
        "ok": _read_manifest(AES_RUNS / "random" / "b10" / "38a1d917b2fd48e390ea200a942975f3"),
        "error": _read_manifest(AES_RUNS / "random" / "b10" / "3514e403ea784cbda77f48e272aa53d0"),
        "interrupted": _read_manifest(
            AES_RUNS / "random" / "b10" / "aa931b086b6a46ba97a04c29c7ee18cd"
        ),
    }


def _read_manifest(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))


def _placement_cause() -> str:
    text = (
        AES_RUNS / "random" / "b10" / "3514e403ea784cbda77f48e272aa53d0" / "stdout.log"
    ).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if "ERROR FLW-0024" in line:
            return line.strip()
    return "ORFS exited with status 2 during global placement."


def _cause_from_logs(run_dir: Path) -> str | None:
    chunks: list[str] = []
    for name in ("stdout.log", "stderr.log"):
        path = run_dir / name
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(chunks)
    for line in text.splitlines():
        if "ERROR FLW-" in line or "ERROR " in line:
            return line.strip()
    for line in reversed(text.splitlines()):
        if "Error" in line or "error:" in line:
            return line.strip()
    return None


def _record(
    method: str,
    design: str,
    budget: int | None,
    trials: list[dict[str, Any]],
    stop_reason: str,
) -> dict[str, Any]:
    return build_record(
        method=method,
        design=design,
        platform=PLATFORM,
        budget=budget,
        status="ok",
        message="",
        trials=trials,
        runs_completed=len(trials),
        stop_reason=stop_reason,
    )


def _failure(
    design: str,
    method: str,
    index: int,
    run_id: str | None,
    cause: str,
) -> dict[str, Any]:
    return {
        "design": design,
        "method": method,
        "index": index,
        "run_id": run_id,
        "cause": cause,
    }


def _design_ready(block: dict[str, Any]) -> bool:
    default = block.get("default") or {}
    agent = block.get("agent") or {}
    trials = block.get("random_trials") or []
    if default.get("status") != "ok" or not default.get("trials"):
        return False
    if len(trials) < BUDGET:
        return False
    if agent.get("status") != "ok" or not agent.get("trials"):
        return False
    for trial in [default["trials"][0], *trials, *agent["trials"]]:
        if trial.get("flow_status") != "ok":
            continue
        for field in ("area", "power", "setup_wns", "hold_wns", "drc_count", "runtime"):
            if trial.get(field) is None:
                return False
    return True


def _records(checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    records = _gcd_records()
    for design in ("aes", "ibex"):
        block = checkpoint.get(design)
        if not block:
            continue
        if block.get("default"):
            records.append(block["default"])
        trials = block.get("random_trials") or []
        if trials:
            records.append(
                _record(
                    "random",
                    design,
                    BUDGET,
                    sorted(trials, key=lambda item: item["index"]),
                    "run budget exhausted",
                )
            )
        if block.get("autotuner"):
            records.append(block["autotuner"])
        elif design == "aes":
            records.append(
                build_record(
                    method="autotuner",
                    design=design,
                    platform=PLATFORM,
                    budget=BUDGET,
                    status="unavailable",
                    message=AUTOTUNER_MISSING,
                    trials=[],
                    runs_completed=0,
                )
            )
        if block.get("agent"):
            records.append(block["agent"])
    return records


def _gcd_records() -> list[dict[str, Any]]:
    records = []
    for name in (
        "gcd_sky130hd_default_base.json",
        "gcd_sky130hd_random_b10.json",
        "gcd_sky130hd_autotuner_b10.json",
        "gcd_sky130hd_agent_b10.json",
    ):
        records.append(json.loads((CAMPAIGN / name).read_text(encoding="utf-8")))
    return records


def _store(checkpoint: dict[str, Any]) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    records = _records(checkpoint)
    failures: list[dict[str, Any]] = []
    for design in ("aes", "ibex"):
        block = checkpoint.get(design) or {}
        failures.extend(block.get("failures") or [])
    payload = {
        "objective": "Smallest clock period with DRC = 0, setup WNS >= 0, and hold WNS >= 0.",
        "budget": BUDGET,
        "seed": SEED,
        "records": records,
        "failures": failures,
        "comparison": compare(records),
    }
    RESULTS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(_summary(payload), encoding="utf-8")
    _write_plots(records)


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "# Benchmark summary",
        "",
        payload["objective"],
        "",
        "Budget 10. Seed 1. Platform sky130hd. gcd was not rerun.",
        "",
        "## Leaderboards",
        "",
        render(payload["comparison"]).rstrip(),
        "",
        _metrics_table(payload["records"]),
        "",
        "## Failed runs",
        "",
    ]
    if not payload["failures"]:
        lines.append("No failed runs are recorded yet.")
    else:
        for item in payload["failures"]:
            lines.append(
                f"- {item['design']} {item['method']} trial {item['index']}: {item['cause']}"
            )
    lines.extend(["", "## Failure analysis", "", _failure_analysis(payload["failures"]), ""])
    lines.append(
        "Recovered aes work: default and random trial 1 are the original completed flows. "
        "Failed and interrupted random trials stay in the record and were not rerun."
    )
    lines.append("")
    return "\n".join(lines)


def _write_aes_board(checkpoint: dict[str, Any]) -> None:
    records = [record for record in _records(checkpoint) if record["design"] == "aes"]
    failures = [
        item for item in (checkpoint.get("aes") or {}).get("failures") or [] if item["design"] == "aes"
    ]
    text = "\n".join(
        [
            "# AES leaderboard",
            "",
            "Success means the flow finished with DRC = 0, setup WNS >= 0, and hold WNS >= 0.",
            "",
            render(compare(records)).rstrip(),
            "",
            _metrics_table(records),
            "",
            "## Failure analysis",
            "",
            _failure_analysis(failures),
            "",
        ]
    )
    AES_BOARD.write_text(text, encoding="utf-8")


def _metrics_table(records: list[dict[str, Any]]) -> str:
    lines = [
        "## Success rate",
        "",
        "| Design | Method | Runs | Finished | Signoff | Success rate | Area | Power | Setup WNS | Hold WNS | DRC | Runtime (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        if record["method"] == "autotuner":
            continue
        trials = record.get("trials") or []
        finished = sum(1 for trial in trials if trial.get("flow_status") == "ok")
        signoff = sum(1 for trial in trials if trial.get("passed"))
        runs = len(trials)
        rate = f"{signoff / runs:.0%}" if runs else "n/a"
        best = record.get("best") or {}
        lines.append(
            "| {design} | {method} | {runs} | {finished} | {signoff} | {rate} | {area} | {power} | {setup} | {hold} | {drc} | {runtime} |".format(
                design=record["design"],
                method=record["method"],
                runs=runs,
                finished=finished,
                signoff=signoff,
                rate=rate,
                area=_cell(best.get("area")),
                power=_cell(best.get("power")),
                setup=_cell(best.get("setup_wns")),
                hold=_cell(best.get("hold_wns")),
                drc=_cell(best.get("drc_count")),
                runtime=_cell(best.get("runtime")),
            )
        )
    return "\n".join(lines)


def _failure_analysis(failures: list[dict[str, Any]]) -> str:
    if not failures:
        return "No failed runs are recorded."
    groups: dict[str, list[str]] = {}
    for item in failures:
        cause = item.get("cause") or "unknown"
        if "FLW-0024" in cause or "density exceeds" in cause:
            kind = "Placement density above 1.0"
        elif "GRT-0116" in cause or "congestion" in cause:
            kind = "Global routing congestion"
        elif "DPL-0033" in cause or "detailed placement" in cause:
            kind = "Detailed placement check failed"
        elif "exited during" in cause or "not scored" in cause:
            kind = "Benchmark process interrupted"
        else:
            kind = "Other flow error"
        groups.setdefault(kind, []).append(
            f"{item['design']} {item['method']} trial {item['index']}"
        )
    lines = [
        "| Failure class | Count | Runs |",
        "| --- | --- | --- |",
    ]
    for kind, runs in groups.items():
        lines.append(f"| {kind} | {len(runs)} | {', '.join(runs)} |")
    return "\n".join(lines)


def _cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return "n/a"
    return str(value)


def _write_plots(records: list[dict[str, Any]]) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    PLOTS.mkdir(parents=True, exist_ok=True)
    designs = []
    methods = ["default", "random", "agent"]
    table: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        if record["method"] not in methods or not record.get("best"):
            continue
        table.setdefault(record["design"], {})[record["method"]] = record["best"]
        if record["design"] not in designs:
            designs.append(record["design"])
    if not designs:
        return
    _bars(plt, designs, methods, table, "clock_period", "Passing or best clock (ns)", PLOTS / "leaderboard_clock.png")
    _bars(plt, designs, methods, table, "runtime", "Best-trial runtime (s)", PLOTS / "runtime_comparison.png")
    _bars(plt, designs, methods, table, "area", "Best-trial area (um^2)", PLOTS / "area_comparison.png")
    _bars(plt, designs, methods, table, "setup_wns", "Best-trial setup WNS (ns)", PLOTS / "wns_comparison.png")


def _bars(plt: Any, designs: list[str], methods: list[str], table: dict[str, Any], field: str, ylabel: str, path: Path) -> None:
    positions = list(range(len(designs)))
    width = 0.25
    figure, axis = plt.subplots(figsize=(8, 4.5))
    for offset, method in enumerate(methods):
        values = []
        for design in designs:
            best = table.get(design, {}).get(method) or {}
            value = best.get(field)
            values.append(value if isinstance(value, (int, float)) else 0)
        axis.bar(
            [item + (offset - 1) * width for item in positions],
            values,
            width,
            label=method,
        )
    axis.set_xticks(positions)
    axis.set_xticklabels(designs)
    axis.set_ylabel(ylabel)
    axis.set_xlabel("Design")
    axis.set_title(ylabel)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)


def _require_same_params(left: dict[str, float], right: dict[str, Any], label: str) -> None:
    if _round_params(left) != _round_params(right):
        raise SystemExit(f"seed replay does not match the saved {label}")


def _round_params(params: dict[str, Any]) -> dict[str, float]:
    return {key: round(float(value), 6) for key, value in params.items()}


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
