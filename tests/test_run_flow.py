"""Flow launch, report tail, and an in-process MCP client session."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from eda_pilot.config import Settings
from mcp_tools.reports import read_report
from mcp_tools.run_flow import locate_wsl_flow, prepare_launch, run_flow, translate_wsl_launch
from mcp_tools.validation import FlowValidationError, list_params

FAKE_MAKE = Path(__file__).resolve().parent / "fake_make.py"


def test_list_params_for_gcd(flow_settings: Settings) -> None:
    listed = list_params("gcd", settings=flow_settings)
    names = [item.name for item in listed.parameters]
    assert "CORE_UTILIZATION" in names
    assert "CTS_CLUSTER_SIZE" in names


def test_run_flow_captures_output_and_uses_unique_variant(flow_settings: Settings) -> None:
    result = run_flow(
        "gcd",
        "sky130hd",
        {"CORE_UTILIZATION": 40, "PLACE_DENSITY_LB_ADDON": 0.1},
        settings=flow_settings,
    )

    assert result.status == "ok"
    assert result.runtime >= 0
    assert result.flow_variant == f"p1{result.run_id}"
    stdout = (flow_settings.runs_dir / result.run_id / "stdout.log").read_text(encoding="utf-8")
    stderr = (flow_settings.runs_dir / result.run_id / "stderr.log").read_text(encoding="utf-8")
    assert "ORFS finish done" in stdout
    assert "warning: fake flow" in stderr

    argv = json.loads(
        (flow_settings.resolve_flow_dir() / ".eda_pilot" / "last_argv.json").read_text(
            encoding="utf-8"
        )
    )
    assert "DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk" in argv
    assert f"FLOW_VARIANT={result.flow_variant}" in argv
    assert "CORE_UTILIZATION=40" in argv
    assert "PLACE_DENSITY_LB_ADDON=0.1" in argv
    assert argv[-1] == "finish"
    assert all(";" not in arg and "|" not in arg and "&&" not in arg for arg in argv)


def test_run_flow_does_not_use_a_shell(flow_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    real_popen = subprocess.Popen

    def spy(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return real_popen(*args, **kwargs)

    monkeypatch.setattr("mcp_tools.run_flow.subprocess.Popen", spy)
    run_flow("gcd", "sky130hd", {"CORE_MARGIN": 2}, settings=flow_settings)
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["shell"] is False
    argv = kwargs["args"]
    assert isinstance(argv, list)
    assert "cmd.exe" not in argv
    assert "sh" not in argv


def test_invalid_parameter_does_not_start_a_process(
    flow_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("process started for an invalid parameter")

    monkeypatch.setattr("mcp_tools.run_flow.subprocess.Popen", fail)
    with pytest.raises(FlowValidationError, match="unknown parameter 'ABC_AREA'"):
        run_flow("gcd", "sky130hd", {"ABC_AREA": 1}, settings=flow_settings)
    assert not (flow_settings.runs_dir / "budget_count").exists()


def test_clock_period_rewrites_only_the_private_sdc(flow_settings: Settings) -> None:
    result = run_flow(
        "gcd",
        "sky130hd",
        {"_SDC_CLK_PERIOD": 2.5},
        settings=flow_settings,
    )
    flow = flow_settings.resolve_flow_dir()
    assert flow is not None
    private = flow / ".eda_pilot" / "sdc" / result.run_id / "constraint.sdc"
    text = private.read_text(encoding="utf-8")
    assert "set clk_period 2.5" in text
    assert "set clk_period 1.1" not in text
    assert "create_clock -name $clk_name -period $clk_period $clk_port" in text
    argv = json.loads((flow / ".eda_pilot" / "last_argv.json").read_text(encoding="utf-8"))
    assert f"SDC_FILE=.eda_pilot/sdc/{result.run_id}/constraint.sdc" in argv
    assert "_SDC_CLK_PERIOD" not in " ".join(argv)


def test_read_report_returns_only_the_tail(flow_settings: Settings) -> None:
    result = run_flow("gcd", "sky130hd", {"CORE_UTILIZATION": 38}, settings=flow_settings)
    timing = read_report(result.run_id, "timing", settings=flow_settings)
    drc = read_report(result.run_id, "drc", settings=flow_settings)
    congestion = read_report(result.run_id, "congestion", settings=flow_settings)

    assert timing.line_count <= 200
    assert timing.truncated is True
    assert "setup slack -0.012" in timing.text
    assert "noise line 0" not in timing.text
    assert timing.source_file == "6_finish.rpt"
    assert "DRC violations: 0" in drc.text
    assert "congestion overflow: 0" in congestion.text


def test_read_report_rejects_a_filename(flow_settings: Settings) -> None:
    result = run_flow("gcd", "sky130hd", None, settings=flow_settings)
    with pytest.raises(FlowValidationError, match="report_name must be timing, drc, or congestion"):
        read_report(result.run_id, "../6_finish.rpt", settings=flow_settings)


def test_timeout_is_enforced(flow_settings: Settings) -> None:
    flow = flow_settings.resolve_flow_dir()
    assert flow is not None
    (flow / ".fake_sleep_seconds").write_text("3", encoding="utf-8")
    limited = flow_settings.model_copy(update={"timeout_seconds": 1})
    result = run_flow("gcd", "sky130hd", {"CORE_UTILIZATION": 30}, settings=limited)
    assert result.status == "timeout"
    assert result.runtime < 3
    assert "exceeded timeout" in (result.message or "")


def test_wsl_launch_quotes_the_linux_flow() -> None:
    flow = Path(r"\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow")
    variant = "p1" + ("a" * 32)
    argv = [
        "make",
        "-C",
        str(flow),
        "DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk",
        f"FLOW_VARIANT={variant}",
        "finish",
    ]
    located = locate_wsl_flow(flow)
    assert located == ("Ubuntu", "/home/administrator/OpenROAD-flow-scripts/flow")
    launch = translate_wsl_launch(
        argv,
        wsl_executable=r"C:\Windows\System32\wsl.exe",
        distro="Ubuntu",
        linux_flow="/home/administrator/OpenROAD-flow-scripts/flow",
    )
    assert launch[:5] == [r"C:\Windows\System32\wsl.exe", "-d", "Ubuntu", "--", "bash"]
    assert launch[5] == "-lc"
    script = launch[6]
    assert "cd '/home/administrator/OpenROAD-flow-scripts/flow'" in script
    assert ". ../env.sh" in script
    assert "DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk" in script
    assert f"FLOW_VARIANT={variant}" in script
    assert "'finish'" in script
    assert script.endswith("'metadata-generate'")
    with pytest.raises(FlowValidationError, match="WSL flow path is not usable"):
        translate_wsl_launch(
            argv,
            wsl_executable=r"C:\Windows\System32\wsl.exe",
            distro="Ubuntu",
            linux_flow="/tmp/$(reboot)",
        )


def test_local_make_is_not_sent_to_wsl(tmp_path: Path) -> None:
    argv = ["make", "-C", str(tmp_path), "finish"]
    launch, cwd = prepare_launch(argv, tmp_path)
    assert launch == argv
    assert cwd == tmp_path


def test_run_budget_is_enforced(flow_settings: Settings) -> None:
    limited = flow_settings.model_copy(update={"max_runs": 1})
    first = run_flow("gcd", "sky130hd", {"CORE_UTILIZATION": 30}, settings=limited)
    assert first.status == "ok"
    with pytest.raises(FlowValidationError, match="run budget exceeded"):
        run_flow("gcd", "sky130hd", {"CORE_UTILIZATION": 31}, settings=limited)


def _tool_payload(result: object) -> dict[str, object]:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    content = getattr(result, "content", []) or []
    chunks: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            chunks.append(text)
    parsed = json.loads("".join(chunks))
    if not isinstance(parsed, dict):
        raise AssertionError("tool result was not a JSON object")
    return parsed


def test_mcp_client_session(flow_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the four tools through the MCP client, the same path Inspector uses."""

    flow = flow_settings.resolve_flow_dir()
    assert flow is not None
    monkeypatch.setenv("ORFS_FLOW_DIR", str(flow))
    monkeypatch.setenv("ORFS_MAKE", str(FAKE_MAKE))
    monkeypatch.setenv("EDA_PILOT_RUNS_DIR", str(flow_settings.runs_dir))
    monkeypatch.setenv("EDA_PILOT_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("EDA_PILOT_MAX_RUNS", "4")
    monkeypatch.delenv("ORFS_ROOT", raising=False)

    async def session() -> None:
        from mcp import Client

        from eda_pilot.server import mcp

        async with Client(mcp) as client:
            listed = await client.call_tool("list_params", {"design": "gcd"})
            assert listed.is_error is False
            listed_payload = _tool_payload(listed)
            names = [item["name"] for item in listed_payload["parameters"]]
            assert "CORE_UTILIZATION" in names

            ran = await client.call_tool(
                "run_flow",
                {
                    "design": "gcd",
                    "platform": "sky130hd",
                    "params": {"CORE_UTILIZATION": 40},
                },
            )
            assert ran.is_error is False
            ran_payload = _tool_payload(ran)
            assert ran_payload["status"] == "ok"
            run_id = ran_payload["run_id"]
            assert isinstance(run_id, str)

            metrics = await client.call_tool("get_metrics", {"run_id": run_id})
            assert metrics.is_error is False
            assert _tool_payload(metrics)["setup_wns"] == -0.012

            report = await client.call_tool(
                "read_report",
                {"run_id": run_id, "report_name": "timing"},
            )
            assert report.is_error is False
            assert "setup slack -0.012" in str(_tool_payload(report)["text"])

            rejected = await client.call_tool(
                "run_flow",
                {
                    "design": "gcd",
                    "platform": "sky130hd",
                    "params": {"CORE_UTILIZATION": 5},
                },
            )
            assert rejected.is_error is True
            error_text = " ".join(
                getattr(block, "text", "") for block in (rejected.content or [])
            )
            assert (
                "validation error: CORE_UTILIZATION value 5 is outside [20, 50]"
                in error_text
            )

    asyncio.run(session())


def test_server_registers_the_four_tools() -> None:
    from eda_pilot.server import mcp

    manager = getattr(mcp, "_tool_manager", None)
    assert manager is not None
    names = sorted(tool.name for tool in manager.list_tools())
    assert names == ["get_metrics", "list_params", "read_report", "run_flow"]
