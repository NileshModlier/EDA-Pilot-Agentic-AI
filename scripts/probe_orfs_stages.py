"""Confirm stage logs, synthesis files, and metadata for the three designs."""

from __future__ import annotations

import base64
import subprocess

PROBE = r"""
set +e
ROOT=/home/administrator/OpenROAD-flow-scripts
for design in gcd aes ibex; do
  echo "==== $design ===="
  res="$ROOT/flow/results/sky130hd/$design/base"
  log="$ROOT/flow/logs/sky130hd/$design/base"
  rep="$ROOT/flow/reports/sky130hd/$design/base"
  echo "-- results --"
  ls -1 "$res" 2>/dev/null
  echo "-- logs --"
  ls -1 "$log" 2>/dev/null
  echo "-- reports --"
  ls -1 "$rep" 2>/dev/null
  echo "-- metadata search --"
  find "$ROOT/flow/reports/sky130hd/$design" "$ROOT/flow/logs/sky130hd/$design" -name '*metadata*' -o -name '6_finish.rpt' -o -name '5_route_drc.rpt' 2>/dev/null
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
            f"printf '%s' {payload} | base64 -d > /tmp/eda_stages.sh && bash /tmp/eda_stages.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    print(completed.stdout)
    if completed.stderr.strip():
        print(completed.stderr)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
