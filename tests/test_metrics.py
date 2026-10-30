"""metadata.json parsing."""

from __future__ import annotations

from eda_pilot.config import Settings
from mcp_tools.metrics import extract_metrics, get_metrics
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError

import pytest


def test_get_metrics_reads_finish_metadata(flow_settings: Settings) -> None:
    result = run_flow(
        "gcd",
        "sky130hd",
        {"CORE_UTILIZATION": 40},
        settings=flow_settings,
    )
    metrics = get_metrics(result.run_id, settings=flow_settings)

    assert metrics.run_id == result.run_id
    assert metrics.setup_wns == -0.012
    assert metrics.setup_tns == -0.04
    assert metrics.hold_wns == 0.005
    assert metrics.hold_tns == 0.0
    assert metrics.power == 0.00087
    assert metrics.area == 2145.3
    assert metrics.utilization == 37.5
    assert metrics.drc_count == 0
    assert metrics.runtime == 12.5
    assert metrics.missing == []


def test_nested_metadata_uses_the_same_names() -> None:
    metrics = extract_metrics(
        "abc123",
        {
            "finish": {
                "timing": {
                    "setup": {"ws": -0.2, "tns": -1.0},
                    "hold": {"ws": 0.01, "tns": 0.0},
                },
                "power": {"total": 0.01},
                "design": {"instance": {"area": 10.0, "utilization": 20.0}},
                "runtime": {"total": 3.0},
            },
            "detailedroute": {"route": {"drc_errors": 2}},
        },
    )
    assert metrics.setup_wns == -0.2
    assert metrics.setup_tns == -1.0
    assert metrics.hold_wns == 0.01
    assert metrics.hold_tns == 0.0
    assert metrics.power == 0.01
    assert metrics.area == 10.0
    assert metrics.utilization == 20.0
    assert metrics.drc_count == 2
    assert metrics.runtime == 3.0
    assert metrics.missing == []


def test_missing_metrics_are_null() -> None:
    metrics = extract_metrics("abc123", {"finish__timing__setup__ws": 0.1})
    assert metrics.setup_wns == 0.1
    assert metrics.power is None
    assert "power" in metrics.missing
    assert "setup_wns" not in metrics.missing


def test_unknown_run_is_rejected(flow_settings: Settings) -> None:
    with pytest.raises(FlowValidationError, match="unknown run_id"):
        get_metrics("not-a-run", settings=flow_settings)
