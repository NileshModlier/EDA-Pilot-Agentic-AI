"""Launch one sky130hd finish through run_flow and record the result."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eda_pilot.config import load_settings
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    design = sys.argv[1]
    settings = load_settings().model_copy(
        update={
            "runs_dir": REPO / "results" / "wsl_validation_runs",
            "timeout_seconds": 7200,
            "max_runs": 8,
        }
    )
    try:
        result = run_flow(design, "sky130hd", None, settings=settings)
        payload = result.model_dump()
    except (FlowValidationError, OSError) as exc:
        payload = {"design": design, "status": "exception", "message": str(exc)}
    payload["design"] = design
    dest = REPO / "results" / f"wsl_run_{design}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload.get("status") == "ok" else 1)


if __name__ == "__main__":
    main()
