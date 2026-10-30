# EDA Pilot AI: summary for hiring managers

**Nilesh P Raghavan** · [github.com/NileshModlier/EDA-Pilot-AI](https://github.com/NileshModlier/EDA-Pilot-AI) · v1.0.0, October 2026

## TL;DR

A solo, end-to-end project that puts an agent in charge of a real RTL-to-GDS flow without trusting it. A LangGraph loop proposes ORFS parameters. A typed tool layer, published as an MCP server, enforces an allowlist, a run budget and timeouts before GNU Make starts. Benchmarked on sky130hd `gcd`, `aes` and `ibex` against default ORFS and seeded random search (budget 10, seed 1), it signed off **3/3 designs against 0/3** and found passing clocks **14.5–30.3% tighter than random**, with the area, power and runtime costs reported next to the win.

## Scope and ownership

| Area | What the candidate did |
| --- | --- |
| Problem framing | Defined the objective as the smallest clock with DRC = 0, setup ≥ 0 and hold ≥ 0, because the defaults "finish" while failing setup |
| Architecture | Six layers with narrow typed interfaces: harness → agent → tool/MCP layer → guardrails → WSL bridge → ORFS |
| Agent | Five-node LangGraph `StateGraph` with retry routing, two stop rules and a JSONL decision log. Pluggable advisor (deterministic bisection, or a chat model via `EDA_PILOT_MODEL`) |
| Safety | Allowlist with tighten-only design overrides, numeric-only values, regex-checked argv, `shell=False`, private SDC copies, a file-locked budget and process-tree kill on timeout |
| Integration | Diagnosed and fixed a Windows/WSL Make failure. Added `metadata-generate` after `finish` so runs can be scored |
| Benchmarking | Built the harness, ran 52 scored flows (~21 h), handled timeouts and six interruptions, and wrote a resumable campaign with checkpoints |
| Quality | 48 pytest tests with a `make` stand-in. Plots regenerated from a single results JSON |
| Communication | Architecture docs, benchmark report with every trial, case study, roadmap, lessons learned |

## Results

| Design | Default | Random best pass | **Agent best pass** | Δ clock | Δ area / power |
| --- | --- | ---: | ---: | ---: | ---: |
| `gcd` | fails, −1.460 ns | 4.113 ns | **2.867 ns** | −30.3% | +23.3% / +70.8% |
| `aes` | fails, −0.081 ns | 6.261 ns | **4.822 ns** | −23.0% | +9.2% / +38.4% |
| `ibex` | fails, −0.551 ns | 10.531 ns | **9.000 ns** | −14.5% | +7.5% / +29.7% |

Pooled signoff rate is about even (36.8% against 36.7%). `aes` improved from 1/10 to 3/10.

## Signals of engineering judgment

1. **Safety by construction, not by prompt.** The model is never on the launch path. A wrong proposal costs a validation message, not a flow.
2. **An honest baseline first.** The measured agent used a deterministic bisection advisor, and the docs say so plainly. That makes the result reproducible and gives any future LLM advisor a bar to clear.
3. **Trade-offs reported with the win.** Random search had better area, power and runtime. `ibex` is one run at the range floor. AutoTuner produced no scores and none were estimated.
4. **Operational realism.** It distinguishes unscored interruptions from failures, documents why a `running` manifest is not a live process, and found a search-step policy gap from the decision logs.
5. **Scoped next steps.** AutoTuner, multiple seeds, then an LLM advisor, in that order, because each depends on the previous measurement.

## Where this candidate fits

- **EDA / CAD tooling and flow-automation teams**: ORFS/OpenROAD fluency, timing-closure framing, METRICS2.1, campaign management.
- **AI-agent and LLM-platform teams**: LangGraph state machines, MCP server design, structured outputs, tool-safety boundaries.
- **ML-for-systems / design-space exploration**: benchmark methodology, baselines, failure-mode analysis.

## Suggested interview probes

- "Why is the model only allowed in two of the five nodes?"
- "Random search got smaller designs. How do you argue your method won?"
- "Your best `ibex` result is at the range floor. What does that tell you?"
- "How did you keep the benchmark fair when one method samples more knobs?"
- "Walk me through what happens when a run is interrupted mid-route."

Model answers are in [docs/interview_guide.md](../docs/interview_guide.md).

## Read in 10 minutes

[README](../README.md) → [Executive summary](../docs/executive_summary.md) → [Case study](../CASE_STUDY.md) → [Benchmark results](../BENCHMARK_RESULTS.md)
