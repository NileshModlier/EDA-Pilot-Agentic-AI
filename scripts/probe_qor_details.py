"""Read DRC, runtime, and whether make considers aes and ibex up to date."""

from __future__ import annotations

import base64
import subprocess

PROBE = r"""
set +e
ROOT=/home/administrator/OpenROAD-flow-scripts
python3 - <<'PY'
import json
from pathlib import Path
root = Path("/home/administrator/OpenROAD-flow-scripts/flow")
for design in ("gcd", "aes", "ibex"):
    data = json.loads((root / "logs" / "sky130hd" / design / "base" / "6_report.json").read_text())
    keys = [k for k in data if any(s in k.lower() for s in ("drc", "runtime", "elapsed", "violation"))]
    print("KEYS", design)
    for key in keys:
        print(f"  {key}={data[key]}")
    drc = (root / "reports" / "sky130hd" / design / "base" / "5_route_drc.rpt").read_text(errors="replace")
    lines = [line.strip() for line in drc.splitlines() if line.strip()]
    print("DRC_LINES", design, len(lines))
    for line in lines[-12:]:
        print("  ", line[:200])
PY
cd "$ROOT/flow"
. ../env.sh
for design in aes ibex gcd; do
  make -q DESIGN_CONFIG=./designs/sky130hd/$design/config.mk
  echo "MAKE_Q $design $?"
done
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
            f"printf '%s' {payload} | base64 -d > /tmp/eda_qor.sh && bash /tmp/eda_qor.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    print(completed.stdout)
    if completed.stderr.strip():
        print(completed.stderr[-2000:])
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
