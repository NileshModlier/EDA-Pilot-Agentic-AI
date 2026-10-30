# Lessons learned

These come from building the system and running the 52-run sky130hd campaign. Each lesson names what happened, what it cost, and what changed.

## Objective and evaluation

### 1. A passing clock is a different objective from a fast default
**What happened.** Default ORFS finished `gcd`, `aes` and `ibex` with DRC = 0, and all three failed setup (−1.460, −0.081 and −0.551 ns).
**Lesson.** Ranking by clock alone would have rewarded a broken constraint. Signoff (DRC = 0, setup ≥ 0, hold ≥ 0) has to be the gate before any clock comparison.

### 2. The tighter clock spends area, power and time
**What happened.** On every design, random search's best signoff was smaller, lower power and faster to produce than the agent's.
**Lesson.** The agent won because the primary key was clock. A PPA-weighted score would rank the methods differently. Say the trade-off in the same sentence as the win.

### 3. Early stop is a sample-size statement
**What happened.** `ibex` converged on its first run (9.0 ns, the range floor) and stopped.
**Lesson.** That is a correct stop under the 0.05 ns rule, and it is a single observation. Quoting "100% signoff" next to `aes`'s 10 runs overstates the evidence. Always publish the denominator.

### 4. Slack is only approximately monotonic in clock
**What happened.** `aes` passed at 4.822 ns and failed at 4.832 ns by −0.0056 ns.
**Lesson.** Placement and routing change with the constraint, so bisection's monotone assumption holds only roughly near the boundary. Report the bracket, not a single "true limit".

## Agent design

### 5. Keep the model off the launch path
**What happened.** `analyse` and `propose` only suggest. Validation, `make` and metric parsing stayed in code for the entire campaign. Illegal proposals in tests never started a process.
**Lesson.** Safety by construction beats safety by prompt. New knobs enter through `configs/allowed_parameters.json`, not through a prompt.

### 6. A deterministic baseline is worth more than it looks
**What happened.** The offline bisection advisor produced the whole measured result.
**Lesson.** It is reproducible, free and explainable, and it sets the bar a chat model has to clear. Without it, an LLM result would have nothing honest to be compared against.

### 7. Clamp search steps to what you already know
**What happened.** On `aes`, after a timeout at 4.782 ns the bisection midpoint repeated the last clock, so the advisor stepped up by its 0.05 ns minimum to 4.832 ns. That is above an existing pass at 4.822 ns. The step was clamped to the allowed range, not to the current bracket, and it spent the final run of the budget.
**Lesson.** Decision logs with a reason per step make policy gaps like this easy to find. The fix is to clamp to `[clock_low, clock_high]` and treat a timeout as information.

### 8. One dimension is a choice, not a law
**What happened.** The agent only moved `_SDC_CLK_PERIOD`. The DRC-triggered utilization change never fired, because every finished run had DRC = 0.
**Lesson.** Random search's failures were all feasibility failures (density, placement, congestion), and the agent's were all timing. The two are complementary, which points to a hybrid policy.

## Flow integration

### 9. Windows cannot see GNU Make
**What happened.** The first real `run_flow` failed with `FileNotFoundError` (WinError 2), because `make` exists only inside WSL.
**Lesson.** A narrow bridge (detect a `\\wsl$\<distro>\…` flow path and wrap the *same validated argv* in `wsl.exe … bash -lc`) was safer than porting Make or opening a general shell.

### 10. `finish` does not write `metadata.json`
**What happened.** Successful GDS runs could not be scored, because `metadata.json` was missing.
**Lesson.** `make … metadata-generate` must follow every successful `finish`. Integration tests should assert the presence of the artefact you score from, not just exit code 0.

### 11. Source the environment for every launch
**What happened.** The flow needs `env.sh` for tool paths inside WSL.
**Lesson.** The bridge sources `../env.sh` in the same `bash -lc` invocation as `make`, so that no launch depends on the state of an interactive shell.

## Running a long campaign

### 12. A `running` manifest is not a live run
**What happened.** Several `aes` and `ibex` manifests stayed at `status: running` after the parent process died, including during an overnight pause.
**Lesson.** Check liveness with the process list and the log timestamps. Record dead attempts as **unscored interruptions** (six in this study) and continue in a new flow variant. Replaying a half-finished route database would have inflated runtime across the gap.

### 13. Checkpoint after every scored trial
**What happened.** Random search resumed cleanly because each trial was written before the next started. The agent's checkpoint row was written only at session end, so a killed agent needed its decision log replayed into the same clock bounds.
**Lesson.** Checkpoint the agent's bounds after every iteration. Re-running multi-hour `aes` flows is the alternative.

### 14. Timeouts are part of the budget
**What happened.** Two `aes` agent runs ended with status `timeout`. Their recorded run times are 8,032 s and 9,933 s, both above the 7,200 s limit. The record does not break down where the extra time went.
**Lesson.** A run budget counted in *runs* hides a 100× cost spread between designs. Future budgets should count wall-clock hours.

### 15. Store the error line, not the exit status
**What happened.** The `gcd` campaign file stored only `ORFS exited with status 2` for four failures. The logs showed FLW-0024 and DPL-0033.
**Lesson.** Capture the ORFS error line into the trial record when `make` exits, or the failure analysis becomes archaeology.

## Tooling and methodology

### 16. Tool installation is part of the method
**What happened.** AutoTuner's executable was missing during the `gcd` and `aes` campaigns. A later install failed on the pinned Ray release under the system Python. A Python 3.12 environment imported the CLI, but on `ibex` Ray could not import HyperOpt before the first sample.
**Lesson.** An unmeasured method has to stay empty. "Unavailable" and "error" are results, and estimates are not.

### 17. Helper scripts encode their host
**What happened.** Several probe and campaign scripts hardcode `/home/administrator/…` and `\\wsl$\Ubuntu\…` paths.
**Lesson.** That was fine for one machine and is a barrier for anyone else. Paths belong in `ORFS_ROOT`-style settings, which the core package already uses.
