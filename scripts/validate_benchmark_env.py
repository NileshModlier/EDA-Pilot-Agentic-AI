"""Check the benchmark machine without starting an ORFS finish run.

The script calls list_params for gcd, aes, and ibex. It calls run_flow only
when that call fails before a process can start. A checkout that already has
config.mk and constraint.sdc is reported as ready, and finish is left unstarted.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eda_pilot.config import ConfigurationError, Settings, load_settings
from mcp_tools.metrics import extract_metrics
from mcp_tools.reports import read_tail
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError, list_params

DESIGNS = ("gcd", "aes", "ibex")
PLATFORM = "sky130hd"
DESIGN_FILES = ("config.mk", "constraint.sdc", "autotuner.json")
SAMPLE_METADATA = {
    "finish__timing__setup__ws": -0.012,
    "finish__timing__setup__tns": -0.04,
    "finish__timing__hold__ws": 0.005,
    "finish__timing__hold__tns": 0.0,
    "finish__power__total": 0.00087,
    "finish__design__instance__area": 2145.3,
    "finish__design__instance__utilization": 37.5,
    "detailedroute__route__drc_errors": 0,
    "finish__runtime__total": 12.5,
}


@dataclass(frozen=True)
class Check:
    name: str
    result: str
    detail: str


def validate(settings: Settings | None = None) -> list[Check]:
    """Return one PASS or FAIL row for every benchmark dependency."""

    active = settings or load_settings()
    checks = [
        _check_orfs_root(),
        _check_flow(active),
    ]
    for design in DESIGNS:
        checks.append(_check_design_files(active, design))
        checks.append(_check_list_params(active, design))
        checks.append(_check_range_detection(active, design))
        checks.append(_check_run_flow(active, design))
    tuner = detect_autotuner(active)
    checks.extend(_autotuner_checks(tuner))
    checks.append(_check_metadata(active))
    checks.append(_check_reports())
    checks.append(_check_framework())
    return checks


def detect_autotuner(settings: Settings) -> dict[str, str | None]:
    """Find openroad_autotuner or an ORFS AutoTuner install.

    The result always includes installed, version, and executable path.
    Missing tools stay empty. No version is invented.
    """

    executable = _autotuner_executable(settings)
    module_origin = _autotuner_module_origin()
    installed = executable is not None or module_origin is not None
    version = _autotuner_version(executable)
    path = executable or module_origin
    return {
        "installed": "yes" if installed else "no",
        "version": version,
        "executable": path,
    }


def render(checks: list[Check]) -> str:
    """Markdown report with a PASS or FAIL for every dependency."""

    lines = [
        "# Benchmark environment validation",
        "",
        f"Checked: {date.today().isoformat()}",
        "",
        "No ORFS finish run and no benchmark sweep was started.",
        "",
        "| Dependency | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        detail = check.detail.replace("|", "/")
        lines.append(f"| {check.name} | {check.result} | {detail} |")
    lines.extend(["", _summary(checks), ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the EDA Pilot benchmark environment."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "environment_validation.md",
    )
    args = parser.parse_args(argv)
    checks = validate()
    text = render(checks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if all(check.result == "PASS" for check in checks) else 1


def _check_orfs_root() -> Check:
    raw = os.environ.get("ORFS_ROOT", "").strip()
    if raw == "":
        return Check(
            "ORFS_ROOT",
            "FAIL",
            "ORFS_ROOT is unset. Point it at an OpenROAD-flow-scripts checkout.",
        )
    path = Path(raw)
    if path.is_dir():
        return Check("ORFS_ROOT", "PASS", str(path))
    return Check("ORFS_ROOT", "FAIL", f"ORFS_ROOT does not exist: {path}")


def _check_flow(settings: Settings) -> Check:
    flow = settings.resolve_flow_dir()
    if flow is not None and flow.is_dir():
        return Check("ORFS flow directory", "PASS", str(flow))
    return Check(
        "ORFS flow directory",
        "FAIL",
        "Set ORFS_ROOT or ORFS_FLOW_DIR to the flow directory that contains designs/.",
    )


def _check_design_files(settings: Settings, design: str) -> Check:
    flow = settings.resolve_flow_dir()
    if flow is None or not flow.is_dir():
        return Check(
            f"{design} design files",
            "FAIL",
            "Flow directory is unavailable, so config.mk, constraint.sdc, and autotuner.json were not found.",
        )
    folder = flow / "designs" / PLATFORM / design
    missing = [name for name in DESIGN_FILES if not (folder / name).is_file()]
    if missing:
        return Check(
            f"{design} design files",
            "FAIL",
            f"Missing {', '.join(missing)} under {folder}.",
        )
    return Check(f"{design} design files", "PASS", str(folder))


def _check_list_params(settings: Settings, design: str) -> Check:
    try:
        listed = list_params(design, PLATFORM, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return Check(f"list_params {design}", "FAIL", str(exc))
    executable = sum(1 for item in listed.parameters if item.executable)
    return Check(
        f"list_params {design}",
        "PASS",
        f"{len(listed.parameters)} parameters, {executable} executable, source {listed.source}.",
    )


def _check_range_detection(settings: Settings, design: str) -> Check:
    flow = settings.resolve_flow_dir()
    live = None if flow is None else flow / "designs" / PLATFORM / design / "autotuner.json"
    try:
        listed = list_params(design, PLATFORM, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return Check(f"autotuner ranges {design}", "FAIL", str(exc))
    if live is not None and live.is_file():
        if listed.source != "ORFS autotuner.json":
            return Check(
                f"autotuner ranges {design}",
                "FAIL",
                f"autotuner.json is present but list_params used {listed.source}.",
            )
        return Check(
            f"autotuner ranges {design}",
            "PASS",
            "list_params tightened the allowlist to the ranges in autotuner.json.",
        )
    return Check(
        f"autotuner ranges {design}",
        "FAIL",
        "autotuner.json is not in the flow tree. The allowlist holds the upstream ranges until that file is present.",
    )


def _check_run_flow(settings: Settings, design: str) -> Check:
    flow = settings.resolve_flow_dir()
    config = None if flow is None else flow / "designs" / PLATFORM / design / "config.mk"
    sdc = None if flow is None else flow / "designs" / PLATFORM / design / "constraint.sdc"
    ready = (
        flow is not None
        and flow.is_dir()
        and config is not None
        and config.is_file()
        and sdc is not None
        and sdc.is_file()
    )
    if ready:
        try:
            list_params(design, PLATFORM, settings=settings)
        except (FlowValidationError, ConfigurationError) as exc:
            return Check(f"run_flow {design}", "FAIL", str(exc))
        return Check(
            f"run_flow {design}",
            "PASS",
            "The design is in the allowlist and config.mk and constraint.sdc are present. finish was not started.",
        )
    try:
        run_flow(design, PLATFORM, None, settings=settings)
    except (FlowValidationError, ConfigurationError) as exc:
        return Check(
            f"run_flow {design}",
            "FAIL",
            f"{exc} finish was not started.",
        )
    return Check(
        f"run_flow {design}",
        "FAIL",
        "run_flow returned without a local design config. finish was not started.",
    )


def _autotuner_checks(found: dict[str, str | None]) -> list[Check]:
    installed = found["installed"] == "yes"
    version = found["version"]
    executable = found["executable"]
    setup = "Install steps are in docs/autotuner_setup.md."
    return [
        Check(
            "AutoTuner detection",
            "PASS",
            "Searched ORFS_AUTOTUNER, PATH, the ORFS AutoTuner virtualenv, and the autotuner.distributed module.",
        ),
        Check(
            "AutoTuner installed",
            "PASS" if installed else "FAIL",
            "openroad_autotuner or autotuner.distributed is available."
            if installed
            else f"AutoTuner is not installed. {setup}",
        ),
        Check(
            "AutoTuner version",
            "PASS" if version else "FAIL",
            version or f"No version command returned a version. {setup}",
        ),
        Check(
            "AutoTuner executable",
            "PASS" if executable else "FAIL",
            executable or f"No executable path was found. {setup}",
        ),
    ]


def _check_metadata(settings: Settings) -> Check:
    parsed = extract_metrics("environment-sample", SAMPLE_METADATA)
    required = ("setup_wns", "hold_wns", "power", "area", "drc_count", "runtime")
    if parsed.missing:
        missing = ", ".join(parsed.missing)
        return Check("metadata generation", "FAIL", f"The metrics parser missed {missing}.")
    for name in required:
        if getattr(parsed, name) is None:
            return Check("metadata generation", "FAIL", f"The metrics parser missed {name}.")
    live = _live_metadata(settings)
    if live is None:
        return Check(
            "metadata generation",
            "FAIL",
            "The metrics parser accepts a METRICS2.1 sample. No metadata.json from ORFS is on disk, and no flow was started.",
        )
    return Check("metadata generation", "PASS", f"Parsed {live}.")


def _check_reports() -> Check:
    sample = "\n".join(
        [
            "setup slack -0.012",
            "hold slack 0.005",
            "DRC violations: 0",
            "congestion overflow: 0",
        ]
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "6_finish.rpt"
        path.write_text(sample + "\n", encoding="utf-8")
        text, count, _truncated = read_tail(path, 200)
    if "setup slack -0.012" not in text or count < 1:
        return Check("report parsing", "FAIL", "read_tail did not return the timing sample.")
    return Check(
        "report parsing",
        "PASS",
        "read_tail returned the timing, DRC, and congestion sample.",
    )


def _check_framework() -> Check:
    modules = (
        "benchmarks.benchmark",
        "benchmarks.run_random",
        "benchmarks.run_autotuner",
        "benchmarks.run_agent",
        "benchmarks.compare_results",
    )
    for name in modules:
        if importlib.util.find_spec(name) is None:
            return Check("benchmark framework", "FAIL", f"Cannot import {name}.")
    return Check(
        "benchmark framework",
        "PASS",
        "benchmark.py, run_random.py, run_autotuner.py, run_agent.py, and compare_results.py import.",
    )


def _autotuner_executable(settings: Settings) -> str | None:
    configured = os.environ.get("ORFS_AUTOTUNER", "").strip()
    if configured and Path(configured).is_file():
        return str(Path(configured))
    found = shutil.which("openroad_autotuner")
    if found:
        return found
    roots: list[Path] = []
    if settings.orfs_root is not None:
        roots.append(settings.orfs_root)
    flow = settings.resolve_flow_dir()
    if flow is not None:
        roots.append(flow.parent)
    names = (
        Path("tools") / "AutoTuner" / "autotuner_env" / "Scripts" / "openroad_autotuner.exe",
        Path("tools") / "AutoTuner" / "autotuner_env" / "bin" / "openroad_autotuner",
    )
    for root in roots:
        for relative in names:
            candidate = root / relative
            if candidate.is_file():
                return str(candidate)
    return None


def _autotuner_module_origin() -> str | None:
    try:
        spec = importlib.util.find_spec("autotuner.distributed")
    except (ModuleNotFoundError, ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    return spec.origin


def _autotuner_version(executable: str | None) -> str | None:
    if executable:
        for extra in (["--version"], ["version"]):
            try:
                completed = subprocess.run(
                    [executable, *extra],
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            line = _first_line(completed.stdout or completed.stderr)
            if line:
                return line
    try:
        return importlib.metadata.version("autotuner")
    except importlib.metadata.PackageNotFoundError:
        return None


def _live_metadata(settings: Settings) -> Path | None:
    flow = settings.resolve_flow_dir()
    if flow is None or not flow.is_dir():
        return None
    for design in DESIGNS:
        root = flow / "reports" / PLATFORM / design
        if not root.is_dir():
            continue
        matches = sorted(path for path in root.rglob("metadata.json") if path.is_file())
        if matches:
            return matches[0]
    return None


def _first_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return None


def _summary(checks: list[Check]) -> str:
    failed = [check.name for check in checks if check.result == "FAIL"]
    if not failed:
        return "Summary: every dependency passed. The benchmark harness can be launched when you choose to start it."
    names = ", ".join(failed)
    return (
        "Summary: list_params is ready for gcd, aes, and ibex where those rows passed. "
        f"Still failing: {names}. "
        "Install the failing tools, then run this script again. "
        "AutoTuner setup is documented in docs/autotuner_setup.md."
    )


if __name__ == "__main__":
    raise SystemExit(main())
