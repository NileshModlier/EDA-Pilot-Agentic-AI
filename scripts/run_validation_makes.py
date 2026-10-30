"""Run the default make goal for aes and ibex, then generate metadata.

The completed stage files stay in place. `finish` is phony only for the
elapsed-time step, and `metadata-generate` writes metadata.json.
"""

from __future__ import annotations

import base64
import subprocess

SCRIPT = r"""
set +e
cd /home/administrator/OpenROAD-flow-scripts/flow
. ../env.sh
echo START_AES
make DESIGN_CONFIG=./designs/sky130hd/aes/config.mk
echo AES_EXIT $?
echo START_IBEX
make DESIGN_CONFIG=./designs/sky130hd/ibex/config.mk
echo IBEX_EXIT $?
for design in gcd aes ibex; do
  echo START_METADATA $design
  make metadata-generate DESIGN_CONFIG=./designs/sky130hd/$design/config.mk
  echo METADATA_EXIT $design $?
done
echo VALIDATION_MAKE_DONE
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
            f"printf '%s' {payload} | base64 -d > /tmp/eda_validate_make.sh && bash /tmp/eda_validate_make.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    print(completed.stdout[-8000:])
    if completed.stderr.strip():
        print(completed.stderr[-2000:])
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
