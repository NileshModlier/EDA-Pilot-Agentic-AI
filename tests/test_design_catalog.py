"""sky130hd gcd, aes, and ibex stay inside the existing MCP tools."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from eda_pilot.config import Settings
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError, list_params, validate_params

ROOT = Path(__file__).resolve().parents[1]


def _environment():
    spec = importlib.util.spec_from_file_location(
        "validate_benchmark_env",
        ROOT / "scripts" / "validate_benchmark_env.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_benchmark_env"] = module
    spec.loader.exec_module(module)
    return module


def test_aes_and_ibex_list_their_autotuner_bounds(catalog_settings: Settings) -> None:
    aes = {item.name: item for item in list_params("aes", settings=catalog_settings).parameters}
    ibex = {item.name: item for item in list_params("ibex", settings=catalog_settings).parameters}

    assert len(aes) == 9
    assert aes["_SDC_CLK_PERIOD"].minimum == 3.5
    assert aes["_SDC_CLK_PERIOD"].maximum == 7.0
    assert aes["_SDC_CLK_PERIOD"].default == 3.6
    assert aes["CORE_UTILIZATION"].default == 35
    assert aes["PLACE_DENSITY_LB_ADDON"].default == 0.2
    assert aes["_FR_LAYER_ADJUST"].executable is False
    assert "CORE_MARGIN" not in aes

    assert len(ibex) == 9
    assert ibex["_SDC_CLK_PERIOD"].minimum == 9.0
    assert ibex["_SDC_CLK_PERIOD"].maximum == 16.0
    assert ibex["_SDC_CLK_PERIOD"].default is None
    assert ibex["CORE_UTILIZATION"].default == 50
    assert ibex["PLACE_DENSITY_LB_ADDON"].default is None
    assert ibex["CTS_CLUSTER_SIZE"].default == 20


def test_gcd_catalog_is_unchanged(catalog_settings: Settings) -> None:
    listed = list_params("gcd", settings=catalog_settings)
    by_name = {item.name: item for item in listed.parameters}

    assert len(by_name) == 10
    assert by_name["CORE_UTILIZATION"].default == 38
    assert by_name["_SDC_CLK_PERIOD"].minimum == 0.8
    assert by_name["_SDC_CLK_PERIOD"].maximum == 5.0


def test_live_autotuner_tightens_aes_and_ignores_new_names(
    tmp_path: Path, catalog_settings: Settings
) -> None:
    design = tmp_path / "flow" / "designs" / "sky130hd" / "aes"
    design.mkdir(parents=True)
    (design / "autotuner.json").write_text(
        json.dumps(
            {
                "_SDC_CLK_PERIOD": {"type": "float", "minmax": [4.0, 6.0], "step": 0},
                "CORE_UTILIZATION": {"type": "int", "minmax": [20, 80], "step": 1},
                "NEW_KNOB": {"type": "int", "minmax": [0, 1], "step": 1},
            }
        ),
        encoding="utf-8",
    )
    settings = catalog_settings.model_copy(update={"orfs_flow_dir": tmp_path / "flow"})
    listed = list_params("aes", "sky130hd", settings=settings)
    by_name = {item.name: item for item in listed.parameters}

    assert listed.source == "ORFS autotuner.json"
    assert set(by_name) == {"_SDC_CLK_PERIOD", "CORE_UTILIZATION"}
    assert by_name["_SDC_CLK_PERIOD"].minimum == 4.0
    assert by_name["_SDC_CLK_PERIOD"].maximum == 6.0
    assert by_name["CORE_UTILIZATION"].maximum == 50
    with pytest.raises(FlowValidationError, match="outside"):
        validate_params("aes", "sky130hd", {"_SDC_CLK_PERIOD": 3.6}, settings=settings)


def test_clock_defaults_validate_and_outsiders_do_not(catalog_settings: Settings) -> None:
    validate_params("aes", "sky130hd", {"_SDC_CLK_PERIOD": 3.6}, settings=catalog_settings)
    validate_params("ibex", "sky130hd", {"_SDC_CLK_PERIOD": 10}, settings=catalog_settings)
    validate_params("ibex", "sky130hd", None, settings=catalog_settings)
    with pytest.raises(FlowValidationError, match="outside"):
        validate_params("aes", "sky130hd", {"_SDC_CLK_PERIOD": 3.0}, settings=catalog_settings)
    with pytest.raises(FlowValidationError, match="outside"):
        validate_params("ibex", "sky130hd", {"_SDC_CLK_PERIOD": 8}, settings=catalog_settings)


def test_aes_and_ibex_run_flow_on_the_stand_in(
    flow_settings: Settings, tmp_path: Path
) -> None:
    flow = flow_settings.orfs_flow_dir
    assert flow is not None
    for design, period in (("aes", "3.6"), ("ibex", "8.0")):
        folder = flow / "designs" / "sky130hd" / design
        folder.mkdir(parents=True)
        (folder / "config.mk").write_text(
            f"export DESIGN_NAME = {design}\nexport PLATFORM = sky130hd\n",
            encoding="utf-8",
        )
        (folder / "constraint.sdc").write_text(
            f"current_design {design}\nset clk_period {period}\n",
            encoding="utf-8",
        )
    settings = flow_settings.model_copy(
        update={"runs_dir": tmp_path / "runs", "max_runs": 4}
    )

    for design in ("aes", "ibex"):
        result = run_flow(design, "sky130hd", None, settings=settings)
        assert result.status == "ok"
    clocked = run_flow(
        "aes",
        "sky130hd",
        {"_SDC_CLK_PERIOD": 4.0},
        settings=settings,
    )
    assert clocked.status == "ok"


def test_validator_does_not_start_finish_when_files_exist(
    flow_settings: Settings, tmp_path: Path, monkeypatch
) -> None:
    environment = _environment()
    flow = flow_settings.orfs_flow_dir
    assert flow is not None
    for design in ("aes", "ibex"):
        folder = flow / "designs" / "sky130hd" / design
        folder.mkdir(parents=True)
        (folder / "config.mk").write_text("export PLATFORM = sky130hd\n", encoding="utf-8")
        (folder / "constraint.sdc").write_text("set clk_period 4.0\n", encoding="utf-8")
    settings = flow_settings.model_copy(update={"runs_dir": tmp_path / "runs", "max_runs": 2})
    monkeypatch.delenv("ORFS_AUTOTUNER", raising=False)
    monkeypatch.setattr(environment.shutil, "which", lambda _name: None)

    checks = {item.name: item for item in environment.validate(settings)}
    found = environment.detect_autotuner(settings)

    assert checks["list_params gcd"].result == "PASS"
    assert checks["list_params aes"].result == "PASS"
    assert checks["list_params ibex"].result == "PASS"
    assert checks["run_flow gcd"].result == "PASS"
    assert checks["run_flow aes"].result == "PASS"
    assert checks["run_flow ibex"].result == "PASS"
    assert "finish was not started" in checks["run_flow aes"].detail
    assert checks["AutoTuner detection"].result == "PASS"
    assert found["installed"] == "no"
    assert found["version"] is None
    assert found["executable"] is None
    assert not (tmp_path / "runs").exists()
