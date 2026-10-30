"""Record openroad -version and whether a gcd metadata.json exists.

Does not compile OpenROAD and does not start make.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_ROOT = Path(r"\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts")
BUILD_BIN = "/home/administrator/OpenROAD-flow-scripts/tools/OpenROAD/build/bin/openroad"
INSTALL_BIN = "/home/administrator/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"


def smoke() -> list[tuple[str, str, str]]:
    rows = []
    for label, binary in (("build tree", BUILD_BIN), ("install tree", INSTALL_BIN)):
        if _wsl_ok(["test", "-x", binary]):
            version = _wsl_text([binary, "-version"]) or "version command returned no text"
            rows.append((f"openroad -version ({label})", "PASS", version))
        else:
            rows.append(
                (
                    f"openroad -version ({label})",
                    "FAIL",
                    f"{binary} is not executable. -version was not run.",
                )
            )
    metadata = _metadata_files()
    if metadata:
        rows.append(("gcd metadata.json", "PASS", metadata[0]))
    else:
        rows.append(
            (
                "gcd metadata.json",
                "FAIL",
                "No metadata.json under flow/reports/sky130hd/gcd. The gcd flow was not started.",
            )
        )
    return rows


def render(rows: list[tuple[str, str, str]]) -> str:
    lines = [
        "# OpenROAD smoke test",
        "",
        f"Checked: {date.today().isoformat()}",
        "",
        "The OpenROAD binary is absent, so the version command and the gcd flow were not started.",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for name, result, detail in rows:
        lines.append(f"| {name} | {result} | {detail.replace('|', '/')} |")
    failed = [name for name, result, _detail in rows if result == "FAIL"]
    if failed:
        summary = "Summary: smoke test failed. Missing: " + ", ".join(failed) + "."
    else:
        summary = "Summary: openroad -version and gcd metadata.json passed."
    lines.extend(["", summary, ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-check OpenROAD without starting a flow.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "openroad_smoke_test.md",
    )
    args = parser.parse_args(argv)
    text = render(smoke())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if "FAIL" not in text else 1


def _metadata_files() -> list[str]:
    root = WINDOWS_ROOT / "flow" / "reports" / "sky130hd" / "gcd"
    if not root.is_dir():
        return []
    return [str(path) for path in root.rglob("metadata.json") if path.is_file()]


def _wsl_ok(args: list[str]) -> bool:
    try:
        completed = subprocess.run(
            ["wsl", "-d", "Ubuntu", "--", *args],
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
            ["wsl", "-d", "Ubuntu", "--", *args],
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


if __name__ == "__main__":
    raise SystemExit(main())
