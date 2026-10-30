# EDA Pilot AI: project overview

> **Status:** complete (v1.0.0, 2026-10-29) · **Platform:** SkyWater SKY130 HD · **Designs:** `gcd`, `aes`, `ibex` · **Budget:** 10 runs per search method · **Seed:** 1

## In one paragraph

EDA Pilot AI searches OpenROAD Flow Scripts for the **fastest clock that still signs off**. A LangGraph agent decides what to try next. An MCP server decides whether the agent is *allowed* to try it, and only then launches GNU Make, Yosys, OpenROAD and KLayout. In a head-to-head benchmark the agent signed off all three designs where the default flow signed off none. Its passing clocks were **14.5–30.3% tighter than seeded random search**, at a cost in area, power and runtime that the project reports alongside the win.

## The problem

- A physical-design run (synthesis → floorplan → placement → CTS → routing → finish) takes from about **a minute (`gcd`) to almost two hours (`ibex`)** per attempt. Every guess is expensive.
- The default ORFS clock targets for `gcd`, `aes` and `ibex` **fail setup timing** on sky130hd. Engineers must search for a period that closes.
- Agents that can type shell commands or edit platform files are unsafe to point at a real flow.

## The approach

| Layer | What it does | Where |
| --- | --- | --- |
| Benchmark harness | Runs default ORFS, random search, AutoTuner and the agent under the same budget and seed. Ranks them by smallest passing clock | `benchmarks/` |
| LangGraph agent | `analyse → propose → validate → run → check`. Only the first two may use a model. A proposal has at most 3 changes, each with a reason. The loop stops when the budget is spent or the passing-clock gap is under 0.05 ns | `agent/` |
| MCP server | `list_params`, `run_flow`, `get_metrics`, `read_report` over stdio | `eda_pilot/server.py` |
| Guardrails | Allowlist with tighten-only design overrides, typed values, regex-checked argv with `shell=False`, run budget lock, timeout with process-tree kill, private SDC copy | `mcp_tools/` |
| Execution | WSL bridge: `wsl.exe … bash -lc '. env.sh; make … finish; make … metadata-generate'` | `mcp_tools/run_flow.py` |
| Metrics | METRICS2.1 `metadata.json` → WNS/TNS, power, area, utilization, DRC | `mcp_tools/metrics.py` |

## Results

| Design | Default ORFS | Random best pass | **Agent best pass** | Gain vs random |
| --- | --- | ---: | ---: | ---: |
| `gcd` | ❌ 1.1 ns, setup WNS −1.460 ns | 4.113 ns | **2.867 ns** | **30.3%** |
| `aes` | ❌ 3.6 ns, setup WNS −0.081 ns | 6.261 ns | **4.822 ns** | **23.0%** |
| `ibex` | ❌ 8.0 ns (SDC), setup WNS −0.551 ns | 10.531 ns | **9.000 ns** | **14.5%** |

- **Signoff:** agent 3/3 designs, default 0/3. Pooled signoff rate: agent 7/19 (36.8%), random 11/30 (36.7%). `aes` improved most, from 1/10 to 3/10.
- **Trade-off:** at the best passing points the agent used +7.5% to +23.3% area, +29.7% to +70.8% power and 1.47× to 5.53× runtime compared with random search.
- **AutoTuner:** scheduled, but it produced no scored trials (not installed for `gcd`/`aes`, and a Ray/HyperOpt import error on `ibex`).

## What was built

- About 3,500 lines of Python across the server, tools, agent and harness, about 1,300 lines of tests, and about 2,700 lines of environment probes and campaign scripts.
- **48 unit tests** that run without OpenROAD, using a `make` stand-in.
- **52 scored ORFS runs** (~21 hours of flow wall-clock) and 6 unscored interruptions, all in `results/final_benchmark_results.json`.
- Reports, plots, diagrams and this documentation set.

## Honest scope

- The benchmarked agent used the **offline advisor**: a deterministic, guarded bisection on `_SDC_CLK_PERIOD`. The chat-model path (`EDA_PILOT_MODEL`) plugs into the same two nodes. The tests exercise those nodes with injected advisors, but no chat model was part of the measured study.
- One platform, one seed, and a budget of 10. The `ibex` agent stopped after a single passing run at the floor of its allowed clock range (9.0 ns).

## Read next

[README](README.md) · [Architecture](ARCHITECTURE.md) · [Benchmark results](BENCHMARK_RESULTS.md) · [Case study](CASE_STUDY.md) · [Executive summary](docs/executive_summary.md)
