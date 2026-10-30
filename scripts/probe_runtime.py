"""Read the finish log runtime table for gcd, aes, and ibex."""

from __future__ import annotations

import base64
import subprocess

PROBE = r"""
from pathlib import Path
root = Path("/home/administrator/OpenROAD-flow-scripts/flow/logs/sky130hd")
for design in ("gcd", "aes", "ibex"):
    text = (root / design / "base" / "6_report.log").read_text(errors="replace")
    lines = text.splitlines()
    print("====", design, "lines", len(lines))
    for line in lines[-25:]:
        print(line)
"""


def main() -> None:
    payload = base64.b64encode(PROBE.replace("\r\n", "\n").encode()).decode()
    completed = subprocess.run(
        [
            "wsl",
            "-d",
            "Ubuntu",
            "--",
            "bash",
            "-lc",
            f"printf '%s' {payload} | base64 -d | python3",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    print(completed.stdout)
    if completed.returncode != 0:
        print(completed.stderr[-1000:])


if __name__ == "__main__":
    main()
