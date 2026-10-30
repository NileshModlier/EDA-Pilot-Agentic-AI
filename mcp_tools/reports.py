"""Return the tail of one ORFS report.

``report_name`` is an enum. It is never used as a filesystem path.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_pilot.config import Settings, load_settings
from eda_pilot.models import ReportResult, RunManifest
from mcp_tools.run_flow import load_manifest
from mcp_tools.validation import FlowValidationError

MAX_REPORT_LINES = 200
MAX_REPORT_BYTES = 512_000
MAX_LINE_LENGTH = 2_000

REPORT_FILES: dict[str, tuple[str, ...]] = {
    "timing": ("6_finish.rpt", "6_final_report.rpt", "6_report.rpt", "6_report.log"),
    "drc": ("5_route_drc.rpt", "5_route_drc.report", "drc.rpt"),
    "congestion": ("5_global_route.rpt", "congestion.rpt", "5_1_grt.rpt", "5_1_grt.log"),
}
REPORT_SCAN: dict[str, re.Pattern[str]] = {
    "timing": re.compile(r"(finish|timing|6_report)", re.IGNORECASE),
    "drc": re.compile(r"drc", re.IGNORECASE),
    "congestion": re.compile(r"(congestion|global_route|grt)", re.IGNORECASE),
}
REPORT_SUFFIXES = {".rpt", ".log", ".report", ".txt"}


def read_report(
    run_id: str,
    report_name: str,
    *,
    settings: Settings | None = None,
) -> ReportResult:
    """Return at most 200 lines from the tail of one report."""

    if report_name not in REPORT_FILES:
        raise FlowValidationError(
            "report error: report_name must be timing, drc, or congestion"
        )
    active = settings or load_settings()
    manifest = load_manifest(run_id, active)
    directories = _report_directories(active, manifest)
    source = _find_report(directories, report_name)
    text, line_count, truncated = read_tail(source, MAX_REPORT_LINES)
    return ReportResult(
        run_id=manifest.run_id,
        report_name=report_name,  # type: ignore[arg-type]
        source_file=source.name,
        line_count=line_count,
        truncated=truncated,
        text=text,
    )


def read_tail(path: Path, max_lines: int) -> tuple[str, int, bool]:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > MAX_REPORT_BYTES:
            handle.seek(size - MAX_REPORT_BYTES)
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if size > MAX_REPORT_BYTES and lines:
        lines = lines[1:]
    truncated = len(lines) > max_lines or size > MAX_REPORT_BYTES
    selected = lines[-max_lines:]
    clipped = [
        line if len(line) <= MAX_LINE_LENGTH else line[:MAX_LINE_LENGTH]
        for line in selected
    ]
    return "\n".join(clipped), len(clipped), truncated


def _report_directories(settings: Settings, manifest: RunManifest) -> list[Path]:
    flow = settings.resolve_flow_dir()
    if flow is None:
        raise FlowValidationError(
            "report error: ORFS is not configured. Set ORFS_ROOT to an OpenROAD-flow-scripts checkout."
        )
    flow_root = flow.resolve()
    directories: list[Path] = []
    for folder in ("reports", "logs"):
        path = (
            flow_root / folder / manifest.platform / manifest.design / manifest.flow_variant
        ).resolve()
        try:
            path.relative_to((flow_root / folder).resolve())
        except ValueError as exc:
            raise FlowValidationError(
                "report error: report path escaped the flow directory"
            ) from exc
        directories.append(path)
    return directories


def _find_report(directories: list[Path], report_name: str) -> Path:
    for directory in directories:
        if not directory.is_dir():
            continue
        for name in REPORT_FILES[report_name]:
            candidate = directory / name
            if candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            try:
                resolved.relative_to(directory.resolve())
            except ValueError:
                continue
            return resolved

    pattern = REPORT_SCAN[report_name]
    matches: list[Path] = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for candidate in directory.iterdir():
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if candidate.suffix.lower() not in REPORT_SUFFIXES:
                continue
            if pattern.search(candidate.name) is None:
                continue
            resolved = candidate.resolve()
            try:
                resolved.relative_to(directory.resolve())
            except ValueError:
                continue
            matches.append(resolved)
    if not matches:
        raise FlowValidationError(f"report error: {report_name} report not found for this run")
    matches.sort(key=lambda path: path.name)
    return matches[0]
