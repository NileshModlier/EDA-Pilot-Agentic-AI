"""Pydantic models for one agent proposal.

The model may return at most three changes. The validate node, not the model,
decides whether those changes are legal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParameterChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter: str = Field(min_length=1, max_length=64)
    value: float
    reason: str = Field(min_length=1, max_length=500)


class Proposal(BaseModel):
    """At most three parameter changes, each with a reason."""

    model_config = ConfigDict(extra="forbid")

    changes: list[ParameterChange] = Field(default_factory=list, max_length=3)


class Diagnosis(BaseModel):
    """One diagnosis sentence or short paragraph. It is not a command."""

    model_config = ConfigDict(extra="forbid")

    diagnosis: str = Field(min_length=1, max_length=2000)
