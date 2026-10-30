# Benchmark results

> **Scope.** SkyWater SKY130 HD (`sky130hd`) · designs `gcd`, `aes`, `ibex` · run budget 10 per search method · seed 1 · OpenROAD Flow Scripts through WSL Ubuntu.
> **Source of truth.** [`results/final_benchmark_results.json`](results/final_benchmark_results.json), which holds 52 scored runs, per-method summaries and 6 unscored interruptions. No new flows were run for this release. Every number below is taken from that file and from [`reports/final_benchmark_report.md`](reports/final_benchmark_report.md).

## Contents

1. [Headline](#headline)
2. [Methodology](#methodology)
3. [Experimental setup](#experimental-setup)
4. [Results by design](#results-by-design)
5. [Leaderboard](#leaderboard)
6. [Signoff rate](#signoff-rate)
7. [QoR trade-off](#qor-trade-off)
8. [Runtime](#runtime)
9. [How each method searched](#how-each-method-searched)
10. [Failure analysis](#failure-analysis)
11. [Key findings](#key-findings)
12. [Limitations](#limitations)
13. [Reproducing the figures](#reproducing-the-figures)
14. [Appendix: every scored trial](#appendix-every-scored-trial)

## Headline

| Design | Default ORFS | Random search | **EDA Pilot agent** | Passing clock vs random |
| --- | --- | ---: | ---: | ---: |
| `gcd` | no signoff (setup WNS −1.460 ns at 1.1 ns) | 4.113 ns | **2.867 ns** | **−30.3%** |
| `aes` | no signoff (setup WNS −0.081 ns at 3.6 ns) | 6.261 ns | **4.822 ns** | **−23.0%** |
| `ibex` | no signoff (setup WNS −0.551 ns at the 8.0 ns SDC) | 10.531 ns | **9.000 ns** | **−14.5%** |

The agent signed off **3 of 3** designs and default ORFS **0 of 3**. Against random search the agent wins the primary objective, the smallest passing clock, on every design. It **loses** area, power and runtime at those points.

![Smallest passing clock](plots/leaderboard_summary.png)

## Methodology

**Objective.** Find the smallest `_SDC_CLK_PERIOD` for which the flow signs off. Area, power and runtime are reported for that result, but they never override a tighter passing clock.

**Signoff.** A run signs off only when all four hold:

| Condition | Source |
| --- | --- |
| Flow status `ok` (exit 0 within the timeout) | `run_flow` |
| DRC count = 0 | `metadata.json` |
| Setup WNS ≥ 0 | `metadata.json` |
| Hold WNS ≥ 0 | `metadata.json` |

**Methods.**

| Method | What it does | Budget |
| --- | --- | --- |
| **Default ORFS** | One run with no parameter overrides, the design's own `config.mk` and `constraint.sdc` | 1 |
| **Random search** | `random.Random(1)`. Each trial samples **every executable knob** uniformly from its allowlisted range (clock, core utilization, aspect ratio, core margin, global and detailed placement padding, placement density add-on, CTS cluster size and diameter). Samples are redrawn until they validate | 10 |
| **EDA Pilot agent** | The LangGraph loop with the **offline advisor**: it starts from the design default clock (clamped into range), then bisects the clock bounds from the observed pass/fail. It stops when the passing-clock gap is under 0.05 ns or the budget is spent | 10 (early stop allowed) |
| **OpenROAD AutoTuner** | `openroad_autotuner … tune --samples 10 --seed 1 --algorithm hyperopt`. A missing executable or a crash is recorded as such, with no metrics filled in | 10 |

> **Important.** The benchmarked agent ran in **offline-advisor mode** (`advisor: offline` in every decision-log line). No chat model made decisions in this study. The result measures the guarded LangGraph loop and its bisection policy. An LLM advisor has not been benchmarked yet.

**Ranking.** Passing trials are ordered by (clock, area, power, runtime), and failing trials by (setup WNS, DRC, hold WNS). See `benchmarks/compare_results.py`.

**Runtime.** Flow-process wall-clock as measured by `run_flow`. The metadata runtime field is a clock string and is not used.

## Experimental setup

| Item | Value |
| --- | --- |
| Platform / PDK | `sky130hd` (SkyWater SKY130, high-density cells) |
| Designs | `gcd` (small arithmetic block), `aes` (AES cipher core), `ibex` (Ibex RISC-V core) |
| Flow | OpenROAD Flow Scripts, `make finish` + `make metadata-generate`, unique `FLOW_VARIANT` per run |
| Tools | Yosys 0.68+, OpenROAD `26Q4-110-g91e5f5ff2f`, KLayout 0.30.0, GNU Make 4.4.1 |
| Host | Windows with WSL Ubuntu 26.04 LTS (the flow runs inside WSL) |
| Budget / seed | 10 / 1 for random, agent and AutoTuner. Default runs once |
| Flow timeout | 7,200 s on the resumed `aes` / `ibex` campaign |
| Clock ranges | `gcd` 0.8–5.0 ns · `aes` 3.5–7.0 ns · `ibex` 9.0–16.0 ns (from each design's `autotuner.json`) |
| Campaign | `gcd` in the first campaign directory, not rerun. `aes` and `ibex` through a checkpointed resume |

## Results by design

Best signoff run per method. Default never signed off, so its row is its single run.

### `gcd`

| Method | Runs | Signoff | Clock (ns) | Area (µm²) | Power (mW) | Setup WNS (ns) | Hold WNS (ns) | DRC | Runtime (s) |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 1 | ❌ | 1.100 | 5,412.69 | 9.850 | −1.460 | 0.532 | 0 | 118.4 |
| Random | 10 | ✅ | 4.113 | 3,361.97 | 1.570 | 0.476 | 0.558 | 0 | 51.0 |
| **Agent** | 8 | ✅ | **2.867** | 4,146.48 | 2.682 | 0.000085 | 0.568 | 0 | 75.0 |
| AutoTuner | 0 | unavailable | | | | | | | |

The agent stopped after 8 runs because the clock search converged (2.837 ns failed by −0.059 ns, 2.867 ns passed).

### `aes`

| Method | Runs | Signoff | Clock (ns) | Area (µm²) | Power (mW) | Setup WNS (ns) | Hold WNS (ns) | DRC | Runtime (s) |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 1 | ❌ | 3.600 | 130,617 | 572.9 | −0.081 | 0.483 | 0 | 2,046 |
| Random | 10 | ✅ | 6.261 | 92,547.5 | 237.9 | 0.611 | 0.517 | 0 | 1,491 |
| **Agent** | 10 | ✅ | **4.822** | 101,032 | 329.3 | 0.017 | 0.480 | 0 | 2,460 |
| AutoTuner | 0 | unavailable | | | | | | | |

The agent used its full budget. Three runs signed off and two hit the flow timeout.

### `ibex`

| Method | Runs | Signoff | Clock (ns) | Area (µm²) | Power (mW) | Setup WNS (ns) | Hold WNS (ns) | DRC | Runtime (s) |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 1 | ❌ | 8.0 (SDC) | 172,822 | 65.50 | −0.551 | 0.421 | 0 | 3,080 |
| Random | 10 | ✅ | 10.531 | 150,786 | 43.52 | 0.099 | 0.317 | 0 | 1,257 |
| **Agent** | 1 | ✅ | **9.000** | 162,093 | 56.43 | 0.017 | 0.420 | 0 | 6,945 |
| AutoTuner | 0 | error | | | | | | | |

The agent's first proposal was the **floor of the allowed clock range** (9.0 ns). The design SDC's 8.0 ns lies below the autotuner sweep, so the agent starts at the range minimum. That run signed off, the bounds collapsed to [9.0, 9.0], and the search stopped as converged. AutoTuner launched on `ibex`, but Ray could not import HyperOpt before the first sample.

## Leaderboard

| Rank | Design | Method | Clock (ns) | Setup WNS | Hold WNS | DRC | Area (µm²) | Power (mW) |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | gcd | **Agent** | **2.867** | 0.000085 | 0.568 | 0 | 4,146.48 | 2.682 |
| 2 | gcd | Random | 4.113 | 0.476 | 0.558 | 0 | 3,361.97 | 1.570 |
| 1 | aes | **Agent** | **4.822** | 0.017 | 0.480 | 0 | 101,032 | 329.3 |
| 2 | aes | Random | 6.261 | 0.611 | 0.517 | 0 | 92,547.5 | 237.9 |
| 1 | ibex | **Agent** | **9.000** | 0.017 | 0.420 | 0 | 162,093 | 56.43 |
| 2 | ibex | Random | 10.531 | 0.099 | 0.317 | 0 | 150,786 | 43.52 |

Default ORFS does not appear because it never signed off. AutoTuner has no scored trials.

## Signoff rate

| Design | Method | Scored runs | Finished (`ok`) | Signoff | Rate |
| --- | --- | ---: | ---: | ---: | ---: |
| gcd | Default | 1 | 1 | 0 | 0% |
| gcd | Random | 10 | 6 | 4 | 40% |
| gcd | Agent | 8 | 8 | 3 | 38% |
| aes | Default | 1 | 1 | 0 | 0% |
| aes | Random | 10 | 2 | 1 | 10% |
| aes | Agent | 10 | 8 | 3 | 30% |
| ibex | Default | 1 | 1 | 0 | 0% |
| ibex | Random | 10 | 8 | 6 | 60% |
| ibex | Agent | 1 | 1 | 1 | 100% (n = 1) |
| **All** | Default | 3 | 3 | 0 | 0% |
| **All** | Random | 30 | 16 | 11 | 36.7% |
| **All** | Agent | 19 | 17 | 7 | 36.8% |

![Signoff rate](plots/success_rate_comparison.png)

## QoR trade-off

Agent best pass relative to random search's best pass:

| Design | Clock | Area | Power | Runtime |
| --- | ---: | ---: | ---: | ---: |
| gcd | −30.3% | +23.3% | +70.8% | 1.47× |
| aes | −23.0% | +9.2% | +38.4% | 1.65× |
| ibex | −14.5% | +7.5% | +29.7% | 5.53× |

Agent best pass relative to the (failing) default run:

| Design | Area | Power |
| --- | ---: | ---: |
| gcd | −23.4% | −72.8% |
| aes | −22.7% | −42.5% |
| ibex | −6.2% | −13.8% |

Hold slack stays positive on every best result, and DRC is 0 on every finished flow in the study, including the failing defaults. The cost of the tighter agent clock shows up as area and power, not DRC.

<table>
  <tr>
    <td><img src="plots/area_comparison.png" alt="Area"></td>
    <td><img src="plots/power_comparison.png" alt="Power"></td>
  </tr>
  <tr>
    <td><img src="plots/setup_wns_comparison.png" alt="Setup WNS"></td>
    <td><img src="plots/hold_wns_comparison.png" alt="Hold WNS"></td>
  </tr>
</table>

## Runtime

| Design | Default (s) | Random best pass (s) | Agent best pass (s) | Agent ÷ random | Mean scored run: random | Mean scored run: agent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gcd | 118.4 | 51.0 | 75.0 | 1.47× | 51 s | 76 s |
| aes | 2,046 | 1,491 | 2,460 | 1.65× | 11 min (9 runs with a runtime) | 70 min |
| ibex | 3,080 | 1,257 | 6,945 | 5.53× | 25 min | 116 min (1 run) |

The agent is slower than random on every design. Most of the extra `aes` and `ibex` time is detailed routing at the tighter clocks. The `aes` agent mean includes two timed-out runs (8,032 s and 9,933 s) and a 105-minute passing run at 4.875 ns. The scored runs add up to about **21.2 hours** of flow wall-clock.

![Runtime](plots/runtime_comparison.png)

## How each method searched

![Search trajectory](plots/search_trajectory.png)

- **Agent, `gcd`:** 1.1 ✗ → 3.05 ✓ → 2.075 ✗ → 2.562 ✗ → 2.806 ✗ → 2.928 ✓ → **2.867 ✓** → 2.837 ✗ → converged.
- **Agent, `aes`:** 3.6 ✗ → 5.3 ✓ → 4.45 ✗ → 4.875 ✓ → 4.662 ✗ → 4.768 timeout → **4.822 ✓** → 4.742 ✗ → 4.782 timeout → 4.832 ✗ → budget spent.
- **Agent, `ibex`:** **9.0 ✓**, at the range floor → converged.
- **Random:** samples spread across each full range. Most failures were placement density and detailed placement errors caused by aggressive utilization or density combinations, not clock.

Note the `aes` run at **4.832 ns failed (−0.0056 ns)** while 4.822 ns passed. Timing is not perfectly monotonic in clock period near the boundary, because placement and routing change with the constraint. That last run was also wasted search. After the timeout at 4.782 ns the bisection midpoint repeated the last clock, so the offline advisor stepped up by its 0.05 ns minimum. That step is clamped to the allowed range, not to the current bracket [4.742, 4.822], so it landed above an existing pass.

## Failure analysis

| Class | Count | Runs |
| --- | ---: | --- |
| Placement density above 1.0 (FLW-0024) | 5 | gcd random 5, 10 · aes random 2, 8 · ibex random 2 |
| Detailed placement check failed (DPL-0033) | 5 | gcd random 7, 8 · aes random 6, 9 · ibex random 7 |
| Global routing congestion (GRT-0116) | 2 | aes random 4, 5 |
| Other ORFS error (make error 2 in detailed placement) | 1 | aes random 7 |
| Flow timeout | 2 | aes agent 6 (8,032 s), 9 (9,933 s) |
| Unscored interruption (process exited, attempt continued in a new flow) | 6 | aes random 3, 9, 10 · aes agent search steps 3, 5 · ibex default |

Finished runs that missed timing, with DRC 0 and a setup WNS miss: gcd random 2 and 9, five gcd agent runs, the `aes` and `ibex` default runs, aes random 10, five `aes` agent runs, and ibex random 3 and 6.

`aes` random 3 has no failure class of its own. Its only attempt stopped during floorplan `repair_timing` when the benchmark process exited, and the campaign scores it as a flow error with no runtime. It is the first entry in the unscored list.

**Pattern.** Random search fails on *feasibility* (density, placement, congestion) because it moves every knob at once. The agent fails on *timing near the boundary*, which is the expected cost of bisecting toward the tightest clock. Its expensive `aes` failures were the two timeouts.

## Key findings

1. **Signoff vs default:** 3/3 vs 0/3. Default fails setup by −1.460, −0.081 and −0.551 ns. The agent's passing clocks are slower than the default targets, so the gain over default is a legal signoff, not a faster clock.
2. **Passing clock vs random:** 30.3%, 23.0% and 14.5% tighter.
3. **Random wins secondary PPA:** less area, less power and less runtime, at its looser clocks.
4. **Signoff rate:** about equal pooled (36.8% vs 36.7%), better on `aes` (30% vs 10%), slightly worse on `gcd` (38% vs 40%). `ibex` is one run.
5. **AutoTuner:** no scored result in this study.

## Limitations

- **One seed, one platform, budget 10.** Random and agent sequences were not repeated, so the 14.5–30.3% gains are single-sample results.
- **Offline advisor only.** No chat model was benchmarked.
- **The agent searched one dimension.** It moved only `_SDC_CLK_PERIOD`. The DRC-triggered utilization change never fired. Random search moved every knob.
- **`ibex` agent = 1 run, at the range floor.** Its 100% rate is not a 10-trial rate, and 9.0 ns is the lowest clock the allowlist permits for `ibex`.
- **Interruptions.** Two `aes` agent attempts and one `ibex` default attempt were paused and lost. They are unscored, and some `aes` work was repeated.
- **`gcd` failure text.** The campaign JSON stores only `ORFS exited with status 2` for four `gcd` random failures. The classes above come from their `stdout.log`.
- **Units.** Area and power are in ORFS metadata units (µm², W shown as mW) and are compared only within a design.

## Reproducing the figures

```bash
python scripts/make_release_plots.py results/final_benchmark_results.json plots/
python -m benchmarks.compare_results results/benchmark_campaign/gcd_sky130hd_default_base.json \
       results/benchmark_campaign/gcd_sky130hd_random_b10.json results/benchmark_campaign/gcd_sky130hd_agent_b10.json
```

Re-running the flows needs the same ORFS checkout and toolchain. Expect run-to-run differences from tool versions and host load.

## Appendix: every scored trial

`#` is the trial index within its method. Clock is the requested `_SDC_CLK_PERIOD`. `–` means the value was not produced because the flow did not finish.

#### `gcd`

| Method | # | Clock (ns) | Outcome | Setup WNS (ns) | Hold WNS (ns) | DRC | Area (µm²) | Power (mW) | Runtime (s) |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 1 | 1.100 | timing miss | -1.460 | +0.532 | 0 | 5,412.69 | 9.850 | 118 |
| random | 1 | 4.113 | ✅ signoff | +0.476 | +0.558 | 0 | 3,361.97 | 1.570 | 51 |
| random | 2 | 1.919 | timing miss | -0.642 | +0.550 | 0 | 4,977.27 | 5.149 | 76 |
| random | 3 | 4.744 | ✅ signoff | +0.810 | +0.558 | 0 | 3,504.61 | 1.462 | 51 |
| random | 4 | 4.745 | ✅ signoff | +0.915 | +0.576 | 0 | 3,508.36 | 1.481 | 79 |
| random | 5 | 2.548 | flow error | – | – | – | – | – | 14 |
| random | 6 | 4.561 | ✅ signoff | +0.948 | +0.569 | 0 | 3,356.97 | 1.371 | 61 |
| random | 7 | 4.384 | flow error | – | – | – | – | – | 69 |
| random | 8 | 4.507 | flow error | – | – | – | – | – | 23 |
| random | 9 | 2.356 | timing miss | -0.578 | +0.599 | 0 | 5,250.04 | 4.611 | 73 |
| random | 10 | 3.518 | flow error | – | – | – | – | – | 10 |
| agent | 1 | 1.100 | timing miss | -1.460 | +0.532 | 0 | 5,412.69 | 9.850 | 124 |
| agent | 2 | 3.050 | ✅ signoff | +0.029 | +0.577 | 0 | 3,862.45 | 2.401 | 64 |
| agent | 3 | 2.075 | timing miss | -0.433 | +0.578 | 0 | 4,628.19 | 4.122 | 68 |
| agent | 4 | 2.562 | timing miss | -0.050 | +0.570 | 0 | 4,616.93 | 3.387 | 77 |
| agent | 5 | 2.806 | timing miss | -0.013 | +0.564 | 0 | 4,359.18 | 2.936 | 62 |
| agent | 6 | 2.928 | ✅ signoff | +0.061 | +0.559 | 0 | 4,186.52 | 2.662 | 62 |
| agent | 7 | 2.867 | ✅ signoff | +0.000085 | +0.568 | 0 | 4,146.48 | 2.682 | 75 |
| agent | 8 | 2.837 | timing miss | -0.059 | +0.573 | 0 | 4,305.38 | 2.842 | 73 |

#### `aes`

| Method | # | Clock (ns) | Outcome | Setup WNS (ns) | Hold WNS (ns) | DRC | Area (µm²) | Power (mW) | Runtime (s) |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 1 | 3.600 | timing miss | -0.081 | +0.483 | 0 | 130,617.00 | 572.873 | 2,046 |
| random | 1 | 6.261 | ✅ signoff | +0.611 | +0.517 | 0 | 92,547.50 | 237.907 | 1,491 |
| random | 2 | 6.185 | flow error | – | – | – | – | – | 84 |
| random | 3 | 3.607 | flow error | – | – | – | – | – | – |
| random | 4 | 6.040 | flow error | – | – | – | – | – | 194 |
| random | 5 | 4.266 | flow error | – | – | – | – | – | 182 |
| random | 6 | 5.703 | flow error | – | – | – | – | – | 652 |
| random | 7 | 6.885 | flow error | – | – | – | – | – | 1,214 |
| random | 8 | 6.487 | flow error | – | – | – | – | – | 62 |
| random | 9 | 5.421 | flow error | – | – | – | – | – | 355 |
| random | 10 | 4.876 | timing miss | -0.386 | +0.505 | 0 | 99,839.50 | 344.963 | 1,673 |
| agent | 1 | 3.600 | timing miss | -0.081 | +0.483 | 0 | 130,617.00 | 572.873 | 1,960 |
| agent | 2 | 5.300 | ✅ signoff | +0.018 | +0.476 | 0 | 98,121.60 | 291.916 | 2,281 |
| agent | 3 | 4.450 | timing miss | -0.029 | +0.506 | 0 | 105,055.00 | 369.274 | 1,910 |
| agent | 4 | 4.875 | ✅ signoff | +0.019 | +0.455 | 0 | 101,346.00 | 327.020 | 6,291 |
| agent | 5 | 4.662 | timing miss | -0.048 | +0.475 | 0 | 102,686.00 | 347.504 | 2,210 |
| agent | 6 | 4.768 | timeout | -0.114 | +0.471 | 0 | 103,382.00 | 342.891 | 8,032 |
| agent | 7 | 4.822 | ✅ signoff | +0.017 | +0.480 | 0 | 101,032.00 | 329.286 | 2,460 |
| agent | 8 | 4.742 | timing miss | -0.055 | +0.522 | 0 | 103,050.00 | 343.013 | 2,579 |
| agent | 9 | 4.782 | timeout | -0.082 | +0.459 | 0 | 102,498.00 | 337.387 | 9,933 |
| agent | 10 | 4.832 | timing miss | -0.006 | +0.508 | 0 | 100,936.00 | 327.552 | 4,555 |

#### `ibex`

| Method | # | Clock (ns) | Outcome | Setup WNS (ns) | Hold WNS (ns) | DRC | Area (µm²) | Power (mW) | Runtime (s) |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 1 | 8.0 (SDC) | timing miss | -0.551 | +0.421 | 0 | 172,822.00 | 65.505 | 3,080 |
| random | 1 | 14.521 | ✅ signoff | +1.353 | +0.375 | 0 | 146,409.00 | 29.383 | 1,380 |
| random | 2 | 14.370 | flow error | – | – | – | – | – | 133 |
| random | 3 | 9.214 | timing miss | -0.075 | +0.449 | 0 | 169,186.00 | 56.798 | 1,152 |
| random | 4 | 14.081 | ✅ signoff | +0.133 | +0.444 | 0 | 147,956.00 | 31.800 | 1,899 |
| random | 5 | 10.531 | ✅ signoff | +0.099 | +0.317 | 0 | 150,786.00 | 43.523 | 1,257 |
| random | 6 | 13.405 | timing miss | -0.461 | +0.448 | 0 | 147,903.00 | 35.043 | 2,027 |
| random | 7 | 15.770 | flow error | – | – | – | – | – | 621 |
| random | 8 | 14.973 | ✅ signoff | +1.235 | +0.441 | 0 | 143,624.00 | 27.638 | 3,720 |
| random | 9 | 12.842 | ✅ signoff | +0.088 | +0.455 | 0 | 148,739.00 | 36.155 | 1,282 |
| random | 10 | 11.753 | ✅ signoff | +0.159 | +0.416 | 0 | 151,708.00 | 40.461 | 1,434 |
| agent | 1 | 9.000 | ✅ signoff | +0.017 | +0.420 | 0 | 162,093.00 | 56.433 | 6,945 |

Unscored interruptions (not counted above): aes random 3, 9, 10 · aes agent search steps 3, 5 · ibex default 1. Each continued in a new flow variant.
