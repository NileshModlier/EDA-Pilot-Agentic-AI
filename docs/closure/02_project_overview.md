# EDA Pilot AI

One-page overview. Platform sky130hd. Budget 10. Seed 1.

## What it is

EDA Pilot AI searches for the fastest clock that still signs off in OpenROAD Flow Scripts. The agent may change only allowlisted parameters. The MCP server rejects anything else before `make` starts. On Windows, the flow runs inside WSL Ubuntu with Yosys, OpenROAD, and KLayout.

## How a run moves

1. The agent reads the last metrics and proposes at most three parameter changes, each with a reason.
2. Code validates the proposal against `configs/allowed_parameters.json` and the design `autotuner.json` ranges.
3. `run_flow` starts `make finish` for a unique variant, then generates `metadata.json`.
4. `get_metrics` and `read_report` return slack, power, area, DRC, and report tails.
5. The loop stops on a converged passing clock (gap under 0.05 ns) or when the budget is exhausted.

With no chat model configured, analyse and propose use an offline clock search. Those two nodes cannot launch a flow.

## What was measured

| Design | Default signoff | Random best clock | Agent best clock |
| --- | --- | ---: | ---: |
| gcd | No, setup −1.460 ns at 1.1 ns | 4.113 ns | **2.867 ns** |
| AES | No, setup −0.081 ns at 3.6 ns | 6.261 ns | **4.822 ns** |
| Ibex | No, setup −0.551 ns at the 8.0 ns SDC | 10.531 ns | **9.000 ns** |

DRC is 0 on every finished flow in the study, including the default runs that miss setup. The agent’s passing points use more area and power, and more runtime, than random search.

## What is finished

MCP server, LangGraph agent, benchmark harness, and the WSL path into OpenROAD, Yosys, and KLayout. gcd, AES, and Ibex benchmarks are recorded in `results/final_benchmark_results.json` and `reports/final_benchmark_report.md`. AutoTuner was scheduled and produced no scores.

## What to read next

`reports/final_benchmark_report.md` for the full tables. `docs/closure/07_architecture.svg` and `08_technology_stack.svg` for the structure.
