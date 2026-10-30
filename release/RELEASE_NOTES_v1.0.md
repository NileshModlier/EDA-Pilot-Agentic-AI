# EDA Pilot AI v1.0.0

**Release date:** 2026-10-29 · **Tag:** `v1.0.0` · **License:** MIT

The first public release of EDA Pilot AI: a guarded LangGraph agent and MCP server that searches OpenROAD Flow Scripts for the smallest clock period that still signs off. The measured study is complete: SkyWater SKY130 HD, `gcd`, `aes` and `ibex`, budget 10, seed 1.

## Highlights

- ✅ **Signed off 3 of 3 designs.** Default ORFS signed off 0 of 3.
- ⏱️ **Passing clocks 14.5–30.3% tighter than seeded random search** under the same 10-run budget.
- 🛡️ **Zero out-of-policy executions.** Every parameter is validated in code before GNU Make starts. No shell, read-only design files, budget lock and timeout.
- 📊 **Full record.** 52 scored ORFS runs (~21.2 h of flow time) and 6 unscored interruptions, all published with decision logs and failure classes.

## Major features

### LangGraph agent (`agent/`)
- Five-node `StateGraph`: `analyse → propose → validate → run → check`.
- Only `analyse` and `propose` may use a model. `validate`, `run` and `check` are code.
- Pydantic `Proposal` contract: at most 3 changes, each with a reason, `extra="forbid"`.
- Validation retries (up to 3) with the error message fed back to the proposer.
- Stop rules: budget exhausted, or a pass exists with a clock bracket under 0.05 ns.
- **Offline advisor** (default): deterministic, guarded clock bisection.
- **Chat-model advisor** (optional): `EDA_PILOT_MODEL` through LangChain `init_chat_model` with structured output.
- JSONL decision log with one line per iteration: diagnosis, proposal, parameters, status, metrics and result.

### MCP server `eda-pilot-orfs` (`eda_pilot/server.py`)
- MCP Python SDK 2.x (`MCPServer`), stdio transport, console script `eda-pilot-orfs`.
- `list_params`: knobs with type, range, default, step and `executable`.
- `run_flow`: validated launch returning run id, status (`ok` / `error` / `timeout`), runtime and variant.
- `get_metrics`: METRICS2.1 setup/hold WNS and TNS, power, area, utilization, DRC, and a `missing` list.
- `read_report`: capped tail (≤ 200 lines) of `timing`, `drc` or `congestion`.

### Guardrails (`mcp_tools/`)
- Allowlist in `configs/allowed_parameters.json`. Design `autotuner.json` files can only tighten it.
- Numeric-only values, with booleans, strings, NaN, infinity, duplicate keys and off-grid values rejected.
- Design names restricted to `^[a-z][a-z0-9_]*$`. Path traversal is rejected.
- Fixed argv with `shell=False`. A unique `FLOW_VARIANT` per run.
- Clock applied through a private copy of `constraint.sdc` per run.
- `_FR_LAYER_ADJUST` listed but non-executable, because it would rewrite platform Tcl.
- Run budget under a file lock. Timeout with a process-tree kill. Logs capped to the last 5 MB.

### Execution
- WSL bridge: `wsl.exe -d <distro> -- bash -lc` → `. ../env.sh` → `make … finish` → `make … metadata-generate`.
- The local `make` path is unchanged for native Linux.

### Benchmark harness (`benchmarks/`)
- Default ORFS, seeded random search, OpenROAD AutoTuner and agent runners under one budget and seed.
- `compare_results.py`: a pass ranks by (clock, area, power, runtime) and a fail by (setup WNS, DRC, hold WNS).
- Checkpointed, resumable campaign (`scripts/resume_campaign.py`).

### Documentation and assets (new in this release)
- README, architecture, benchmark results with every trial, case study, executive summary, technology stack, lessons learned, roadmap, interview guide, and recruiter and hiring-manager summaries.
- Diagrams in SVG, Mermaid and draw.io. Eight plots redrawn from the results JSON by `scripts/make_release_plots.py`. Logo, banner and screenshots.
- `citations.bib`.

## Benchmark achievements

| Design | Default ORFS | Random best pass | **Agent best pass** | vs random |
| --- | --- | ---: | ---: | ---: |
| `gcd` | ❌ setup −1.460 ns @ 1.1 ns | 4.113 ns | **2.867 ns** | **−30.3%** |
| `aes` | ❌ setup −0.081 ns @ 3.6 ns | 6.261 ns | **4.822 ns** | **−23.0%** |
| `ibex` | ❌ setup −0.551 ns @ 8.0 ns SDC | 10.531 ns | **9.000 ns** | **−14.5%** |

- Signoff rate: agent 7/19 (36.8%), random 11/30 (36.7%), default 0/3. `aes`: agent 3/10 against random 1/10.
- Every best result has DRC = 0 and non-negative setup and hold slack.
- Trade-off at the best points compared with random: area +7.5% to +23.3%, power +29.7% to +70.8%, runtime 1.47× to 5.53×.

Details: [BENCHMARK_RESULTS.md](../BENCHMARK_RESULTS.md).

## Known limitations

- **Offline advisor only.** The benchmarked agent used the deterministic bisection advisor. No chat model made decisions in the measured study.
- **Single seed, single PDK, budget 10.** The gains are single-sample results.
- **One-dimensional agent search.** The agent moved only `_SDC_CLK_PERIOD`, while random search moved every knob.
- **`ibex`** stopped after one run at the floor of its allowed clock range (9.0 ns). The real limit may be lower.
- **AutoTuner produced no scored trials.** The executable was missing for `gcd`/`aes`, and a Ray/HyperOpt import error occurred on `ibex`.
- **Search-step gap.** After a timeout, the offline advisor's minimum step is clamped to the range, not the bracket. This wasted the final `aes` run.
- **Campaign operations.** Two `aes` agent timeouts and six unscored interruptions. The agent checkpoint is written at session end only.
- **Host-specific scripts.** Several helper scripts under `scripts/` hardcode `/home/administrator/…` and `\\wsl$\Ubuntu\…` paths. The core package uses settings and environment variables.
- **The agent calls the tool layer in process.** The MCP server wraps the same functions and is tested separately with an in-process client.

## Upgrade notes

- Package version `0.1.0` → `1.0.0` (`pyproject.toml`, `eda_pilot/__init__.py`). No behaviour change, and no API change.
- No new benchmark runs were performed for this release. All results are the finalized P3.4 / P3.5 artefacts.

## Verification

- `pytest`: **48 passed** in clean Linux environments on Python 3.11, 3.12 and 3.13.
- Plots regenerated from `results/final_benchmark_results.json`. All figures in the docs match that file.

## Roadmap

- **v1.1:** score AutoTuner, per-iteration agent checkpoints, error lines in trial records, bracket-clamped steps, configurable script paths.
- **v1.2:** multi-seed study, and a lower `ibex` clock floor.
- **v1.3:** benchmark the chat-model advisor against bisection.
- **v2.0:** hybrid clock-then-PPA policy, and multi-objective leaderboards.

Full plan: [docs/roadmap.md](../docs/roadmap.md).

## Acknowledgements

Built on OpenROAD, OpenROAD Flow Scripts, Yosys, KLayout, the SkyWater SKY130 PDK, the Ibex core, LangGraph and the Model Context Protocol. See [citations.bib](../citations.bib).
