# Interview guide

How to present EDA Pilot AI in technical interviews, with model answers. **Rule one: speak only from the measured study** (sky130hd, budget 10, seed 1). If a number is not on this page or in [BENCHMARK_RESULTS.md](../BENCHMARK_RESULTS.md), do not invent it.

## Contents

- [Pitches](#pitches)
- [Numbers to know cold](#numbers-to-know-cold)
- [Likely questions](#likely-questions)
- [Architecture questions](#architecture-questions)
- [OpenROAD and physical-design questions](#openroad-and-physical-design-questions)
- [Benchmarking questions](#benchmarking-questions)
- [LangGraph questions](#langgraph-questions)
- [MCP questions](#mcp-questions)
- [Hard and skeptical questions](#hard-and-skeptical-questions)
- [Things not to say](#things-not-to-say)
- [Questions to ask them](#questions-to-ask-them)

---

## Pitches

**30 seconds.**
> "I built a guarded agent loop around OpenROAD Flow Scripts. A LangGraph agent proposes settings, and a typed tool layer, published as an MCP server, refuses anything off an allowlist before Make starts. Against default ORFS and random search on three SkyWater 130 designs, it signed off all three where the defaults failed setup, and its passing clocks were 15 to 30 percent tighter than random search, at a cost in area and power that I report alongside."

**2 minutes.** Add: the objective (smallest clock with DRC 0, setup ≥ 0, hold ≥ 0); the five nodes and which ones may use a model; the WSL bridge; that the benchmarked advisor was a deterministic bisection, which makes it a baseline; the trade-off; and what you would do next (AutoTuner, seeds, LLM advisor).

## Numbers to know cold

| | `gcd` | `aes` | `ibex` |
| --- | ---: | ---: | ---: |
| Default clock / setup WNS | 1.1 ns / −1.460 | 3.6 ns / −0.081 | 8.0 ns SDC / −0.551 |
| Random best pass | 4.113 ns | 6.261 ns | 10.531 ns |
| **Agent best pass** | **2.867 ns** | **4.822 ns** | **9.000 ns** |
| Gain vs random | 30.3% | 23.0% | 14.5% |
| Signoff: agent / random | 3/8 · 4/10 | 3/10 · 1/10 | 1/1 · 6/10 |
| Area / power vs random | +23.3% / +70.8% | +9.2% / +38.4% | +7.5% / +29.7% |
| Runtime vs random (best pass) | 1.47× | 1.65× | 5.53× |

Pooled signoff rate: agent 7/19 (36.8%), random 11/30 (36.7%), default 0/3. In total, 52 scored runs, about 21.2 h of flow time, 6 unscored interruptions and 48 unit tests.

---

## Likely questions

**Q: Walk me through the project.**
A: The problem is that physical-design runs are slow and defaults do not necessarily close timing. Engineers search for a clock that does. I wanted an agent that could do that search *safely*. The system has a benchmark harness, a LangGraph agent, a tool layer exposed as an MCP server, guardrails, a WSL execution bridge into ORFS, and metrics read from `metadata.json`. The agent proposes, and code validates, launches and scores. I benchmarked it against default ORFS and seeded random search with the same 10-run budget. The headline is 3/3 signoffs against 0/3 for default, and passing clocks 14.5 to 30.3% tighter than random.

**Q: What was the hardest part?**
A: Running the campaign more than writing the agent. A run takes from one minute to two hours, so the campaign had to survive interruptions. Manifests said `running` after the process had died, timeouts were hit, and the agent's checkpoint was written only at session end. I had to define unscored interruptions, resume in new flow variants without double-counting, and replay decision logs into the same clock bounds.

**Q: What would you do differently?**
A: Checkpoint the agent after every iteration, capture the ORFS error line in every failed trial, clamp the search step to the current bracket, and budget in wall-clock hours rather than runs. I would also get AutoTuner working before the campaign, not during it.

**Q: What are you most proud of?**
A: That the result is honest. The README says, next to the win, that random search has better area and power, that `ibex` is one run at the range floor, and that the benchmarked advisor was not an LLM. Those caveats make the numbers trustworthy.

---

## Architecture questions

**Q: Why separate "propose" from "validate"?**
A: A model's output is untrusted input. `propose` returns a Pydantic `Proposal`, with at most 3 changes, each with a reason, and no extra fields. `validate` is plain code that checks every value against the allowlist and step grid. If it fails, the proposal goes back with the message, up to three times, and then the iteration is logged as rejected. A model can be wrong as often as it likes, and it still cannot start a flow with an illegal value.

**Q: How do you stop command injection?**
A: There is no shell. The `make` argv is assembled from fixed templates and regex-checked tokens and run with `subprocess.Popen(..., shell=False)`. Values must be finite numbers. Booleans, strings, NaN and infinity are rejected, so a value cannot carry text. Design names must match `^[a-z][a-z0-9_]*$`. The WSL bridge is the only place a bash script is built, and it uses only tokens that already passed those checks.

**Q: How is the clock applied without editing design files?**
A: ORFS reads the clock from the SDC. For each run the server copies `constraint.sdc` to `flow/.eda_pilot/sdc/<run_id>/`, rewrites the single `set clk_period` line, and points the flow at the copy. If there is not exactly one such line, the run is refused. The design directory is never written.

**Q: What stops a runaway agent from burning compute?**
A: A server-wide run budget held under a file lock, so concurrent clients cannot both take the last run. There is also a per-run timeout that kills the whole process tree (`killpg` on Linux, `taskkill /T` on Windows), and the agent refuses to start if its own budget exceeds the server's.

**Q: Why WSL?**
A: OpenROAD and ORFS are supported on Linux, and the host was Windows. The first real run failed because `make` exists only inside WSL. Rather than port the flow, `run_flow` detects a `\\wsl$\<distro>\…` path and runs the same validated argv through `wsl.exe -d <distro> -- bash -lc`, sourcing `env.sh`, then `make … finish`, then `make … metadata-generate`.

**Q: How do you test without OpenROAD?**
A: The 48 tests use a `make` stand-in (`tests/fake_make.py`) that writes realistic `metadata.json` and report files. They cover allowlist rejections, argv construction, the WSL quoting, timeouts, metrics aliasing, report caps, an in-process MCP client session, the agent's budget and stop rules, and the harness's ranking.

---

## OpenROAD and physical-design questions

**Q: What does the flow actually do?**
A: Yosys synthesizes RTL to sky130hd standard cells. OpenROAD does floorplan, placement, CTS, timing repair, global and detailed routing, and static timing and power analysis. KLayout writes the final GDS. ORFS drives it all with Make targets, and `metadata-generate` collects METRICS2.1 values into `metadata.json`.

**Q: What are setup and hold WNS?**
A: Worst negative slack. Setup slack is how much earlier than required data arrives before the capturing clock edge. Negative means the path is too slow for the clock period. Hold slack is about data changing too soon after the edge. Signoff needs both ≥ 0, plus zero DRC violations.

**Q: Why does a tighter clock cost area and power?**
A: To meet a shorter period, timing repair upsizes cells and inserts buffers on critical paths, and the router has less slack to work with. Larger, faster cells mean more area and more switching and leakage power. On `gcd` the agent's 2.867 ns point used 23.3% more area and 70.8% more power than random's 4.113 ns point.

**Q: Why did the default ORFS clocks fail?**
A: The defaults are aggressive targets, not closure guarantees. On this toolchain and PDK they missed setup by −1.460 ns (`gcd`), −0.081 ns (`aes`) and −0.551 ns (`ibex`), with DRC 0. The flow "finishes" and the design still does not meet its constraint.

**Q: What were the random-search failures?**
A: Feasibility errors. Placement density above 1.0 (FLW-0024, 5 runs), detailed placement check failures (DPL-0033, 5), global-routing congestion on `aes` (GRT-0116, 2) and one other Make error. They came from aggressive combinations of utilization, density add-on and padding.

**Q: What is `FLOW_VARIANT` for?**
A: It gives each run its own results, logs and reports directory in ORFS. The server generates `p1<uuid hex>` per run, so runs never overwrite each other and every metric traces to exactly one launch.

---

## Benchmarking questions

**Q: How did you make the comparison fair?**
A: Same allowlist, flow, toolchain, timeout, budget (10) and seed (1) for every method, and one ranking function. Passes are ranked by (clock, area, power, runtime) and fails by (setup WNS, DRC, hold WNS). Random search actually had a *larger* action space than the agent, because it sampled every knob.

**Q: Why rank by clock first?**
A: That was the question: the fastest legal clock. Area and power are reported for that point and break ties, but they cannot override a tighter pass. I say explicitly that a PPA-weighted score could rank the methods differently.

**Q: Is the signoff-rate comparison meaningful?**
A: Partly. Pooled, it is a tie (36.8% against 36.7%). `aes` is the clean gain, 3/10 against 1/10. `ibex` is 1/1 because the agent converged on its first run, so I never quote it as 100%.

**Q: How do you handle runs that were interrupted?**
A: If the parent process died and the manifest still said `running`, the attempt is an *unscored interruption*. It is not counted as a trial, and the same sample or clock search continued in a new flow variant. There were six. They are listed separately in the results JSON.

**Q: What about AutoTuner?**
A: It is in the harness and produced no scored trials. The executable was missing for `gcd` and `aes`, and on `ibex` Ray could not import HyperOpt before the first sample. I report it as unavailable or error and do not estimate numbers.

**Q: What is the statistical weakness?**
A: One seed, one PDK and a budget of 10. The 14.5–30.3% gains are single samples. The next step is multiple seeds, reporting the distribution of best passing clocks.

---

## LangGraph questions

**Q: Why LangGraph?**
A: The control flow has real branches: validation retries, a give-up-after-three path, and two stop conditions. A `StateGraph` makes those edges explicit and testable, and the typed state means every node's inputs and outputs end up in the decision log.

**Q: Describe the graph.**
A: `START → analyse → propose → validate`. From `validate` there are three conditional edges: `run` if legal, `propose` if rejected with attempts left, and `check` after the third rejection. `run → check`. From `check`, it goes to `END` if the budget is spent or a pass exists with `clock_high − clock_low < 0.05 ns`, and otherwise back to `analyse`.

**Q: What is in the state?**
A: Design, platform, objective, remaining budget, history, current metrics, report summaries, best run, clock bounds, the parameter catalog, the current proposal, validation attempts and message, and the last run's status, runtime and id.

**Q: How would a chat model plug in?**
A: Set `EDA_PILOT_MODEL`. LangChain's `init_chat_model` loads it, and `analyse` and `propose` call it with structured output into `Diagnosis` and `Proposal`. The system prompt forbids commands, inventing metrics and `_FR_LAYER_ADJUST`. Nothing else changes, because validation, run and check stay code.

**Q: How does it decide it is done?**
A: Two rules in `check`: the budget is exhausted, or there is a passing run and the clock bracket is narrower than 0.05 ns. On `gcd` it stopped after 8 runs with a 0.03 ns bracket. On `ibex` it stopped after one, because 9.0 ns passed at the range floor and the bracket collapsed to zero.

---

## MCP questions

**Q: Which tools does the server expose?**
A: Four. `list_params(design, platform)` returns knobs with type, range, default, step and `executable`. `run_flow(design, platform, params)` returns run id, status, runtime and variant. `get_metrics(run_id)` returns WNS/TNS, power, area, utilization, DRC and a `missing` list. `read_report(run_id, report_name)` returns a capped tail of timing, DRC or congestion.

**Q: Why MCP instead of just a Python API?**
A: The tool layer is the one place a proposal becomes a process. Exposing it over MCP means any client, whether MCP Inspector, an IDE assistant or another agent, gets exactly the same validation, budget and timeout guarantees. The built-in agent calls the same functions in process, so there is one implementation of the policy.

**Q: Did the benchmarked agent go through the MCP transport?**
A: No, and I say so. The agent imports the `mcp_tools` functions directly. The server wraps the same functions and is tested with an in-process MCP client session. Bypassing the transport gives no extra power, because the policy lives in the functions, not in the protocol.

**Q: How does `read_report` avoid becoming a file-read primitive?**
A: The report name is an enum (`timing`, `drc`, `congestion`) mapped to fixed files (`6_finish.rpt`, `5_route_drc.rpt`, `5_global_route.rpt`). It is never a path. It returns at most 200 lines, reads at most 512 KB and caps each line at 2,000 characters.

**Q: How are errors surfaced?**
A: Anticipated failures (`FlowValidationError`, `ConfigurationError`) become MCP `ToolError`s with a plain message, for example "validation error: _SDC_CLK_PERIOD 9.5 is above maximum 5.0". A rejected call never creates a run, consumes budget or starts a process.

**Q: Which SDK?**
A: The official MCP Python SDK 2.x. In 2.x FastMCP was renamed `MCPServer`, and the decorator API (`@mcp.tool()`) is the same. The transport is stdio, and the console script is `eda-pilot-orfs`.

---

## Hard and skeptical questions

**Q: Isn't this just binary search?**
A: The benchmarked *policy* is, and that is deliberate. A guarded bisection on the clock is the simplest strong baseline for "smallest passing clock". It is reproducible, free and explainable. The contribution is the safe loop around it (allowlist, typed proposals, no shell, budget, timeout, decision log) and an honest comparison showing that even this policy beats unguided random search on the primary objective. The open question, which I list as next work, is whether a chat model's diagnosis beats this baseline. Without the baseline you could not even ask that.

**Q: So where is the AI?**
A: In the architecture and the path it opens. The LangGraph agent has a model slot in `analyse` and `propose`, built with structured output and tested with injected advisors. The measured study used the deterministic advisor so the result would be reproducible. I would rather show a real, safe loop with a modest policy than an LLM demo without a baseline.

**Q: Random search found smaller, lower-power designs. Didn't it win?**
A: On area, power and runtime, yes, and I say so in the headline. It did that at clocks 14.5–30.3% slower. If the goal is the fastest legal clock, the agent wins. If it is PPA at a fixed clock, random search's points are better. A hybrid policy (bisect the clock, then tune area at that clock) is on the roadmap.

**Q: `ibex` at 9.0 ns, isn't that just the range floor?**
A: Yes. The allowlist floor for `ibex` is 9.0 ns, the agent started there, and that run passed. The true limit may be lower. Widening the floor is on the roadmap. It is still 14.5% tighter than random's best, but it is one run.

**Q: `aes` passed at 4.822 ns and failed at 4.832 ns. Doesn't that break bisection?**
A: It shows slack is only approximately monotonic near the boundary, because placement and routing change with the constraint. Bisection still finds a good bracket, but the reported value is a passing point in a bracket, not a proof of the limit. That 4.832 ns run also exposed a small policy gap. After a timeout, the minimum step was clamped to the range but not to the bracket.

**Q: Could the agent ever run something dangerous?**
A: Not through these tools. Unknown names, non-numbers, out-of-range values, off-grid values, `_FR_LAYER_ADJUST` and over-budget calls are all rejected before any directory or process exists. There is no shell, and the design files are read-only. The remaining risk is resource use within the policy, which the budget and timeout bound.

**Q: How do I know the numbers are real?**
A: Every scored run is in `results/final_benchmark_results.json`, with per-run manifests, logs and decision logs in the repo. The plots are redrawn from that JSON by a script. Failures, timeouts and interruptions are kept. Nothing was re-run or tuned for the release.

---

## Things not to say

- ❌ "The LLM found a 30% faster clock." The benchmarked advisor was offline bisection.
- ❌ "The agent beat the default clock." The default clocks are faster. They fail setup.
- ❌ "100% signoff rate on `ibex`." It was 1 run.
- ❌ "Better PPA." Random search had better area and power.
- ❌ Any AutoTuner number. There are none.
- ❌ "Statistically significant." It is one seed.

## Questions to ask them

- Do you score flows on signoff clock, or on a weighted PPA number?
- Is your exploration budget counted in wall-clock hours or in runs?
- Who is allowed to add a tunable knob: the agent, or only the owner of the allowlist?
- How do you handle runs interrupted by infrastructure, rather than by the design?
