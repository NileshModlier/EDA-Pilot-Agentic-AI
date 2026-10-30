# Interview Talking Points

Speak from the measured study. Budget 10, seed 1, sky130hd. If a number is not in this list, do not invent it.

## 1. The problem, in one sentence

Physical-design clock search is expensive, and an unconstrained language model must not be able to launch `make` or rewrite a platform file. EDA Pilot puts the model, or an offline search, behind an allowlist and a real OpenROAD flow.

## 2. The objective

The score is the smallest `_SDC_CLK_PERIOD` with DRC = 0, setup WNS ≥ 0, and hold WNS ≥ 0. Area, power, and runtime are reported for that trial. A faster clock that misses setup is a failed default run, not a win.

## 3. The result to lead with

The agent signed off gcd, AES, and Ibex. Default ORFS signed off none. Versus random search, the passing clocks were 2.867 ns versus 4.113 ns on gcd (30% tighter), 4.822 ns versus 6.261 ns on AES (23% tighter), and 9.0 ns versus 10.531 ns on Ibex (15% tighter).

## 4. The tradeoff, unprompted

Say this before the interviewer asks. The tighter clocks cost area, power, and runtime. The best agent points are 7–23% larger and 30–71% higher power than the best random points, and the Ibex agent run took about 5.5× the best random runtime. Random search is the better area and power result at a slower clock.

## 5. Why default “lost”

Default setup WNS was −1.460 ns at 1.1 ns on gcd, −0.081 ns at 3.6 ns on AES, and −0.551 ns at the 8.0 ns Ibex SDC. The agent clocks are slower than those targets. The comparison is signoff, not “we beat the default period.”

## 6. How the safety boundary works

Five nodes: analyse, propose, validate, run, check. Only analyse and propose can be a model. Validate, run, and check are code. A proposal is at most three changes, each with a parameter, a value, and a reason. `run_flow` builds the `make` argv itself, with `shell=False`. On Windows it wraps that argv into WSL and sources `env.sh`. Unknown names, strings, and out-of-range values return a tool error and do not start a process.

## 7. Signoff rate, said carefully

AES is the clean rate result: 3/10 for the agent, 1/10 for random search. gcd is 3/8 versus 4/10. Ibex is 1/1 because the search stopped when the 9.0 ns run passed and the clock gap was inside 0.05 ns. Pooled rate is about 37% for both the agent and random search. Do not quote Ibex as a 100% method over a full budget.

## 8. What failed, and what you did

Random search failures were mostly placement density (FLW-0024), detailed placement (DPL-0033), and AES global-routing congestion (GRT-0116). Two AES agent runs hit the 7200 s timeout during detailed routing. Several runs were paused and the process did not survive; those attempts were recorded as unscored and the same sample or the same clock search continued in a new variant. Completed failures were kept.

## 9. AutoTuner

The harness has an AutoTuner row. gcd and AES recorded it as unavailable because `openroad_autotuner` was not installed then. Ibex launched it and Ray exited before the first sample because HyperOpt was not visible. There are no AutoTuner area, power, or slack numbers. Do not estimate them.

## 10. What you would do next

Repair the AutoTuner environment and run the same budget, add seeds before calling the clock gains stable, and keep storing the ORFS error line with every failed trial. The agent loop itself does not need a new objective until those measurements exist.

## Questions you can ask them

- Do they score a flow on signoff clock, or on a weighted PPA number?
- Is the run budget wall-clock hours, or a fixed trial count?
- Who is allowed to add a knob: the agent, or only the allowlist owner?
