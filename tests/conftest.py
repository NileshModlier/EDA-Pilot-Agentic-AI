"""Shared fixtures for the ORFS MCP tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from eda_pilot.config import Settings

ROOT = Path(__file__).resolve().parents[1]
FAKE_MAKE = Path(__file__).resolve().parent / "fake_make.py"
ALLOWLIST = ROOT / "configs" / "allowed_parameters.json"

SDC = """current_design gcd

set clk_name core_clock
set clk_port_name clk
set clk_period 1.1
set clk_io_pct 0.2

set clk_port [get_ports $clk_port_name]

create_clock -name $clk_name -period $clk_period $clk_port
"""


@pytest.fixture
def catalog_settings(tmp_path: Path) -> Settings:
    return Settings(
        runs_dir=tmp_path / "runs",
        timeout_seconds=30,
        max_runs=4,
        allowed_parameters_path=ALLOWLIST,
    )


@pytest.fixture
def flow_settings(tmp_path: Path) -> Settings:
    flow = tmp_path / "flow"
    design = flow / "designs" / "sky130hd" / "gcd"
    design.mkdir(parents=True)
    (design / "config.mk").write_text(
        "export DESIGN_NAME = gcd\nexport PLATFORM = sky130hd\n",
        encoding="utf-8",
    )
    (design / "constraint.sdc").write_text(SDC, encoding="utf-8")
    return Settings(
        orfs_flow_dir=flow,
        make_prefix=(sys.executable, str(FAKE_MAKE)),
        runs_dir=tmp_path / "runs",
        timeout_seconds=30,
        max_runs=4,
        allowed_parameters_path=ALLOWLIST,
    )
