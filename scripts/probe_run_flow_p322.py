"""Call run_flow once per design against the configured ORFS checkout.

Uses an isolated runs directory and an empty parameter set, so no private SDC
is written. The timeout is short so a launched make is stopped.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from eda_pilot.config import load_settings
from mcp_tools.run_flow import run_flow
from mcp_tools.validation import FlowValidationError

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "results" / "_p322_run_flow"


def main() -> None:
    if RUNS.exists():
        shutil.rmtree(RUNS)
    configured = load_settings()
    settings = configured.model_copy(
        update={"runs_dir": RUNS, "timeout_seconds": 20, "max_runs": 3}
    )
    rows = []
    for design in ("gcd", "aes", "ibex"):
        try:
            result = run_flow(design, "sky130hd", None, settings=settings)
            rows.append(
                {
                    "design": design,
                    "status": result.status,
                    "runtime": result.runtime,
                    "message": result.message,
                    "flow_variant": result.flow_variant,
                }
            )
        except (FlowValidationError, OSError, FileNotFoundError) as exc:
            rows.append(
                {
                    "design": design,
                    "status": "exception",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
