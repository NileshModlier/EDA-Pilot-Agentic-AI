"""Read timing, power, area, and routing metrics from ORFS metadata.json."""

from __future__ import annotations

import json
import math
from pathlib import Path

from eda_pilot.config import Settings, load_settings
from eda_pilot.models import MetricsResult, RunManifest
from mcp_tools.run_flow import load_manifest
from mcp_tools.validation import FlowValidationError

METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "setup_wns": ("finish__timing__setup__ws", "finish__timing__setup__wns"),
    "setup_tns": ("finish__timing__setup__tns",),
    "hold_wns": ("finish__timing__hold__ws", "finish__timing__hold__wns"),
    "hold_tns": ("finish__timing__hold__tns",),
    "power": ("finish__power__total",),
    "area": ("finish__design__instance__area", "finish__design__core__area"),
    "utilization": (
        "finish__design__instance__utilization",
        "finish__design__core__utilization",
    ),
    "drc_count": (
        "detailedroute__route__drc_errors",
        "finish__drt__drc_count",
        "detailedroute__route__drc_count",
    ),
    "runtime": (
        "finish__runtime__total",
        "run__flow__runtime__total",
        "total_time",
    ),
}


def get_metrics(run_id: str, *, settings: Settings | None = None) -> MetricsResult:
    """Parse metadata.json for one completed or failed run."""

    active = settings or load_settings()
    manifest = load_manifest(run_id, active)
    path = metadata_path(active, manifest)
    if path.is_symlink() or not path.is_file():
        raise FlowValidationError(
            f"metrics error: metadata.json not found for run {manifest.run_id}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowValidationError(
            f"metrics error: metadata.json for run {manifest.run_id} is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise FlowValidationError(
            f"metrics error: metadata.json for run {manifest.run_id} must be a JSON object"
        )
    return extract_metrics(manifest.run_id, payload)


def extract_metrics(run_id: str, payload: dict[str, object]) -> MetricsResult:
    """Map flat or nested ORFS metadata keys onto the public metric names."""

    flat = flatten_metrics(payload)
    values: dict[str, float | None] = {}
    missing: list[str] = []
    for name, aliases in METRIC_ALIASES.items():
        value = _lookup(flat, aliases)
        values[name] = value
        if value is None:
            missing.append(name)
    return MetricsResult(run_id=run_id, missing=missing, **values)


def metadata_path(settings: Settings, manifest: RunManifest) -> Path:
    flow = settings.resolve_flow_dir()
    if flow is None:
        raise FlowValidationError(
            "metrics error: ORFS is not configured. Set ORFS_ROOT to an OpenROAD-flow-scripts checkout."
        )
    flow_root = flow.resolve()
    path = (
        flow_root
        / "reports"
        / manifest.platform
        / manifest.design
        / manifest.flow_variant
        / "metadata.json"
    ).resolve()
    try:
        path.relative_to((flow_root / "reports").resolve())
    except ValueError as exc:
        raise FlowValidationError(
            "metrics error: metadata path escaped the reports directory"
        ) from exc
    return path


def flatten_metrics(payload: object, prefix: str = "") -> dict[str, object]:
    flat: dict[str, object] = {}
    if not isinstance(payload, dict):
        return flat
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        name = f"{prefix}__{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_metrics(value, name))
        else:
            flat[name] = value
    return flat


def _lookup(flat: dict[str, object], names: tuple[str, ...]) -> float | None:
    for name in names:
        value = flat.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        return float(value)
    return None
