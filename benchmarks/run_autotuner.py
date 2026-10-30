"""Launch OpenROAD AutoTuner for the same trial budget.

The harness does not reimplement the tuner. It builds an argument list for
``openroad_autotuner`` and, when that program is absent, records the method as
unavailable. It does not fill in clock, area, power, or slack from another method.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from eda_pilot.config import ConfigurationError, Settings, load_settings
from mcp_tools.metrics import extract_metrics
from mcp_tools.validation import DESIGN_RE, FlowValidationError, list_params

from benchmarks.compare_results import build_record, make_trial

AUTOTUNER_MISSING = (
    "OpenROAD AutoTuner executable was not found. "
    "Set ORFS_AUTOTUNER or install openroad_autotuner. "
    "No AutoTuner metrics were recorded."
)


def run_autotuner(
    design: str,
    platform: str,
    budget: int,
    *,
    settings: Settings,
    seed: int = 1,
    executable: str | None = None,
) -> dict[str, Any]:
    """Run ``budget`` AutoTuner samples, or return status ``unavailable``."""

    if budget < 1:
        raise ValueError("budget must be at least 1")
    if not DESIGN_RE.fullmatch(design) or not DESIGN_RE.fullmatch(platform):
        return _unavailable(design, platform, budget, "design or platform name was rejected")
    try:
        list_params(design, platform, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return _unavailable(design, platform, budget, str(exc))
    flow = settings.resolve_flow_dir()
    if flow is None or not flow.is_dir():
        return _unavailable(
            design,
            platform,
            budget,
            "ORFS flow directory is not configured.",
        )
    config = (flow / "designs" / platform / design / "autotuner.json").resolve()
    designs_root = (flow / "designs").resolve()
    if designs_root not in config.parents or not config.is_file():
        return _unavailable(
            design,
            platform,
            budget,
            f"autotuner.json was not found for {platform}/{design}.",
        )
    program = executable if executable is not None else find_autotuner()
    if program is None:
        return _unavailable(design, platform, budget, AUTOTUNER_MISSING)
    argv = build_autotuner_argv(program, design, platform, config, budget, seed)
    started = time.time()
    timeout = min(settings.timeout_seconds * budget, 86_400)
    try:
        completed = subprocess.run(
            argv,
            cwd=str(flow),
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return build_record(
            method="autotuner",
            design=design,
            platform=platform,
            budget=budget,
            status="error",
            message=f"AutoTuner exceeded {timeout} seconds.",
            trials=[],
            runs_completed=0,
        )
    except OSError as exc:
        return _unavailable(design, platform, budget, f"AutoTuner could not be started: {exc}")
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()[-500:]
        return build_record(
            method="autotuner",
            design=design,
            platform=platform,
            budget=budget,
            status="error",
            message=tail or f"AutoTuner exited {completed.returncode}.",
            trials=[],
            runs_completed=0,
        )
    trials = collect_autotuner_trials(flow, platform, design, budget, started)
    if not trials:
        return build_record(
            method="autotuner",
            design=design,
            platform=platform,
            budget=budget,
            status="error",
            message="AutoTuner exited 0 but wrote no metadata.json metrics.",
            trials=[],
            runs_completed=0,
        )
    return build_record(
        method="autotuner",
        design=design,
        platform=platform,
        budget=budget,
        status="ok",
        message="",
        trials=trials,
        runs_completed=len(trials),
        stop_reason="run budget exhausted",
    )


def build_autotuner_argv(
    executable: str,
    design: str,
    platform: str,
    config: Path,
    samples: int,
    seed: int,
) -> list[str]:
    """Argv for one AutoTuner invocation. ``samples`` is the shared run budget."""

    if any(character in executable for character in "\r\n\x00"):
        raise ConfigurationError("ORFS_AUTOTUNER is not a usable executable path")
    if not DESIGN_RE.fullmatch(design) or not DESIGN_RE.fullmatch(platform):
        raise FlowValidationError("design or platform name was rejected")
    return [
        executable,
        "--design",
        design,
        "--platform",
        platform,
        "--config",
        str(config),
        "--jobs",
        "1",
        "tune",
        "--samples",
        str(samples),
        "--iterations",
        "1",
        "--seed",
        str(seed),
        "--algorithm",
        "hyperopt",
    ]


def find_autotuner() -> str | None:
    """Return the AutoTuner program, or None when it is not installed."""

    configured = os.environ.get("ORFS_AUTOTUNER", "").strip()
    if configured:
        if any(character in configured for character in "\r\n\x00"):
            raise ConfigurationError("ORFS_AUTOTUNER is not a usable executable path")
        if Path(configured).is_file():
            return configured
        return None
    return shutil.which("openroad_autotuner")


def collect_autotuner_trials(
    flow: Path,
    platform: str,
    design: str,
    budget: int,
    started: float,
) -> list[dict[str, Any]]:
    """Read at most ``budget`` metadata files written during this invocation."""

    report_root = (flow / "reports" / platform / design).resolve()
    if not report_root.is_dir():
        return []
    fresh = [
        path
        for path in report_root.rglob("metadata.json")
        if path.is_file() and path.stat().st_mtime >= started - 1
    ]
    fresh.sort(key=lambda path: path.stat().st_mtime)
    trials: list[dict[str, Any]] = []
    for index, path in enumerate(fresh[:budget], start=1):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        metrics = extract_metrics(path.parent.name, payload).model_dump()
        trials.append(
            make_trial(
                index=index,
                parameters={},
                metrics=metrics,
                flow_status="ok",
                clock_period=_clock_near(path.parent),
                runtime=metrics.get("runtime"),
            )
        )
    return trials


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run OpenROAD AutoTuner for one budget.")
    parser.add_argument("--design", default="gcd")
    parser.add_argument("--platform", default="sky130hd")
    parser.add_argument("--budget", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    record = run_autotuner(
        args.design,
        args.platform,
        args.budget,
        settings=load_settings(),
        seed=args.seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _unavailable(design: str, platform: str, budget: int, message: str) -> dict[str, Any]:
    return build_record(
        method="autotuner",
        design=design,
        platform=platform,
        budget=budget,
        status="unavailable",
        message=message,
        trials=[],
        runs_completed=0,
    )


def _clock_near(directory: Path) -> float | None:
    for path in directory.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        found = _find_clock(payload, depth=0)
        if found is not None:
            return found
    return None


def _find_clock(payload: object, depth: int) -> float | None:
    if depth > 6 or not isinstance(payload, dict):
        return None
    value = payload.get("_SDC_CLK_PERIOD")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    for child in payload.values():
        found = _find_clock(child, depth + 1)
        if found is not None:
            return found
    return None


if __name__ == "__main__":
    main()
