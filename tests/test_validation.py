"""Checks for the parameter catalog and rejection rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eda_pilot.config import Settings
from mcp_tools.validation import FlowValidationError, list_params, validate_params

ALLOWLIST = Path(__file__).resolve().parents[1] / "configs" / "allowed_parameters.json"


def test_list_params_returns_gcd_bounds(catalog_settings: Settings) -> None:
    listed = list_params("gcd", settings=catalog_settings)

    assert listed.design == "gcd"
    assert listed.platform == "sky130hd"
    assert listed.source == "configs/allowed_parameters.json"
    by_name = {item.name: item for item in listed.parameters}
    utilization = by_name["CORE_UTILIZATION"]
    assert utilization.minimum == 20
    assert utilization.maximum == 50
    assert utilization.default == 38
    assert utilization.type == "int"
    assert utilization.executable is True
    assert by_name["_SDC_CLK_PERIOD"].default == 1.1
    assert by_name["_SDC_CLK_PERIOD"].minimum == 0.8
    assert by_name["_SDC_CLK_PERIOD"].maximum == 5.0
    assert by_name["CORE_ASPECT_RATIO"].default == 1.0
    assert by_name["_FR_LAYER_ADJUST"].executable is False
    assert "_SDC_FILE_PATH" not in by_name
    assert len(by_name) == 10


def test_unknown_parameter_is_rejected(catalog_settings: Settings) -> None:
    with pytest.raises(FlowValidationError, match="unknown parameter 'ABC_AREA'"):
        validate_params("gcd", "sky130hd", {"ABC_AREA": 1}, settings=catalog_settings)


def test_out_of_range_parameter_is_rejected(catalog_settings: Settings) -> None:
    with pytest.raises(
        FlowValidationError,
        match=r"CORE_UTILIZATION value 5 is outside \[20, 50\]",
    ):
        validate_params(
            "gcd",
            "sky130hd",
            {"CORE_UTILIZATION": 5},
            settings=catalog_settings,
        )


def test_duplicate_json_keys_are_rejected(catalog_settings: Settings) -> None:
    raw = '{"CORE_UTILIZATION": 30, "CORE_UTILIZATION": 40}'
    with pytest.raises(FlowValidationError, match="duplicate parameter 'CORE_UTILIZATION'"):
        validate_params("gcd", "sky130hd", raw, settings=catalog_settings)


def test_shell_text_is_not_a_number(catalog_settings: Settings) -> None:
    with pytest.raises(FlowValidationError, match="parameter 'CORE_UTILIZATION' must be an integer"):
        validate_params(
            "gcd",
            "sky130hd",
            {"CORE_UTILIZATION": "40; rm -rf /"},
            settings=catalog_settings,
        )


def test_booleans_are_rejected(catalog_settings: Settings) -> None:
    with pytest.raises(FlowValidationError, match="must be an integer"):
        validate_params(
            "gcd",
            "sky130hd",
            {"CELL_PAD_IN_SITES_GLOBAL_PLACEMENT": True},
            settings=catalog_settings,
        )


def test_platform_file_rewrite_is_not_executable(catalog_settings: Settings) -> None:
    with pytest.raises(FlowValidationError, match="not executable"):
        validate_params(
            "gcd",
            "sky130hd",
            {"_FR_LAYER_ADJUST": 0.2},
            settings=catalog_settings,
        )


def test_path_traversal_design_is_rejected(catalog_settings: Settings) -> None:
    with pytest.raises(FlowValidationError, match="unknown design '<rejected>'"):
        validate_params("../gcd", "sky130hd", {}, settings=catalog_settings)


def test_autotuner_can_tighten_but_not_widen_or_add(
    tmp_path: Path,
    catalog_settings: Settings,
) -> None:
    flow = tmp_path / "flow"
    design = flow / "designs" / "sky130hd" / "gcd"
    design.mkdir(parents=True)
    (design / "autotuner.json").write_text(
        json.dumps(
            {
                "CORE_UTILIZATION": {"type": "int", "minmax": [30, 40], "step": 1},
                "CORE_MARGIN": {"type": "int", "minmax": [0, 100], "step": 1},
                "EVIL": {"type": "int", "minmax": [0, 1], "step": 1},
                "_SDC_FILE_PATH": "constraint.sdc",
            }
        ),
        encoding="utf-8",
    )
    settings = catalog_settings.model_copy(update={"orfs_flow_dir": flow})
    listed = list_params("gcd", "sky130hd", settings=settings)
    by_name = {item.name: item for item in listed.parameters}

    assert listed.source == "ORFS autotuner.json"
    assert set(by_name) == {"CORE_UTILIZATION", "CORE_MARGIN"}
    assert by_name["CORE_UTILIZATION"].minimum == 30
    assert by_name["CORE_UTILIZATION"].maximum == 40
    assert by_name["CORE_MARGIN"].minimum == 1
    assert by_name["CORE_MARGIN"].maximum == 3
    assert "EVIL" not in by_name

    with pytest.raises(FlowValidationError, match="outside"):
        validate_params("gcd", "sky130hd", {"CORE_UTILIZATION": 25}, settings=settings)
    with pytest.raises(FlowValidationError, match="outside"):
        validate_params("gcd", "sky130hd", {"CORE_MARGIN": 0}, settings=settings)
    validate_params("gcd", "sky130hd", {"CORE_UTILIZATION": 35, "CORE_MARGIN": 2}, settings=settings)


def test_shipped_allowlist_loads() -> None:
    payload = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    assert payload["designs"]["gcd"]["platforms"]["sky130hd"]["parameters"]["CORE_UTILIZATION"]["default"] == 38
