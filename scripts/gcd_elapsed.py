"""Reprint the gcd elapsed table. Does not rebuild completed stages."""

from __future__ import annotations

import base64
import subprocess

SCRIPT = r"""
set +e
cd /home/administrator/OpenROAD-flow-scripts/flow
. ../env.sh
echo START_GCD
make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk
echo GCD_EXIT $?
"""


def main() -> None:
    payload = base64.b64encode(SCRIPT.replace("\r\n", "\n").encode()).decode()
    completed = subprocess.run(
        [
            "wsl",
            "-d",
            "Ubuntu",
            "--",
            "bash",
            "-lc",
            f"printf '%s' {payload} | base64 -d > /tmp/eda_gcd_elapsed.sh && bash /tmp/eda_gcd_elapsed.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    print(completed.stdout[-4000:])
    if completed.stderr.strip():
        print(completed.stderr[-1500:])
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
