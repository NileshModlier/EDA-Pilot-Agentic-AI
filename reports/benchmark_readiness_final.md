# Benchmark readiness

Checked: 2026-10-17. Validation only. MCP server, LangGraph agent, and benchmark logic were not modified.

| Item | Status | Detail |
| --- | --- | --- |
| OpenROAD | PASS | `openroad -version` prints `26Q4-110-g91e5f5ff2f` from `tools/install/OpenROAD/bin/openroad`. |
| Yosys | PASS | Yosys 0.68+ (`a5af9d690`) from `tools/install/yosys/bin/yosys`. |
| KLayout | PASS | KLayout 0.30.0 at `/usr/bin/klayout`. |
| gcd | PASS | Synthesis, floorplan, placement, CTS, routing, and `6_final.gds` (974,128 bytes) are present. `make` exited 0. Elapsed total 124 s. |
| aes | PASS | All six stages and `6_final.gds` (19,462,484 bytes). `make` exited 0. Elapsed total 2623 s. See `reports/aes_validation.md`. |
| ibex | PASS | All six stages and `6_final.gds` (22,120,568 bytes). `make` exited 0. Elapsed total 4094 s. See `reports/ibex_validation.md`. |
| MCP | FAIL | `list_params`, `get_metrics`, and `read_report` succeed. `run_flow` raises `FileNotFoundError` because Windows has no `make`. See `reports/mcp_validation_final.md`. |
| Agent | PASS | `run_session` imports. Agent tests are included in the 44 passed tests. |
| Harness | PASS | `run_matrix` and `compare` import. Benchmark tests are included in the 44 passed tests. |

Metrics for the three base runs are in `results/design_metrics.json`. Area, power, setup WNS, hold WNS, and DRC count come from `metadata.json`. Runtime is the Make elapsed total. `get_metrics` leaves runtime empty because the metadata runtime fields are clock strings.

Default setup WNS is negative on all three base runs (gcd -1.45954, aes -0.0805747, ibex -0.551246). Hold WNS is positive and DRC count is 0.

## Can P3.3 start?

NO.

Blockers:

1. The benchmark harness calls `run_flow`, and `run_flow` starts `make` on the Windows PATH. `make` is absent there (`WinError 2` for gcd, aes, and ibex). The flow directory is visible at `\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow`, and GNU Make 4.4.1 inside Ubuntu can complete the flows, but the server process cannot launch it.
