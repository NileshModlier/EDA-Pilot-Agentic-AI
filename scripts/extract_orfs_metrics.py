"""Pull QoR fields from completed sky130hd base runs. Does not start make."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

PROBE = r"""
import json
from pathlib import Path
root = Path("/home/administrator/OpenROAD-flow-scripts/flow")
designs = ["gcd", "aes", "ibex"]
out = {}
for design in designs:
    report = root / "reports" / "sky130hd" / design / "base" / "6_finish.rpt"
    drc = root / "reports" / "sky130hd" / design / "base" / "5_route_drc.rpt"
    metrics = root / "logs" / "sky130hd" / design / "base" / "6_report.json"
    gds = root / "results" / "sky130hd" / design / "base" / "6_final.gds"
    payload = {}
    if metrics.is_file():
        data = json.loads(metrics.read_text())
        payload["metrics_keys"] = sorted(data)[:80]
        payload["metrics_count"] = len(data)
        wanted = [k for k in data if any(s in k for s in (
            "timing__setup__ws", "timing__hold__ws", "power__total",
            "instance__area", "drc", "runtime__total", "wns", "tns"
        ))]
        payload["wanted"] = {k: data[k] for k in wanted}
    payload["gds_bytes"] = gds.stat().st_size if gds.is_file() else 0
    payload["finish_tail"] = "\n".join(report.read_text(errors="replace").splitlines()[-30:]) if report.is_file() else ""
    payload["drc_tail"] = "\n".join(drc.read_text(errors="replace").splitlines()[-20:]) if drc.is_file() else ""
    synth = root / "logs" / "sky130hd" / design / "base" / "1_2_yosys.log"
    text = synth.read_text(errors="replace") if synth.is_file() else ""
    payload["synth_ok"] = "End of script" in text or "Yosys" in text
    payload["synth_tail"] = "\n".join(text.splitlines()[-8:])
    out[design] = payload
Path("/tmp/eda_metrics.json").write_text(json.dumps(out))
print("WROTE", len(out))
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
            f"printf '%s' {payload} | base64 -d > /tmp/eda_metrics.py && python3 /tmp/eda_metrics.py && base64 -w 0 /tmp/eda_metrics.json",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        raise SystemExit(completed.returncode)
    lines = [line for line in completed.stdout.splitlines() if line and not line.startswith("WROTE")]
    raw = lines[-1]
    data = json.loads(base64.b64decode(raw))
    dest = Path("results")
    dest.mkdir(exist_ok=True)
    (dest / "orfs_raw_metrics.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for design, payload in data.items():
        print("====", design, "gds", payload.get("gds_bytes"), "keys", payload.get("metrics_count"))
        print("WANTED", json.dumps(payload.get("wanted"), indent=2)[:2000])
        print("SYNTH", payload.get("synth_ok"))
        print(payload.get("synth_tail"))
        print("--- finish ---")
        print(payload.get("finish_tail")[-800:])
        print("--- drc ---")
        print(payload.get("drc_tail")[-500:])


if __name__ == "__main__":
    main()
