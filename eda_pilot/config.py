"""Process configuration for the ORFS MCP server.

Tool arguments cannot change these values. Only the operator's environment,
or a test that constructs ``Settings`` directly, can.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = REPO_ROOT / "configs" / "allowed_parameters.json"
DEFAULT_RUNS_DIR = REPO_ROOT / "runs"


class ConfigurationError(ValueError):
    """The server process is configured incorrectly."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orfs_root: Path | None = None
    orfs_flow_dir: Path | None = None
    make_executable: str = "make"
    make_prefix: tuple[str, ...] = ()
    runs_dir: Path = Field(default_factory=lambda: DEFAULT_RUNS_DIR)
    timeout_seconds: float = 7200
    max_runs: int = 8
    allowed_parameters_path: Path = Field(default_factory=lambda: DEFAULT_ALLOWLIST)
    orfs_target: str = "finish"

    @field_validator("make_executable")
    @classmethod
    def _executable(cls, value: str) -> str:
        if value == "" or any(character in value for character in "\r\n\x00"):
            raise ValueError("ORFS_MAKE is not a usable executable name")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def _timeout(cls, value: float) -> float:
        if value <= 0 or value > 86_400:
            raise ValueError("timeout must be greater than 0 and at most 86400 seconds")
        return value

    @field_validator("max_runs")
    @classmethod
    def _budget(cls, value: int) -> int:
        if value < 1 or value > 1000:
            raise ValueError("run budget must be from 1 to 1000")
        return value

    @field_validator("orfs_target")
    @classmethod
    def _target(cls, value: str) -> str:
        if value != "finish":
            raise ValueError("only the finish target is approved")
        return value

    def command_prefix(self) -> list[str]:
        """Argv prefix for ORFS. A ``.py`` launcher runs under this interpreter."""

        if self.make_prefix:
            return list(self.make_prefix)
        if self.make_executable.lower().endswith(".py"):
            return [sys.executable, self.make_executable]
        return [self.make_executable]

    def resolve_flow_dir(self) -> Path | None:
        if self.orfs_flow_dir is not None:
            return self.orfs_flow_dir
        if self.orfs_root is not None:
            return self.orfs_root / "flow"
        return None


def _optional_path(name: str) -> Path | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return Path(raw)


def load_settings() -> Settings:
    """Load operator settings from the environment."""

    timeout_raw = os.environ.get("EDA_PILOT_TIMEOUT_SECONDS", "7200")
    budget_raw = os.environ.get("EDA_PILOT_MAX_RUNS", "8")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ConfigurationError(
            "validation error: EDA_PILOT_TIMEOUT_SECONDS must be a number"
        ) from exc
    try:
        max_runs = int(budget_raw)
    except ValueError as exc:
        raise ConfigurationError(
            "validation error: EDA_PILOT_MAX_RUNS must be an integer"
        ) from exc
    try:
        return Settings(
            orfs_root=_optional_path("ORFS_ROOT"),
            orfs_flow_dir=_optional_path("ORFS_FLOW_DIR"),
            make_executable=os.environ.get("ORFS_MAKE", "make"),
            runs_dir=_optional_path("EDA_PILOT_RUNS_DIR") or DEFAULT_RUNS_DIR,
            timeout_seconds=timeout_seconds,
            max_runs=max_runs,
            allowed_parameters_path=(
                _optional_path("EDA_PILOT_ALLOWED_PARAMETERS") or DEFAULT_ALLOWLIST
            ),
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"]
        raise ConfigurationError(f"validation error: invalid server configuration ({message})") from exc
