"""Parameter checks for ORFS runs.

Every rejection happens before a flow process is started. Names, ranges, and
the run budget come from the server catalog, never from a shell command.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from eda_pilot.config import Settings, load_settings
from eda_pilot.models import Allowlist, ListedParameter, ParameterKnob, ParameterList

DESIGN_RE = re.compile(r"^[a-z][a-z0-9_]*$")
RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
VARIANT_RE = re.compile(r"^p1[0-9a-f]{32}$")
MAKE_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
SAFE_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")

SPECIAL_APPLY = {
    "_SDC_CLK_PERIOD": "sdc_clock",
    "_FR_LAYER_ADJUST": "unsupported",
}


class FlowValidationError(ValueError):
    """A tool argument was rejected before ORFS started."""


@dataclass(frozen=True)
class ValidatedRequest:
    design: str
    platform: str
    make_values: dict[str, str]
    clock_period: str | None
    recorded_params: dict[str, float]


def list_params(
    design: str,
    platform: str = "sky130hd",
    *,
    settings: Settings | None = None,
) -> ParameterList:
    """Return tunable parameters, bounds, and defaults for one design."""

    active = settings or load_settings()
    design_name = _require_design(design, active)
    platform_name = _require_platform(design_name, platform, active)
    knobs, source = effective_knobs(design_name, platform_name, active)
    parameters = [
        ListedParameter(
            name=name,
            type=knob.type,
            minimum=knob.minimum,
            maximum=knob.maximum,
            default=knob.default,
            step=knob.step,
            executable=knob.apply != "unsupported",
            reason=knob.reason if knob.apply == "unsupported" else None,
        )
        for name, knob in sorted(knobs.items())
    ]
    return ParameterList(
        design=design_name,
        platform=platform_name,
        source=source,
        parameters=parameters,
    )


def validate_params(
    design: str,
    platform: str,
    params: object,
    *,
    settings: Settings | None = None,
) -> ValidatedRequest:
    """Reject unknown keys, duplicates, bad types, and out-of-range values."""

    active = settings or load_settings()
    design_name = _require_design(design, active)
    platform_name = _require_platform(design_name, platform, active)
    knobs, _source = effective_knobs(design_name, platform_name, active)
    raw = parse_params_payload(params)
    if len(raw) > 64:
        raise FlowValidationError("validation error: too many parameters")

    make_values: dict[str, str] = {}
    recorded: dict[str, float] = {}
    clock_period: str | None = None
    for name, value in raw.items():
        if name not in knobs:
            raise FlowValidationError(
                f"validation error: unknown parameter '{_safe_token(name)}'"
            )
        knob = knobs[name]
        number = _coerce_number(name, value, knob.type)
        if knob.apply == "unsupported":
            reason = knob.reason or "it cannot be applied safely"
            raise FlowValidationError(
                f"validation error: parameter '{name}' is not executable ({reason})"
            )
        rendered = format_number(number, knob.type)
        lower = format_number(knob.minimum, knob.type)
        upper = format_number(knob.maximum, knob.type)
        if number < knob.minimum or number > knob.maximum:
            raise FlowValidationError(
                f"validation error: {name} value {rendered} is outside [{lower}, {upper}]"
            )
        if not _matches_step(number, knob.minimum, knob.step):
            raise FlowValidationError(
                f"validation error: {name} value {rendered} "
                f"is not on step {format_number(knob.step, knob.type)}"
            )
        recorded[name] = float(number)
        if knob.apply == "make":
            make_values[name] = rendered
        elif knob.apply == "sdc_clock":
            clock_period = rendered
        else:
            raise FlowValidationError(
                f"validation error: parameter '{name}' is not executable"
            )
    return ValidatedRequest(
        design=design_name,
        platform=platform_name,
        make_values=make_values,
        clock_period=clock_period,
        recorded_params=recorded,
    )


def parse_params_payload(params: object) -> dict[str, object]:
    """Parse a parameter object and reject duplicate keys in raw JSON."""

    if params is None:
        return {}
    if isinstance(params, str):
        try:
            parsed = json.loads(params, object_pairs_hook=_reject_duplicate_pairs)
        except FlowValidationError:
            raise
        except json.JSONDecodeError as exc:
            raise FlowValidationError(
                "validation error: params is not a JSON object"
            ) from exc
        if not isinstance(parsed, dict):
            raise FlowValidationError("validation error: params must be a JSON object")
        return parsed
    if isinstance(params, dict):
        return dict(params)
    raise FlowValidationError("validation error: params must be a JSON object")


def effective_knobs(
    design: str,
    platform: str,
    settings: Settings,
) -> tuple[dict[str, ParameterKnob], str]:
    """Return knobs the server will accept for this design.

    A local ORFS ``autotuner.json`` can tighten a range. It cannot add a name
    or widen a range past ``configs/allowed_parameters.json``.
    """

    catalog = load_allowlist(settings.allowed_parameters_path)
    knobs = dict(catalog.designs[design].platforms[platform].parameters)
    autotuner = _autotuner_path(settings, platform, design)
    if autotuner is None:
        return knobs, "configs/allowed_parameters.json"

    live = _load_autotuner(autotuner)
    selected: dict[str, ParameterKnob] = {}
    for name, knob in knobs.items():
        if name not in live:
            continue
        _live_type, live_min, live_max = live[name]
        minimum = max(knob.minimum, live_min)
        maximum = min(knob.maximum, live_max)
        if minimum > maximum:
            continue
        default = knob.default
        if default is not None and not (minimum <= default <= maximum):
            default = None
        selected[name] = knob.model_copy(
            update={"minimum": minimum, "maximum": maximum, "default": default}
        )
    return selected, "ORFS autotuner.json"


def load_allowlist(path: Path) -> Allowlist:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowValidationError(
            "validation error: allowed parameter catalog is unreadable"
        ) from exc
    try:
        catalog = Allowlist.model_validate(payload)
    except ValidationError as exc:
        raise FlowValidationError(
            "validation error: allowed parameter catalog is invalid"
        ) from exc
    _check_catalog_names(catalog)
    return catalog


def format_number(value: float, kind: str) -> str:
    """Render a checked number using only digits and one optional decimal."""

    if kind == "int":
        if not float(value).is_integer():
            raise FlowValidationError(
                "validation error: refused to format a non-integer make value"
            )
        return str(int(value))
    if not math.isfinite(float(value)):
        raise FlowValidationError(
            "validation error: refused to format a non-finite make value"
        )
    rendered = format(Decimal(str(float(value))).normalize(), "f")
    if rendered in {"", "-0"}:
        rendered = "0"
    if NUMBER_RE.fullmatch(rendered) is None:
        raise FlowValidationError(
            "validation error: refused to format an unsafe numeric value"
        )
    return rendered


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise FlowValidationError(
                f"validation error: duplicate parameter '{_safe_token(key)}'"
            )
        parsed[key] = value
    return parsed


def _require_design(design: object, settings: Settings) -> str:
    catalog = load_allowlist(settings.allowed_parameters_path)
    if isinstance(design, str) and DESIGN_RE.fullmatch(design) and design in catalog.designs:
        return design
    raise FlowValidationError(f"validation error: unknown design '{_public_label(design)}'")


def _require_platform(design: str, platform: object, settings: Settings) -> str:
    catalog = load_allowlist(settings.allowed_parameters_path)
    platforms = catalog.designs[design].platforms
    if (
        isinstance(platform, str)
        and DESIGN_RE.fullmatch(platform)
        and platform in platforms
    ):
        return platform
    raise FlowValidationError(
        f"validation error: unknown platform '{_public_label(platform)}'"
    )


def _check_catalog_names(catalog: Allowlist) -> None:
    for design, design_catalog in catalog.designs.items():
        if DESIGN_RE.fullmatch(design) is None:
            raise FlowValidationError(
                "validation error: allowed parameter catalog has an invalid design name"
            )
        for platform, platform_catalog in design_catalog.platforms.items():
            if DESIGN_RE.fullmatch(platform) is None:
                raise FlowValidationError(
                    "validation error: allowed parameter catalog has an invalid platform name"
                )
            for name, knob in platform_catalog.parameters.items():
                expected = SPECIAL_APPLY.get(name)
                if expected is not None:
                    if knob.apply != expected:
                        raise FlowValidationError(
                            "validation error: allowed parameter catalog has a bad apply mode"
                        )
                    continue
                if MAKE_NAME_RE.fullmatch(name) is None or knob.apply != "make":
                    raise FlowValidationError(
                        "validation error: allowed parameter catalog has an unapproved parameter"
                    )
                if knob.minimum > knob.maximum:
                    raise FlowValidationError(
                        "validation error: allowed parameter catalog has an inverted range"
                    )


def _autotuner_path(settings: Settings, platform: str, design: str) -> Path | None:
    flow = settings.resolve_flow_dir()
    if flow is None:
        return None
    flow_root = flow.resolve()
    candidate = (flow_root / "designs" / platform / design / "autotuner.json").resolve()
    try:
        candidate.relative_to((flow_root / "designs").resolve())
    except ValueError:
        return None
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def _load_autotuner(path: Path) -> dict[str, tuple[str, float, float]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowValidationError(
            "validation error: could not read ORFS autotuner.json"
        ) from exc
    if not isinstance(payload, dict):
        raise FlowValidationError("validation error: autotuner.json must be a JSON object")
    parsed: dict[str, tuple[str, float, float]] = {}
    for name, raw in payload.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            continue
        bounds = raw.get("minmax")
        kind = raw.get("type", "float")
        if kind not in {"int", "float"} or not isinstance(bounds, list) or len(bounds) != 2:
            continue
        low, high = bounds
        if isinstance(low, bool) or isinstance(high, bool):
            continue
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            continue
        if not math.isfinite(float(low)) or not math.isfinite(float(high)):
            continue
        parsed[name] = (kind, float(low), float(high))
    return parsed


def _coerce_number(name: str, value: object, kind: str) -> float:
    expected = "an integer" if kind == "int" else "a number"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FlowValidationError(
            f"validation error: parameter '{name}' must be {expected}"
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise FlowValidationError(f"validation error: parameter '{name}' must be finite")
    if kind == "int" and isinstance(value, float) and not value.is_integer():
        raise FlowValidationError(
            f"validation error: parameter '{name}' must be an integer"
        )
    return float(int(value) if kind == "int" else value)


def _matches_step(value: float, minimum: float, step: float) -> bool:
    if step == 0:
        return True
    span = Decimal(str(value)) - Decimal(str(minimum))
    quotient = span / Decimal(str(step))
    return quotient == quotient.to_integral_value()


def _safe_token(value: object) -> str:
    if isinstance(value, str) and SAFE_TOKEN_RE.fullmatch(value):
        return value
    return "<rejected>"


def _public_label(value: object) -> str:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value):
        return value
    return "<rejected>"
