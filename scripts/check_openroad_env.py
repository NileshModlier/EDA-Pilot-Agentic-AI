"""Check Ubuntu build tools and the OpenROAD binary. Does not compile or run a flow."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WSL_DISTRO = "Ubuntu"
WSL_ROOT = "/home/administrator/OpenROAD-flow-scripts"
TOOLS = (
    ("make", "make"),
    ("python3", "python3"),
    ("cmake", "cmake"),
    ("gcc", "gcc"),
    ("g++", "g++"),
    ("swig", "swig"),
    ("tcl", "tclsh"),
    ("git", "git"),
)
OPENROAD_BIN = f"{WSL_ROOT}/tools/OpenROAD/build/bin/openroad"


def dependency_rows() -> list[dict[str, str]]:
    rows = []
    for label, command in TOOLS:
        located = _wsl_text(["bash", "-lc", f"command -v {command}"])
        version = ""
        if located:
            version = _wsl_text(["bash", "-lc", f"{command} --version 2>/dev/null | head -n 1"]) or ""
        rows.append(
            {
                "name": label,
                "result": "PASS" if located else "FAIL",
                "path": located or "",
                "version": version,
            }
        )
    return rows


def openroad_status() -> dict[str, str]:
    if _wsl_ok(["test", "-x", OPENROAD_BIN]):
        version = _wsl_text([OPENROAD_BIN, "-version"]) or ""
        return {"result": "PASS", "path": OPENROAD_BIN, "version": version}
    return {
        "result": "FAIL",
        "path": OPENROAD_BIN,
        "version": "",
    }


def write_dependency_report(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# OpenROAD dependency check",
        "",
        f"Checked: {date.today().isoformat()}",
        "",
        "Host: Ubuntu on WSL. No packages were installed and no build was started.",
        "",
        "| Tool | Result | Path | Version |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        version = row["version"].replace("|", "/") or "not reported"
        location = row["path"] or "not found"
        lines.append(f"| {row['name']} | {row['result']} | {location} | {version} |")
    failed = [row["name"] for row in rows if row["result"] == "FAIL"]
    if failed:
        summary = "Summary: missing " + ", ".join(failed) + "."
    else:
        summary = "Summary: every listed build tool is present."
    lines.extend(["", summary, ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check OpenROAD build dependencies in Ubuntu.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "openroad_dependencies.md",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    rows = dependency_rows()
    binary = openroad_status()
    write_dependency_report(args.out, rows)
    payload = {"dependencies": rows, "openroad": binary}
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"), end="")
    print(f"OpenROAD binary: {binary['result']} {binary['path']}")
    if binary["version"]:
        print(binary["version"])
    return 0 if all(row["result"] == "PASS" for row in rows) else 1


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
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


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


if __name__ == "__main__":
    raise SystemExit(main())
