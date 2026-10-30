"""Pydantic models for the ORFS MCP tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParameterKnob(BaseModel):
    """One allowlisted ORFS knob."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["int", "float"]
    minimum: float
    maximum: float
    default: float | None = None
    step: float = 0
    apply: Literal["make", "sdc_clock", "unsupported"]
    default_source: str
    reason: str | None = None


class PlatformCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameters: dict[str, ParameterKnob]


class DesignCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platforms: dict[str, PlatformCatalog]


class Allowlist(BaseModel):
    """Checked-in parameter catalog derived from an ORFS autotuner.json."""

    model_config = ConfigDict(extra="forbid")

    version: int
    source: str
    designs: dict[str, DesignCatalog]


class ListedParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["int", "float"]
    minimum: float
    maximum: float
    default: float | None
    step: float
    executable: bool
    reason: str | None = None


class ParameterList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design: str
    platform: str
    source: str
    parameters: list[ListedParameter]


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: Literal["ok", "error", "timeout"]
    runtime: float
    flow_variant: str
    message: str | None = None


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    design: str
    platform: str
    flow_variant: str
    status: Literal["running", "ok", "error", "timeout"]
    runtime: float | None = None
    params: dict[str, float]
    message: str | None = None


class MetricsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    setup_wns: float | None = None
    setup_tns: float | None = None
    hold_wns: float | None = None
    hold_tns: float | None = None
    power: float | None = None
    area: float | None = None
    utilization: float | None = None
    drc_count: float | None = None
    runtime: float | None = None
    missing: list[str] = Field(default_factory=list)


class ReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    report_name: Literal["timing", "drc", "congestion"]
    source_file: str
    line_count: int
    truncated: bool
    text: str
