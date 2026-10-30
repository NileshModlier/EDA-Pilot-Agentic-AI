# Reports

| File | What it is |
| --- | --- |
| [`final_benchmark_report.md`](final_benchmark_report.md) | Final P3.4 analysis: leaderboards, signoff rate, failure classes, runtime and QoR. Unchanged for v1.0.0 |
| [`benchmark_summary.md`](benchmark_summary.md) | Plain-text leaderboard per design, as printed by the harness. Unchanged for v1.0.0 |
| `aes_leaderboard.md`, `aes_validation.md`, `ibex_validation.md` | Per-design validation before the campaign |
| `environment_validation.md`, `orfs_discovery.md`, `openroad_dependencies.md`, `openroad_smoke_test.md` | Toolchain and ORFS checks |
| `mcp_validation_final.md`, `wsl_integration_validation.md` | MCP server and WSL bridge validation |
| `benchmark_readiness_v2.md`, `benchmark_readiness_final.md` | Readiness reviews before the campaign |

**Reading note.** The two benchmark reports describe the agent as "the agent". Every agent session in the study ran with the **offline advisor** (`"advisor": "offline"` in each line of `results/benchmark_campaign/logs/*_agent_b10.jsonl`), which is a deterministic clock bisection. No chat model made decisions in the measured study. The release-level write-up is in [`../BENCHMARK_RESULTS.md`](../BENCHMARK_RESULTS.md).
