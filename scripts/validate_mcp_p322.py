"""Call the existing MCP tools against the P3.2.2 sky130hd results.

Does not change tool code. A live run_flow is issued only when the configured
flow directory is not visible, so a second finish cannot start.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from eda_pilot.config import Settings, load_settings
from eda_pilot.models import RunManifest
from mcp_tools.metrics import extract_metrics, get_metrics
from mcp_tools.reports import read_report
from mcp_tools.run_flow import build_make_argv, run_flow
from mcp_tools.validation import FlowValidationError, list_params

REPO = Path(__file__).resolve().parents[1]
STAGE = REPO / "results" / "_p322_stage"
MIRROR = REPO / "results" / "_p322_mirror"
DESIGNS = ("gcd", "aes", "ibex")
RUN_IDS = {
    "gcd": "a" * 32,
    "aes": "b" * 32,
    "ibex": "c" * 32,
}


def _stage_mirror() -> Settings:
    flow = MIRROR / "flow"
    runs = MIRROR / "runs"
    if MIRROR.exists():
        shutil.rmtree(MIRROR)
    for design, run_id in RUN_IDS.items():
        variant = f"p1{run_id}"
        report_dir = flow / "reports" / "sky130hd" / design / variant
        report_dir.mkdir(parents=True)
        source_dir = STAGE / design
        for name in ("metadata.json", "6_finish.rpt", "5_route_drc.rpt", "5_global_route.rpt"):
            shutil.copy2(source_dir / name, report_dir / name)
        run_dir = runs / run_id
        run_dir.mkdir(parents=True)
        manifest = RunManifest(
            run_id=run_id,
            design=design,
            platform="sky130hd",
            flow_variant=variant,
            status="ok",
            runtime=0.0,
            params={},
        )
        (run_dir / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    return Settings(
        orfs_flow_dir=flow,
        runs_dir=runs,
        make_executable="make",
        timeout_seconds=30,
        max_runs=8,
        allowed_parameters_path=REPO / "configs" / "allowed_parameters.json",
    )


def main() -> None:
    import agent.agent as agent_module
    import benchmarks.benchmark as benchmark_module
    import benchmarks.compare_results as compare_module

    configured = load_settings()
    flow = configured.resolve_flow_dir()
    flow_visible = bool(flow is not None and flow.is_dir())
    mirror_settings = _stage_mirror()
    report: dict[str, object] = {
        "configured_flow": str(flow) if flow is not None else None,
        "flow_visible": flow_visible,
        "windows_make": shutil.which("make"),
        "windows_wsl": shutil.which("wsl"),
        "agent_entrypoint": callable(getattr(agent_module, "run_session", None)),
        "harness_entrypoint": callable(getattr(benchmark_module, "run_matrix", None))
        and callable(getattr(compare_module, "compare", None)),
        "designs": {},
    }
    designs: dict[str, object] = {}
    for design in DESIGNS:
        listed = list_params(design, "sky130hd")
        metadata = json.loads((STAGE / f"{design}_metadata.json").read_text(encoding="utf-8"))
        extracted = extract_metrics(RUN_IDS[design], metadata)
        metrics = get_metrics(RUN_IDS[design], settings=mirror_settings)
        reports = {}
        for name in ("timing", "drc", "congestion"):
            item = read_report(RUN_IDS[design], name, settings=mirror_settings)
            reports[name] = {
                "source_file": item.source_file,
                "line_count": item.line_count,
                "truncated": item.truncated,
                "empty": item.text.strip() == "",
            }
        argv = build_make_argv(
            configured,
            flow or Path(r"\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow"),
            design,
            "sky130hd",
            f"p1{RUN_IDS[design]}",
            {},
            None,
        )
        run_result: dict[str, object]
        if flow_visible:
            run_result = {
                "called": False,
                "status": "skipped",
                "message": "configured flow directory is visible; live finish was not started",
            }
        else:
            try:
                result = run_flow(design, "sky130hd", None, settings=configured)
                run_result = {
                    "called": True,
                    "status": result.status,
                    "message": result.message,
                    "runtime": result.runtime,
                }
            except (FlowValidationError, OSError, FileNotFoundError) as exc:
                run_result = {"called": True, "status": "rejected", "message": str(exc)}
        designs[design] = {
            "list_params": {
                "count": len(listed.parameters),
                "executable": sum(1 for item in listed.parameters if item.executable),
                "names": [item.name for item in listed.parameters],
            },
            "extract_metrics": extracted.model_dump(),
            "get_metrics": metrics.model_dump(),
            "read_report": reports,
            "make_argv_head": argv[:4],
            "make_argv_tail": argv[-2:],
            "run_flow": run_result,
            "total_elapsed_seconds": metadata.get("total_elapsed_seconds"),
        }
    report["designs"] = designs
    dest = REPO / "results" / "p322_mcp.json"
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
