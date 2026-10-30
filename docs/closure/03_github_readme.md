# EDA Pilot AI

An allowlisted LangGraph agent for OpenROAD Flow Scripts. It searches for the smallest clock that signs off on sky130hd, and it was measured against default ORFS and random search on gcd, AES, and Ibex.

Signoff means DRC count = 0, setup WNS ≥ 0, and hold WNS ≥ 0. Area, power, and runtime are reported for that result.

## Result

Budget 10. Seed 1. sky130hd. The agent signed off all three designs. Default ORFS signed off none.

| Design | Default | Random search | EDA Pilot |
| --- | --- | ---: | ---: |
| gcd | 1.1 ns, setup −1.460 ns | 4.113 ns | **2.867 ns** |
| AES | 3.6 ns, setup −0.081 ns | 6.261 ns | **4.822 ns** |
| Ibex | 8.0 ns SDC, setup −0.551 ns | 10.531 ns | **9.000 ns** |

The passing agent clocks are 30.3%, 23.0%, and 14.5% tighter than the best random clocks. Those agent points are larger, higher power, and slower to run. Full tables, failure classes, and plots are in [`reports/final_benchmark_report.md`](../../reports/final_benchmark_report.md) and [`plots/`](../../plots/).

This file is the publication README. Paths are written from the `docs/closure/` folder. If you copy it to the repository root, change those two links to `reports/final_benchmark_report.md` and `plots/`.

AutoTuner was included in the harness and produced no scored trials.

## Architecture

```text
Benchmark harness
        |
LangGraph agent: analyse → propose → validate → run → check
        |
MCP tools: list_params, run_flow, get_metrics, read_report
        |
WSL Ubuntu: make finish
        |
Yosys → OpenROAD → KLayout → metadata.json
```

`analyse` and `propose` only suggest changes. Validation, launch, and metrics are code. A proposal outside the allowlist never reaches `make`. Diagrams: [`07_architecture.svg`](07_architecture.svg), [`08_technology_stack.svg`](08_technology_stack.svg).

## Requirements

- Python 3.11 or newer
- An [OpenROAD-flow-scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts) checkout
- GNU Make inside WSL Ubuntu when the host is Windows
- Yosys, OpenROAD, and KLayout on the flow `PATH` after `env.sh`

Unit tests do not need OpenROAD. They use the same argument list with a local stand-in for `make`.

## Install and test

```powershell
cd "C:\Users\Administrator\EDA Pilot AI"
python -m pip install -e ".[dev]"
python -m pytest
```

## Point at the flow

```powershell
$env:ORFS_ROOT = "\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts"
$env:EDA_PILOT_TIMEOUT_SECONDS = "7200"
$env:EDA_PILOT_MAX_RUNS = "10"
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `ORFS_ROOT` | unset | Checkout that contains `flow\Makefile` |
| `ORFS_FLOW_DIR` | `ORFS_ROOT\flow` | Makefile directory |
| `EDA_PILOT_TIMEOUT_SECONDS` | `7200` | Wall-clock limit for one finish |
| `EDA_PILOT_MAX_RUNS` | `8` | Finish runs this process may start |
| `EDA_PILOT_RUNS_DIR` | `runs` | Manifests and logs |
| `EDA_PILOT_ALLOWED_PARAMETERS` | `configs\allowed_parameters.json` | Parameter allowlist |
| `EDA_PILOT_MODEL` | unset | Offline clock search. Set a chat model only for analyse and propose |
| `ORFS_AUTOTUNER` | unset | Optional AutoTuner executable |

On Windows, `run_flow` sends `make` into the WSL distro named by the `ORFS_ROOT` UNC path, sources `env.sh`, runs `finish`, then runs `metadata-generate`.

## Run the agent

```powershell
python -m agent.agent --design gcd --platform sky130hd --budget 10
```

The session writes `runs\decision_log.jsonl` and stops on budget or on a passing clock narrowed to 0.05 ns.

## Run the benchmark

```powershell
python -m benchmarks.benchmark --designs gcd aes ibex --platform sky130hd --budgets 10 --seed 1
```

Methods: default ORFS once, random search, AutoTuner if `openroad_autotuner` is on `PATH`, and the EDA Pilot agent. A missing AutoTuner is recorded as unavailable. No AutoTuner metrics are invented.

## Tools

| Tool | Role |
| --- | --- |
| `list_params` | Allowlisted knobs, ranges, and defaults |
| `run_flow` | Validate, launch `finish`, return status and runtime |
| `get_metrics` | Slack, power, area, utilization, DRC from `metadata.json` |
| `read_report` | Tail of `timing`, `drc`, or `congestion` |

## Safety

The server builds the `make` argument list itself and does not use a shell. It rejects unknown names, non-numeric values, out-of-range values, duplicate keys, and parameters that would rewrite platform files. A spent budget or a timeout stops the run before a metric is invented.

## Repository map

| Path | Contents |
| --- | --- |
| `eda_pilot/` | MCP server and settings |
| `mcp_tools/` | Parameter checks, flow launch, metrics |
| `agent/` | LangGraph loop |
| `benchmarks/` | Default, random, AutoTuner, and agent harness |
| `results/final_benchmark_results.json` | Every scored trial |
| `reports/final_benchmark_report.md` | Full analysis |
| `docs/closure/` | Project closure package |
