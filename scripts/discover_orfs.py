"""Locate an OpenROAD-flow-scripts checkout and check the benchmark designs.

Windows paths are checked first, including the Ubuntu tree exposed through
\\\\wsl$. A short `wsl` argument list records the git commit and whether the
OpenROAD binary is built. This does not start a flow.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGNS = ("gcd", "aes", "ibex")
DESIGN_FILES = ("config.mk", "constraint.sdc", "autotuner.json")
WSL_DISTRO = "Ubuntu"
WSL_ROOT = "/home/administrator/OpenROAD-flow-scripts"
WINDOWS_CANDIDATES = (
    Path(r"\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts"),
    Path(r"\\wsl.localhost\Ubuntu\home\administrator\OpenROAD-flow-scripts"),
)


@dataclass(frozen=True)
class Check:
    name: str
    result: str
    detail: str


def discover(
    env: dict[str, str] | None = None,
    *,
    root: Path | None = None,
    commit: str | None = None,
    make_path: str | None = None,
    openroad_path: str | None = None,
    search: bool = True,
) -> list[Check]:
    """Return PASS/FAIL rows for the checkout and the three sky130hd designs."""

    values = os.environ if env is None else env
    checks = [_environment_root(values)]
    located = root if root is not None else (_search(values) if search else None)
    if located is None:
        checks.append(
            Check(
                "ORFS checkout",
                "FAIL",
                "No checkout was found in ORFS_ROOT or the Ubuntu WSL path.",
            )
        )
        return checks
    label = str(located)
    commit_text = f", commit {commit}" if commit else ""
    checks.append(Check("ORFS checkout", "PASS", f"{label}{commit_text}"))
    makefile = located / "flow" / "Makefile"
    checks.append(
        Check(
            "flow/Makefile",
            "PASS" if makefile.is_file() else "FAIL",
            str(makefile) if makefile.is_file() else "flow/Makefile is missing.",
        )
    )
    for design in DESIGNS:
        folder = located / "flow" / "designs" / "sky130hd" / design
        checks.append(
            Check(
                f"{design} directory",
                "PASS" if folder.is_dir() else "FAIL",
                str(folder),
            )
        )
        for name in DESIGN_FILES:
            file_path = folder / name
            if file_path.is_file():
                detail = f"{file_path.stat().st_size} bytes"
                result = "PASS"
            else:
                detail = f"{name} is missing."
                result = "FAIL"
            checks.append(Check(f"{design} {name}", result, detail))
    checks.append(
        Check(
            "GNU make in Ubuntu",
            "PASS" if make_path else "FAIL",
            make_path or "make was not found on the Ubuntu PATH.",
        )
    )
    checks.append(
        Check(
            "OpenROAD binary",
            "PASS" if openroad_path else "FAIL",
            openroad_path or "tools/OpenROAD/build/bin/openroad is not built.",
        )
    )
    return checks


def render(checks: list[Check]) -> str:
    lines = [
        "# ORFS discovery",
        "",
        f"Checked: {date.today().isoformat()}",
        "",
        "No ORFS finish run was started.",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        detail = check.detail.replace("|", "/")
        lines.append(f"| {check.name} | {check.result} | {detail} |")
    lines.extend(["", _summary(checks), ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Locate ORFS and check gcd, aes, and ibex.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "orfs_discovery.md",
    )
    args = parser.parse_args(argv)
    root = _search(os.environ)
    checks = discover(
        root=root,
        search=False,
        commit=_wsl_commit(root),
        make_path=_wsl_make(),
        openroad_path=_wsl_openroad(),
    )
    text = render(checks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if all(check.result == "PASS" for check in checks) else 1


def _environment_root(env: dict[str, str]) -> Check:
    raw = env.get("ORFS_ROOT", "").strip()
    if raw == "":
        return Check(
            "ORFS_ROOT environment variable",
            "FAIL",
            "ORFS_ROOT is unset in this Windows process.",
        )
    path = Path(raw)
    if path.is_dir():
        return Check("ORFS_ROOT environment variable", "PASS", str(path))
    return Check(
        "ORFS_ROOT environment variable",
        "FAIL",
        f"ORFS_ROOT does not exist: {path}",
    )


def _search(env: dict[str, str]) -> Path | None:
    raw = env.get("ORFS_ROOT", "").strip()
    if raw and Path(raw).is_dir():
        return Path(raw)
    flow = env.get("ORFS_FLOW_DIR", "").strip()
    if flow and Path(flow).is_dir():
        return Path(flow).parent
    for candidate in WINDOWS_CANDIDATES:
        if candidate.is_dir():
            return candidate
    if _wsl_ok(["test", "-d", WSL_ROOT]):
        return Path(WSL_ROOT)
    return None


def _wsl_commit(root: Path | None) -> str | None:
    linux = _to_linux(root)
    if linux is None:
        return None
    return _wsl_text(["git", "-C", linux, "rev-parse", "--short", "HEAD"])


def _wsl_make() -> str | None:
    return _wsl_text(["bash", "-lc", "command -v make"])


def _wsl_openroad() -> str | None:
    binary = f"{WSL_ROOT}/tools/OpenROAD/build/bin/openroad"
    if _wsl_ok(["test", "-x", binary]):
        return binary
    return None


def _to_linux(root: Path | None) -> str | None:
    if root is None:
        return None
    normalized = str(root).replace("/", "\\").lower()
    for candidate in WINDOWS_CANDIDATES:
        if normalized == str(candidate).replace("/", "\\").lower():
            return WSL_ROOT
    text = str(root).replace("\\", "/")
    if text.startswith(WSL_ROOT):
        return WSL_ROOT
    return _wsl_text(["wslpath", "-u", str(root)])


def _wsl_ok(args: list[str]) -> bool:
    try:
        completed = subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "--", *args],
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _wsl_text(args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "--", *args],
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    line = completed.stdout.strip().splitlines()
    return line[0].strip() if line else None


def _summary(checks: list[Check]) -> str:
    failed = [check.name for check in checks if check.result == "FAIL"]
    design_names = [
        name
        for name in failed
        if any(name.startswith(f"{design} ") or name == f"{design} directory" for design in DESIGNS)
    ]
    if any(check.name == "ORFS checkout" and check.result == "FAIL" for check in checks):
        return "Summary: no OpenROAD-flow-scripts checkout was found. No finish run was started."
    if design_names:
        return "Summary: one or more sky130hd design files are missing. No finish run was started."
    if failed:
        names = ", ".join(failed)
        return (
            "Summary: gcd, aes, and ibex design files passed. "
            f"Still failing: {names}. "
            "No finish run was started."
        )
    return "Summary: the checkout and the three sky130hd designs passed."


if __name__ == "__main__":
    raise SystemExit(main())
