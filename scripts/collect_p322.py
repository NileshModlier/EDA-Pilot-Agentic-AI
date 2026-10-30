"""Collect P3.2.2 stage files, metadata, and tool versions from WSL ORFS.

Does not start make and does not change the flow.
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

PROBE = r"""
import json
import shutil
import subprocess
from pathlib import Path

root = Path("/home/administrator/OpenROAD-flow-scripts")
flow = root / "flow"
designs = ["gcd", "aes", "ibex"]
stage_files = {
    "synthesis_netlist": "1_2_yosys.v",
    "synthesis_odb": "1_synth.odb",
    "floorplan_odb": "2_floorplan.odb",
    "placement_odb": "3_place.odb",
    "cts_odb": "4_cts.odb",
    "route_odb": "5_route.odb",
    "final_gds": "6_final.gds",
    "merged_gds": "6_1_merged.gds",
}
report_files = ["6_finish.rpt", "5_route_drc.rpt", "5_global_route.rpt", "metadata.json"]
aliases = [
    "finish__timing__setup__ws",
    "finish__timing__setup__wns",
    "finish__timing__hold__ws",
    "finish__timing__hold__wns",
    "finish__power__total",
    "finish__design__instance__area",
    "finish__design__core__area",
    "detailedroute__route__drc_errors",
    "finish__drt__drc_count",
    "detailedroute__route__drc_count",
    "finish__runtime__total",
    "run__flow__runtime__total",
    "total_time",
]
windows_stage = Path("/mnt/c/Users/Administrator/EDA Pilot AI/results/_p322_stage")
windows_stage.mkdir(parents=True, exist_ok=True)

def tool_version(argv):
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": argv, "ok": False, "error": str(exc)}
    text = (completed.stdout or "") + (completed.stderr or "")
    return {
        "argv": argv,
        "ok": completed.returncode == 0,
        "code": completed.returncode,
        "which": shutil.which(argv[0]),
        "text": text.strip()[:500],
    }

out = {
    "tools": {
        "openroad": tool_version(["openroad", "-version"]),
        "yosys": tool_version(["yosys", "-V"]),
        "klayout": tool_version(["klayout", "-b", "-v"]),
        "make": tool_version(["make", "--version"]),
    },
    "designs": {},
}
for design in designs:
    results = flow / "results" / "sky130hd" / design / "base"
    reports = flow / "reports" / "sky130hd" / design / "base"
    logs = flow / "logs" / "sky130hd" / design / "base"
    files = {}
    for label, name in stage_files.items():
        path = results / name
        files[label] = {
            "path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
        }
    synth_log = logs / "1_2_yosys.log"
    synth_text = synth_log.read_text(errors="replace") if synth_log.is_file() else ""
    meta_path = reports / "metadata.json"
    meta = {}
    meta_error = None
    if meta_path.is_file():
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            payload = None
            meta_error = str(exc)
        if isinstance(payload, dict):
            for key in aliases:
                if key in payload:
                    meta[key] = payload[key]
            # genMetrics sometimes nests; keep a flat scan too
            def walk(node, prefix=""):
                if not isinstance(node, dict):
                    return
                for key, value in node.items():
                    name = f"{prefix}__{key}" if prefix else key
                    if isinstance(value, dict):
                        walk(value, name)
                    elif name in aliases or name.endswith("__drc_errors"):
                        meta[name] = value
            walk(payload)
        shutil.copy2(meta_path, windows_stage / f"{design}_metadata.json")
    copied = []
    for name in report_files:
        source = reports / name
        if source.is_file():
            target = windows_stage / design / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append({"name": name, "bytes": source.stat().st_size})
    out["designs"][design] = {
        "files": files,
        "synth_log_bytes": synth_log.stat().st_size if synth_log.is_file() else 0,
        "synth_end": "End of script" in synth_text,
        "metadata_bytes": meta_path.stat().st_size if meta_path.is_file() else 0,
        "metadata_error": meta_error,
        "metrics": meta,
        "copied": copied,
    }
Path("/tmp/p322_collect.json").write_text(json.dumps(out))
print("COLLECT_OK")
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
            "source /home/administrator/OpenROAD-flow-scripts/env.sh && "
            f"printf '%s' {payload} | base64 -d > /tmp/p322_collect.py && "
            "python3 /tmp/p322_collect.py && base64 -w 0 /tmp/p322_collect.json",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        raise SystemExit(completed.returncode)
    lines = [line for line in completed.stdout.splitlines() if line and line != "COLLECT_OK"]
    data = json.loads(base64.b64decode(lines[-1]))
    dest = Path("results")
    dest.mkdir(exist_ok=True)
    (dest / "p322_collect.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2)[:12000])


if __name__ == "__main__":
    main()
