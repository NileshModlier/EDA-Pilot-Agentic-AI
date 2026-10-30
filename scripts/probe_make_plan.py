"""Show the make dry run and the detailed-route DRC metric."""

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
    route = root / "logs" / "sky130hd" / design / "base" / "5_2_route.json"
    data = json.loads(route.read_text())
    keys = [k for k in data if "drc" in k.lower() or "violation" in k.lower() or "runtime" in k.lower()]
    print("ROUTE", design)
    for key in keys:
        print(f"  {key}={data[key]}")
    drc = root / "reports" / "sky130hd" / design / "base" / "5_route_drc.rpt"
    print("DRC_BYTES", design, drc.stat().st_size)
    report = root / "logs" / "sky130hd" / design / "base" / "6_report.json"
    data = json.loads(report.read_text())
    keys = [k for k in data if "runtime" in k.lower() or "elapsed" in k.lower() or k.endswith("__drt__drc_count")]
    print("FINISH_RUNTIME", design)
    for key in keys:
        print(f"  {key}={data[key]}")
PY
cd "$ROOT/flow"
. ../env.sh
for design in aes ibex; do
  echo "PLAN $design"
  make -n DESIGN_CONFIG=./designs/sky130hd/$design/config.mk 2>/dev/null | head -n 40
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
            f"printf '%s' {payload} | base64 -d > /tmp/eda_plan.sh && bash /tmp/eda_plan.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    print(completed.stdout)
    if completed.stderr.strip():
        print(completed.stderr[-1500:])


if __name__ == "__main__":
    main()
