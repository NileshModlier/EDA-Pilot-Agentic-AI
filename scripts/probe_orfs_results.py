"""Read ORFS tool versions and sky130hd result files. Does not start a flow."""

from __future__ import annotations

import base64
import subprocess

PROBE = r"""
set +e
ROOT=/home/administrator/OpenROAD-flow-scripts
export PATH="$ROOT/tools/install/OpenROAD/bin:$ROOT/tools/install/yosys/bin:$PATH"
echo "ROOT_DIR $(test -d "$ROOT" && echo PASS || echo FAIL)"
echo "OPENROAD_BIN $(test -x "$ROOT/tools/install/OpenROAD/bin/openroad" && echo PASS || echo FAIL)"
echo "OPENROAD_BUILD $(test -x "$ROOT/tools/OpenROAD/build/bin/openroad" && echo PASS || echo FAIL)"
echo "YOSYS_BIN $(test -x "$ROOT/tools/install/yosys/bin/yosys" && echo PASS || echo FAIL)"
echo "KLAYOUT_BIN $(command -v klayout >/dev/null && echo PASS || echo FAIL)"
echo "OPENROAD_VER $(openroad -version 2>/dev/null | head -n 1)"
echo "YOSYS_VER $(yosys -V 2>/dev/null | head -n 1)"
echo "KLAYOUT_VER $(klayout -v 2>/dev/null | head -n 1)"
for design in gcd aes ibex; do
  echo "DESIGN $design"
  for base in results logs reports; do
    dir="$ROOT/flow/$base/sky130hd/$design"
    if [ -d "$dir" ]; then
      echo "TREE $design $base"
      find "$dir" -maxdepth 3 -type d -printf 'DIR %p\n'
      find "$dir" -maxdepth 4 -type f \( -name '6_final.gds' -o -name 'metadata.json' -o -name '1_synth.v' -o -name '2_floorplan.odb' -o -name '3_place.odb' -o -name '4_cts.odb' -o -name '5_route.odb' -o -name '*.gds' \) -printf 'FILE %s %p\n'
    else
      echo "MISSING $design $base"
    fi
  done
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
            f"printf '%s' {payload} | base64 -d > /tmp/eda_probe.sh && bash /tmp/eda_probe.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    print(completed.stdout)
    if completed.returncode != 0:
        print(completed.stderr)
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
