"""Launch the WSL OpenROAD AutoTuner from the Windows benchmark harness."""

from __future__ import annotations

import subprocess
import sys

DISTRO = "Ubuntu"
FLOW = "/home/administrator/OpenROAD-flow-scripts/flow"
BINARY = (
    "/home/administrator/OpenROAD-flow-scripts/tools/AutoTuner/"
    "autotuner_env/bin/openroad_autotuner"
)
_PREFIXES = (
    "\\\\wsl$\\ubuntu\\",
    "\\\\wsl.localhost\\ubuntu\\",
)


def to_linux(value: str) -> str:
    """Turn a WSL UNC path into the Linux path AutoTuner can open."""

    normalized = value.replace("/", "\\")
    lowered = normalized.lower()
    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            rest = normalized[len(prefix) :].replace("\\", "/")
            return "/" + rest
    return value


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def main() -> int:
    translated = [to_linux(argument) for argument in sys.argv[1:]]
    script = (
        "set -eu; "
        f"cd {_quote(FLOW)}; "
        ". ../env.sh >/dev/null; "
        f"exec {_quote(BINARY)} {' '.join(_quote(argument) for argument in translated)}"
    )
    completed = subprocess.run(
        ["wsl.exe", "-d", DISTRO, "--", "bash", "-lc", script],
        cwd=r"C:\Windows",
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
