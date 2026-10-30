"""MCP server for OpenROAD Flow Scripts.

The official MCP Python SDK 2.x renamed FastMCP to MCPServer. The class below
is that server. The decorator API is the FastMCP API: ``@mcp.tool()``.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer as FastMCP
from mcp.server.mcpserver.exceptions import ToolError

from eda_pilot import __version__
from eda_pilot.config import ConfigurationError
from eda_pilot.models import MetricsResult, ParameterList, ReportResult, RunResult
from mcp_tools.metrics import get_metrics as read_metrics
from mcp_tools.reports import read_report as read_run_report
from mcp_tools.run_flow import run_flow as execute_flow
from mcp_tools.validation import FlowValidationError, list_params as list_design_params


def _public_error(exc: FlowValidationError | ConfigurationError) -> ToolError:
    """Surface an anticipated rejection to the MCP client."""

    return ToolError(str(exc))


mcp = FastMCP(
    "eda-pilot-orfs",
    instructions=(
        "Safe OpenROAD Flow Scripts tools for design-space exploration. "
        "Call list_params before run_flow. Pass only numeric parameters "
        "returned by list_params. This server does not run shell commands."
    ),
    version=__version__,
)


@mcp.tool()
def list_params(design: str, platform: str = "sky130hd") -> ParameterList:
    """List tunable ORFS parameters for a design.

    Returns each parameter's type, minimum, maximum, default, and step.
    Parameters with executable=false are rejected by run_flow.
    Source data is the design autotuner.json, bounded by the server allowlist.
    """

    try:
        return list_design_params(design, platform)
    except (FlowValidationError, ConfigurationError) as exc:
        raise _public_error(exc) from exc


@mcp.tool()
def run_flow(
    design: str,
    platform: str,
    params: dict[str, float] | None = None,
) -> RunResult:
    """Run the ORFS finish target for one design and platform.

    params is an object of parameter names to numbers. Unknown names,
    duplicate names, and out-of-range values are rejected and no flow
    process is started. The server creates FLOW_VARIANT, enforces the
    run budget, enforces the timeout, and captures stdout and stderr.
    """

    try:
        return execute_flow(design, platform, params)
    except (FlowValidationError, ConfigurationError) as exc:
        raise _public_error(exc) from exc


@mcp.tool()
def get_metrics(run_id: str) -> MetricsResult:
    """Read setup, hold, power, area, utilization, DRC, and runtime from metadata.json."""

    try:
        return read_metrics(run_id)
    except (FlowValidationError, ConfigurationError) as exc:
        raise _public_error(exc) from exc


@mcp.tool()
def read_report(run_id: str, report_name: str) -> ReportResult:
    """Return the tail of a timing, drc, or congestion report.

    report_name must be timing, drc, or congestion.
    The response is capped at 200 lines.
    """

    try:
        return read_run_report(run_id, report_name)
    except (FlowValidationError, ConfigurationError) as exc:
        raise _public_error(exc) from exc


def main() -> None:
    """Serve the tools over stdio for MCP Inspector and other clients."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
