"""Launch one validated OpenROAD Flow Scripts finish run.

The process is started with ``shell=False`` and an argument list built only
from the allowlist. There is no caller-supplied command. When the checkout is
a WSL path and GNU make is the launcher, the same argument list is executed
inside that distro.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from eda_pilot.config import Settings, load_settings
from eda_pilot.models import RunManifest, RunResult
from mcp_tools.validation import (
    DESIGN_RE,
    RUN_ID_RE,
    VARIANT_RE,
    FlowValidationError,
    validate_params,
)

CONFIG_TOKEN_RE = re.compile(
    r"^DESIGN_CONFIG=\./designs/[a-z][a-z0-9_]*/[a-z][a-z0-9_]*/config\.mk$"
)
ASSIGNMENT_RE = re.compile(r"^[A-Z][A-Z0-9_]*=[0-9]+(?:\.[0-9]+)?$")
SDC_ASSIGNMENT_RE = re.compile(
    r"^SDC_FILE=\.eda_pilot/sdc/[0-9a-f]{32}/constraint\.sdc$"
)
VARIANT_TOKEN_RE = re.compile(r"^FLOW_VARIANT=p1[0-9a-f]{32}$")
CLK_PERIOD_RE = re.compile(r"^(\s*set\s+clk_period\s+)([0-9]+(?:\.[0-9]+)?)\s*$")
LOG_LIMIT = 5_000_000


def run_flow(
    design: str,
    platform: str,
    params: object = None,
    *,
    settings: Settings | None = None,
) -> RunResult:
    """Validate parameters, then execute ORFS with a unique FLOW_VARIANT."""

    active = settings or load_settings()
    validated = validate_params(design, platform, params, settings=active)
    flow = _require_flow(active)
    _require_design_config(flow, validated.design, validated.platform)

    run_id = uuid.uuid4().hex
    variant = f"p1{run_id}"
    if VARIANT_RE.fullmatch(variant) is None:
        raise FlowValidationError("validation error: refused to build an unsafe FLOW_VARIANT")
    sdc_relative = (
        f".eda_pilot/sdc/{run_id}/constraint.sdc" if validated.clock_period is not None else None
    )
    argv = build_make_argv(
        active,
        flow,
        validated.design,
        validated.platform,
        variant,
        validated.make_values,
        sdc_relative,
    )
    launch_argv, launch_cwd = prepare_launch(argv, flow)
    _reserve_budget(active)

    run_dir = active.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    if validated.clock_period is not None:
        written = _write_private_sdc(
            flow,
            validated.design,
            validated.platform,
            run_id,
            validated.clock_period,
        )
        if written != sdc_relative:
            raise FlowValidationError("validation error: refused to build an unsafe SDC path")
    _write_manifest(
        run_dir,
        RunManifest(
            run_id=run_id,
            design=validated.design,
            platform=validated.platform,
            flow_variant=variant,
            status="running",
            params=validated.recorded_params,
        ),
    )

    started = time.perf_counter()
    code, stdout, stderr, timed_out = _execute(launch_argv, launch_cwd, active.timeout_seconds)
    runtime = round(time.perf_counter() - started, 3)
    _write_log(run_dir / "stdout.log", stdout)
    _write_log(run_dir / "stderr.log", stderr)

    if timed_out:
        status = "timeout"
        message = f"flow exceeded timeout of {active.timeout_seconds:g} seconds"
    elif code == 0:
        status = "ok"
        message = None
    else:
        status = "error"
        message = f"ORFS exited with status {code}"

    _write_manifest(
        run_dir,
        RunManifest(
            run_id=run_id,
            design=validated.design,
            platform=validated.platform,
            flow_variant=variant,
            status=status,
            runtime=runtime,
            params=validated.recorded_params,
            message=message,
        ),
    )
    return RunResult(
        run_id=run_id,
        status=status,
        runtime=runtime,
        flow_variant=variant,
        message=message,
    )


def load_manifest(run_id: str, settings: Settings | None = None) -> RunManifest:
    """Load a run record addressed only by a server-generated id."""

    active = settings or load_settings()
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise FlowValidationError(
            f"validation error: unknown run_id '{_public_run_id(run_id)}'"
        )
    runs_root = active.runs_dir.resolve()
    manifest_path = (runs_root / run_id / "manifest.json").resolve()
    try:
        manifest_path.relative_to(runs_root)
    except ValueError as exc:
        raise FlowValidationError(
            "validation error: unknown run_id '<rejected>'"
        ) from exc
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise FlowValidationError(f"validation error: unknown run_id '{run_id}'")
    try:
        manifest = RunManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise FlowValidationError(
            f"validation error: run '{run_id}' has an unreadable manifest"
        ) from exc
    if manifest.run_id != run_id:
        raise FlowValidationError(f"validation error: unknown run_id '{run_id}'")
    if DESIGN_RE.fullmatch(manifest.design) is None or DESIGN_RE.fullmatch(manifest.platform) is None:
        raise FlowValidationError(
            f"validation error: run '{run_id}' has an invalid manifest"
        )
    if VARIANT_RE.fullmatch(manifest.flow_variant) is None:
        raise FlowValidationError(
            f"validation error: run '{run_id}' has an invalid manifest"
        )
    return manifest


def build_make_argv(
    settings: Settings,
    flow: Path,
    design: str,
    platform: str,
    variant: str,
    make_values: dict[str, str],
    sdc_relative: str | None,
) -> list[str]:
    """Build the fixed ORFS argument list. This is not a shell command."""

    if settings.orfs_target != "finish":
        raise FlowValidationError("validation error: refused to run an unapproved ORFS target")
    if any(character in str(flow) for character in "\r\n\x00"):
        raise FlowValidationError("validation error: ORFS flow path is not usable")
    config_token = f"DESIGN_CONFIG=./designs/{platform}/{design}/config.mk"
    variant_token = f"FLOW_VARIANT={variant}"
    if CONFIG_TOKEN_RE.fullmatch(config_token) is None:
        raise FlowValidationError("validation error: refused to build an unsafe design config path")
    if VARIANT_TOKEN_RE.fullmatch(variant_token) is None:
        raise FlowValidationError("validation error: refused to build an unsafe FLOW_VARIANT")

    prefix = settings.command_prefix()
    for part in prefix:
        if not isinstance(part, str) or part == "" or any(ch in part for ch in "\r\n\x00"):
            raise FlowValidationError("validation error: ORFS make executable is not usable")

    argv = [*prefix, "-C", str(flow), config_token, variant_token]
    for name in sorted(make_values):
        token = f"{name}={make_values[name]}"
        if ASSIGNMENT_RE.fullmatch(token) is None:
            raise FlowValidationError("validation error: refused to build an unsafe make argument")
        argv.append(token)
    if sdc_relative is not None:
        sdc_token = f"SDC_FILE={sdc_relative}"
        if SDC_ASSIGNMENT_RE.fullmatch(sdc_token) is None:
            raise FlowValidationError("validation error: refused to build an unsafe SDC path")
        argv.append(sdc_token)
    argv.append("finish")
    return argv


_MAKE_NAMES = {"make", "make.exe"}
_WSL_UNC_RE = re.compile(
    r"^\\\\wsl(?:\$|\.localhost)\\([A-Za-z0-9._-]+)\\(.+)$",
    re.IGNORECASE,
)
_SAFE_BASH_TOKEN_RE = re.compile(r"^[A-Za-z0-9_./=+,-]+$")


def prepare_launch(argv: list[str], flow: Path) -> tuple[list[str], Path]:
    """Return the argv and cwd used to start this flow.

    A normal ``make`` invocation is unchanged. A Windows process whose flow
    directory is ``\\\\wsl$\\<distro>\\...`` runs that make inside the distro.
    """

    if os.name != "nt" or not argv or Path(argv[0]).name.lower() not in _MAKE_NAMES:
        return argv, flow
    located = locate_wsl_flow(flow)
    if located is None:
        return argv, flow
    distro, linux_flow = located
    wsl_executable = shutil.which("wsl")
    if wsl_executable is None or not _wsl_flow_ready(wsl_executable, distro, linux_flow):
        raise FlowValidationError(
            "validation error: WSL OpenROAD-flow-scripts checkout was not found "
            f"at {linux_flow}"
        )
    return (
        translate_wsl_launch(
            argv,
            wsl_executable=wsl_executable,
            distro=distro,
            linux_flow=linux_flow,
        ),
        _windows_launch_cwd(),
    )


def locate_wsl_flow(flow: Path) -> tuple[str, str] | None:
    """Map a ``\\\\wsl$\\<distro>\\...`` flow directory to its Linux path."""

    match = _WSL_UNC_RE.match(str(flow))
    if match is None:
        return None
    distro = match.group(1)
    linux_flow = "/" + match.group(2).replace("\\", "/").strip("/")
    if _SAFE_BASH_TOKEN_RE.fullmatch(linux_flow) is None:
        raise FlowValidationError("validation error: WSL flow path is not usable")
    if _SAFE_BASH_TOKEN_RE.fullmatch(distro) is None:
        raise FlowValidationError("validation error: WSL distro name is not usable")
    return distro, linux_flow


def translate_wsl_launch(
    argv: list[str],
    *,
    wsl_executable: str,
    distro: str,
    linux_flow: str,
) -> list[str]:
    """Build ``wsl.exe -d <distro> -- bash -lc <script>`` from a make argv."""

    if _SAFE_BASH_TOKEN_RE.fullmatch(distro) is None:
        raise FlowValidationError("validation error: WSL distro name is not usable")
    if _SAFE_BASH_TOKEN_RE.fullmatch(linux_flow) is None:
        raise FlowValidationError("validation error: WSL flow path is not usable")
    make_args = _retarget_make(argv, linux_flow)
    if not make_args or make_args[-1] != "finish":
        raise FlowValidationError("validation error: refused to build an unsafe WSL flow command")
    finish = " ".join(_quote_bash(token) for token in make_args)
    metadata = " ".join(_quote_bash(token) for token in [*make_args[:-1], "metadata-generate"])
    script = (
        f"set -eu; cd {_quote_bash(linux_flow)}; . ../env.sh; {finish}; {metadata}"
    )
    return [wsl_executable, "-d", distro, "--", "bash", "-lc", script]


def _retarget_make(argv: list[str], linux_flow: str) -> list[str]:
    if len(argv) >= 3 and argv[1] == "-C":
        tail = argv[3:]
    else:
        tail = argv[1:]
    return ["make", "-C", linux_flow, *tail]


def _quote_bash(token: str) -> str:
    if _SAFE_BASH_TOKEN_RE.fullmatch(token) is None:
        raise FlowValidationError("validation error: refused to build an unsafe WSL flow command")
    return "'" + token + "'"


def _wsl_flow_ready(wsl_executable: str, distro: str, linux_flow: str) -> bool:
    try:
        completed = subprocess.run(
            [wsl_executable, "-d", distro, "--", "test", "-f", f"{linux_flow}/Makefile"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            shell=False,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _windows_launch_cwd() -> Path:
    system_root = os.environ.get("SystemRoot")
    if system_root and Path(system_root).is_dir():
        return Path(system_root)
    return Path.cwd()


def _require_flow(settings: Settings) -> Path:
    flow = settings.resolve_flow_dir()
    if flow is None:
        raise FlowValidationError(
            "validation error: ORFS is not configured. "
            "Set ORFS_ROOT to an OpenROAD-flow-scripts checkout."
        )
    resolved = flow.resolve()
    if not resolved.is_dir():
        raise FlowValidationError(
            "validation error: ORFS flow directory does not exist. "
            "Set ORFS_ROOT to an OpenROAD-flow-scripts checkout."
        )
    return resolved


def _require_design_config(flow: Path, design: str, platform: str) -> None:
    config = (flow / "designs" / platform / design / "config.mk").resolve()
    try:
        config.relative_to((flow / "designs").resolve())
    except ValueError as exc:
        raise FlowValidationError(
            "validation error: design config is outside the flow designs directory"
        ) from exc
    if config.is_symlink() or not config.is_file():
        raise FlowValidationError(
            f"validation error: design config not found for {design}/{platform}"
        )


def _write_private_sdc(
    flow: Path,
    design: str,
    platform: str,
    run_id: str,
    period: str,
) -> str:
    """Copy the design SDC and replace only the literal clock period."""

    source = (flow / "designs" / platform / design / "constraint.sdc").resolve()
    try:
        source.relative_to((flow / "designs").resolve())
    except ValueError as exc:
        raise FlowValidationError(
            "validation error: design SDC is outside the flow designs directory"
        ) from exc
    if source.is_symlink() or not source.is_file():
        raise FlowValidationError(
            "validation error: design SDC was not found; refusing to invent a clock constraint"
        )
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    indexes = [
        index
        for index, line in enumerate(lines)
        if CLK_PERIOD_RE.fullmatch(line.rstrip("\r\n"))
    ]
    if len(indexes) != 1:
        raise FlowValidationError(
            "validation error: design SDC must contain exactly one "
            "'set clk_period <number>' line"
        )
    matched = CLK_PERIOD_RE.fullmatch(lines[indexes[0]].rstrip("\r\n"))
    if matched is None:
        raise FlowValidationError(
            "validation error: design SDC must contain exactly one "
            "'set clk_period <number>' line"
        )
    newline = "\n" if lines[indexes[0]].endswith("\n") else ""
    lines[indexes[0]] = f"{matched.group(1)}{period}{newline}"

    relative = f".eda_pilot/sdc/{run_id}/constraint.sdc"
    if SDC_ASSIGNMENT_RE.fullmatch(f"SDC_FILE={relative}") is None:
        raise FlowValidationError("validation error: refused to build an unsafe SDC path")
    destination = (flow / Path(relative)).resolve()
    try:
        destination.relative_to((flow / ".eda_pilot").resolve())
    except ValueError as exc:
        raise FlowValidationError(
            "validation error: refusing to write the private SDC outside the flow directory"
        ) from exc
    destination.parent.mkdir(parents=True, exist_ok=False)
    destination.write_text("".join(lines), encoding="utf-8")
    return relative


def _reserve_budget(settings: Settings) -> None:
    count_path = settings.runs_dir / "budget_count"
    with _budget_lock(settings.runs_dir, settings.timeout_seconds + 30):
        count = 0
        if count_path.is_file():
            text = count_path.read_text(encoding="utf-8").strip()
            if text.isdigit():
                count = int(text)
        if count >= settings.max_runs:
            raise FlowValidationError(
                f"validation error: run budget exceeded (limit {settings.max_runs})"
            )
        settings.runs_dir.mkdir(parents=True, exist_ok=True)
        count_path.write_text(str(count + 1), encoding="utf-8")


@contextmanager
def _budget_lock(runs_dir: Path, stale_after: float):
    runs_dir.mkdir(parents=True, exist_ok=True)
    lock_path = runs_dir / ".budget.lock"
    deadline = time.monotonic() + 10
    lock_fd: int | None = None
    while lock_fd is None:
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > stale_after:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() > deadline:
                raise FlowValidationError(
                    "validation error: could not acquire the run budget lock"
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(lock_fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _execute(argv: list[str], cwd: Path, timeout: float) -> tuple[int, bytes, bytes, bool]:
    popen_kwargs: dict[str, object] = {
        "args": argv,
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "shell": False,
        "env": os.environ.copy(),
    }
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(**popen_kwargs)  # noqa: S603 - argv is an allowlisted list, shell is off
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        code = proc.returncode if proc.returncode is not None else 1
        return code, stdout or b"", stderr or b"", False
    except subprocess.TimeoutExpired:
        _kill_tree(proc.pid)
        try:
            stdout, stderr = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        code = proc.returncode if proc.returncode is not None else -1
        return code, stdout or b"", stderr or b"", True


def _kill_tree(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(int(pid))],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            shell=False,
            check=False,
        )
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return


def _write_manifest(run_dir: Path, manifest: RunManifest) -> None:
    temporary = run_dir / "manifest.json.tmp"
    temporary.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(run_dir / "manifest.json")


def _write_log(path: Path, data: bytes) -> None:
    path.write_bytes(data[-LOG_LIMIT:])


def _public_run_id(value: object) -> str:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value):
        return value
    return "<rejected>"
