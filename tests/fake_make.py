"""Stand-in for GNU make used only by the unit tests.

The MCP server never shells out. Tests set ``Settings.make_prefix`` to this
interpreter and script so ``run_flow`` can be exercised without OpenROAD.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "-C":
        flow = Path(args[1])
        rest = args[2:]
    else:
        flow = Path.cwd()
        rest = args

    record = flow / ".eda_pilot"
    record.mkdir(parents=True, exist_ok=True)
    (record / "last_argv.json").write_text(json.dumps(sys.argv), encoding="utf-8")

    sleep_file = flow / ".fake_sleep_seconds"
    if sleep_file.is_file():
        time.sleep(float(sleep_file.read_text(encoding="utf-8").strip()))

    assignments: dict[str, str] = {}
    targets: list[str] = []
    for arg in rest:
        if "=" in arg:
            key, value = arg.split("=", 1)
            assignments[key] = value
        else:
            targets.append(arg)

    pieces = [
        piece
        for piece in assignments.get("DESIGN_CONFIG", "").replace("\\", "/").split("/")
        if piece not in {"", "."}
    ]
    platform = pieces[-3]
    design = pieces[-2]
    variant = assignments["FLOW_VARIANT"]
    report_dir = flow / "reports" / platform / design / variant
    report_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "finish__timing__setup__ws": -0.012,
        "finish__timing__setup__tns": -0.04,
        "finish__timing__hold__ws": 0.005,
        "finish__timing__hold__tns": 0.0,
        "finish__power__total": 0.00087,
        "finish__design__instance__area": 2145.3,
        "finish__design__instance__utilization": 37.5,
        "detailedroute__route__drc_errors": 0,
        "finish__runtime__total": 12.5,
    }
    (report_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    timing_lines = [f"noise line {index}" for index in range(250)]
    timing_lines.append("setup slack -0.012")
    timing_lines.append("hold slack 0.005")
    (report_dir / "6_finish.rpt").write_text("\n".join(timing_lines) + "\n", encoding="utf-8")
    (report_dir / "5_route_drc.rpt").write_text("DRC violations: 0\n", encoding="utf-8")
    (report_dir / "5_global_route.rpt").write_text("congestion overflow: 0\n", encoding="utf-8")

    print("ORFS finish starting")
    print("ORFS finish done")
    print("warning: fake flow", file=sys.stderr)

    code_file = flow / ".fake_exit_code"
    if code_file.is_file():
        return int(code_file.read_text(encoding="utf-8").strip())
    if targets != ["finish"]:
        print(f"unexpected targets: {targets}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
