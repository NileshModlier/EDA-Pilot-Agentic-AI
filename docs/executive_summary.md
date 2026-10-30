# Executive summary

**EDA Pilot AI** · v1.0.0 · October 2026 · status: complete

## The one-line version

A guarded agent loop around OpenROAD Flow Scripts signed off **3 of 3** sky130hd designs where the default flow signed off **0 of 3**, and found passing clocks **14.5–30.3% tighter than random search** under the same 10-run budget. It paid for that with more area, power and runtime.

## What was built

- **A LangGraph agent** (`analyse → propose → validate → run → check`). Only the first two nodes may use a model. Validation, flow launch, metric parsing and the stop decision are code.
- **An MCP server** (`eda-pilot-orfs`) with four typed tools: `list_params`, `run_flow`, `get_metrics` and `read_report`. It refuses any parameter outside a published allowlist *before* GNU Make starts, never uses a shell, enforces a run budget and a timeout, and applies clock changes through a private copy of the SDC.
- **A Windows-to-WSL execution bridge** that runs Yosys, OpenROAD and KLayout through `make finish` and `make metadata-generate`.
- **A benchmark harness** that runs default ORFS, seeded random search, OpenROAD AutoTuner and the agent under one budget and seed, and ranks them by smallest passing clock.

## The question

Can the loop find a smaller clock than default ORFS and random search, while still signing off? Signoff means the flow finishes, DRC = 0, setup WNS ≥ 0 and hold WNS ≥ 0.

## The answer

| Design | Default ORFS | Random search | **EDA Pilot** | Tighter than random |
| --- | --- | ---: | ---: | ---: |
| `gcd` | fails setup (−1.460 ns) | 4.113 ns | **2.867 ns** | 30.3% |
| `aes` | fails setup (−0.081 ns) | 6.261 ns | **4.822 ns** | 23.0% |
| `ibex` | fails setup (−0.551 ns) | 10.531 ns | **9.000 ns** | 14.5% |

- **Signoff rate.** Agent 7/19 (36.8%), random 11/30 (36.7%) pooled. The agent did clearly better on `aes`, at 3/10 against 1/10.
- **Trade-off.** At the best points the agent used 7–23% more area, 30–71% more power and 1.5–5.5× the runtime of random search.
- **AutoTuner** produced no scored trials (not installed for two designs, and a Ray/HyperOpt error on the third).

## What the result does and does not mean

| It shows | It does not show |
| --- | --- |
| An agent loop can drive a real PDK flow with **zero** out-of-policy executions | That a language model out-searches classical optimizers. The benchmarked advisor was a deterministic clock bisection |
| Signoff-first ranking avoids "winning" with a failing clock | That the gains are stable across seeds. One seed was run |
| Bisection on the clock beats unguided random sampling for the tightest passing clock | That the agent is better on area or power. Random search wins those |

## Why it matters

Physical-design runs are slow (≈1 minute to ≈2 hours each here), and defaults do not necessarily close timing. A safe, auditable loop, where every decision is logged with a reason and every action is validated in code, is the prerequisite for letting any AI system near a production flow. This project builds that loop and gives it an honest baseline.

## Next

1. Repair AutoTuner and add it to the comparison.
2. Repeat at more seeds.
3. Benchmark a chat-model advisor against the bisection baseline.

More: [Case study](../CASE_STUDY.md) · [Benchmark results](../BENCHMARK_RESULTS.md) · [Roadmap](roadmap.md)
