"""Random search over the executable knobs published by list_params.

Each trial draws one value inside every executable min/max range, checks it
with validate_params, then calls run_flow and get_metrics. The trial count is
the shared run budget.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from eda_pilot.config import ConfigurationError, Settings, load_settings
from mcp_tools.metrics import get_metrics
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError, list_params, validate_params

from benchmarks.compare_results import build_record, make_trial


def run_random(
    design: str,
    platform: str,
    budget: int,
    *,
    settings: Settings,
    seed: int = 1,
) -> dict[str, Any]:
    """Run ``budget`` validated random samples. Identical seeds repeat the samples."""

    if budget < 1:
        raise ValueError("budget must be at least 1")
    try:
        listed = list_params(design, platform, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return build_record(
            method="random",
            design=design,
            platform=platform,
            budget=budget,
            status="unavailable",
            message=str(exc),
            trials=[],
            runs_completed=0,
        )
    knobs = [item for item in listed.parameters if item.executable]
    if not knobs:
        return build_record(
            method="random",
            design=design,
            platform=platform,
            budget=budget,
            status="error",
            message="list_params returned no executable parameters.",
            trials=[],
            runs_completed=0,
        )
    method_settings = _method_settings(settings, budget)
    rng = random.Random(seed)
    trials: list[dict[str, Any]] = []
    for index in range(1, budget + 1):
        params = _sample_until_valid(design, platform, knobs, rng, method_settings)
        if params is None:
            return build_record(
                method="random",
                design=design,
                platform=platform,
                budget=budget,
                status="error",
                message="A random sample stayed outside the allowlist after 20 draws.",
                trials=trials,
                runs_completed=len(trials),
            )
        try:
            trials.append(
                _execute(design, platform, params, method_settings, index)
            )
        except (FlowValidationError, ConfigurationError) as exc:
            return build_record(
                method="random",
                design=design,
                platform=platform,
                budget=budget,
                status="error",
                message=str(exc),
                trials=trials,
                runs_completed=len(trials),
            )
    return build_record(
        method="random",
        design=design,
        platform=platform,
        budget=budget,
        status="ok",
        message="",
        trials=trials,
        runs_completed=len(trials),
        stop_reason="run budget exhausted",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Random search at a fixed run budget.")
    parser.add_argument("--design", default="gcd")
    parser.add_argument("--platform", default="sky130hd")
    parser.add_argument("--budget", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    record = run_random(
        args.design,
        args.platform,
        args.budget,
        settings=load_settings(),
        seed=args.seed,
    )
    _write(args.out, record)


def _sample_until_valid(
    design: str,
    platform: str,
    knobs: list[Any],
    rng: random.Random,
    settings: Settings,
) -> dict[str, float] | None:
    for _ in range(20):
        params = {knob.name: _sample_value(knob, rng) for knob in knobs}
        try:
            validated = validate_params(design, platform, params, settings=settings)
        except FlowValidationError:
            continue
        return validated.recorded_params
    return None


def _sample_value(knob: Any, rng: random.Random) -> float:
    low = float(knob.minimum)
    high = float(knob.maximum)
    step = float(knob.step or 0)
    if knob.type == "int" or step >= 1:
        return float(rng.randint(int(low), int(high)))
    if step > 0:
        count = int(round((high - low) / step))
        return low + rng.randint(0, count) * step
    drawn = min(high, max(low, round(rng.uniform(low, high), 6)))
    return float(drawn)


def _execute(
    design: str,
    platform: str,
    params: dict[str, float],
    settings: Settings,
    index: int,
) -> dict[str, Any]:
    result = run_flow(design, platform, params, settings=settings)
    metrics = None
    if result.status == "ok":
        metrics = get_metrics(result.run_id, settings=settings).model_dump()
    clock = params.get("_SDC_CLK_PERIOD")
    return make_trial(
        index=index,
        parameters=params,
        metrics=metrics,
        flow_status=result.status,
        clock_period=clock,
        runtime=result.runtime,
    )


def _method_settings(settings: Settings, budget: int) -> Settings:
    runs_dir = settings.runs_dir / "random" / f"b{budget}"
    return settings.model_copy(update={"runs_dir": runs_dir, "max_runs": budget})


def _write(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
