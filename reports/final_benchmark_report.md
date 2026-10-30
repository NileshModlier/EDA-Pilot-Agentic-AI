# P3.4 Final Benchmark Report

Platform `sky130hd`. Budget 10. Seed 1. No new flows were run for this package. Figures are taken from the saved gcd campaign files and `results/campaign_checkpoint.json`.

The objective is the smallest clock period that finishes with DRC count = 0, setup WNS >= 0, and hold WNS >= 0. Area, power, and runtime are reported with that result. They do not override a tighter passing clock.

## 1. Executive Summary

EDA Pilot outperformed Default ORFS on signoff for every design. The default flow missed setup on gcd, AES, and IBEX. The agent produced a passing implementation of each design.

EDA Pilot outperformed Random Search on the primary objective for every design. Its best passing clocks are:

| Design | Agent | Random | Tighter than random |
| --- | ---: | ---: | ---: |
| gcd | 2.867 ns | 4.113 ns | 30.3% |
| aes | 4.822 ns | 6.261 ns | 23.0% |
| ibex | 9.000 ns | 10.531 ns | 14.5% |

Those passing agent results are larger and higher power than the best random results, and they take longer. Signoff rate is higher for the agent on AES (30% vs 10%). On gcd it is slightly lower (3/8 vs 4/10). On IBEX the agent signed off its only run, while random signed off 6 of 10. Pooled across designs, the signoff rate is 7/19 for the agent and 11/30 for random.

AutoTuner produced no scored trials. It was unavailable for gcd and AES. The IBEX invocation exited before the first sample because Ray could not load HyperOpt.

## 2. Methodology

Four methods were scheduled. Each search method used budget 10 and seed 1.

- **Default ORFS** runs the design once with no parameter overrides.
- **Random Search** draws 10 executable parameter sets from the allowlist with seed 1.
- **EDA Pilot Agent** is the existing LangGraph session. It proposes a clock, runs the flow, and may stop when the passing-clock gap is under 0.05 ns or when the budget is exhausted.
- **AutoTuner** is OpenROAD AutoTuner with the same sample budget. A missing executable is recorded as unavailable. A launch that exits is recorded as an error. Neither case is filled with metrics from another method.

A run signs off only when the flow status is `ok`, DRC count is 0, setup WNS is at least 0, and hold WNS is at least 0. Runtime in the tables is the flow process wall clock. The metadata runtime field is a clock string and is not used.

## 3. Experimental Setup

| Item | Value |
| --- | --- |
| Platform | sky130hd |
| Designs | gcd, aes, ibex |
| Budget | 10 trials for random, agent, and AutoTuner |
| Seed | 1 |
| Flow | OpenROAD Flow Scripts through WSL Ubuntu |
| Tools | Yosys, OpenROAD, KLayout, GNU Make |
| Flow timeout | 7200 s on the resumed AES and IBEX campaign |
| Primary key | smallest passing clock |
| Recorded metrics | area, power, setup WNS, hold WNS, DRC count, runtime |

gcd was collected in the first campaign directory and was not rerun. AES and IBEX were collected by the checkpointed resume. Interrupted attempts that were not scored are listed separately and are not counted as the scored trial that replaced them.

## 4. Design Descriptions

**gcd** is the small arithmetic block in the sky130hd catalog. The default clock period is 1.1 ns. It is the shortest flow of the three.

**aes** is the AES cipher core. The default clock period is 3.6 ns. Detailed routing dominates a successful run, and several random samples fail in placement or global routing.

**ibex** is the Ibex RISC-V core, the largest of the three. The design SDC sets the clock period to 8.0 ns. The default result record stores no clock override, so its clock field is empty. The measured setup WNS at that default configuration is -0.551 ns.

## 5. Benchmark Results

Each row is the best signoff result for that method. Default has no signoff, so the row is the single default run.

### gcd

| Method | Runs | Signoff | Clock (ns) | Area | Power (W) | Setup WNS | Hold WNS | DRC | Runtime (s) |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 1 | no | 1.100 | 5412.69 | 0.009850 | -1.460 | 0.532 | 0 | 118.4 |
| Random | 10 | yes | 4.113 | 3361.97 | 0.001570 | 0.476 | 0.558 | 0 | 51.0 |
| Agent | 8 | yes | 2.867 | 4146.48 | 0.002682 | 0.000085 | 0.568 | 0 | 75.0 |
| AutoTuner | 0 | unavailable |  |  |  |  |  |  |  |

The agent stopped after 8 runs because the clock search converged.

### aes

| Method | Runs | Signoff | Clock (ns) | Area | Power (W) | Setup WNS | Hold WNS | DRC | Runtime (s) |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 1 | no | 3.600 | 130617 | 0.5729 | -0.081 | 0.483 | 0 | 2046 |
| Random | 10 | yes | 6.261 | 92547.5 | 0.2379 | 0.611 | 0.517 | 0 | 1491 |
| Agent | 10 | yes | 4.822 | 101032 | 0.3293 | 0.017 | 0.480 | 0 | 2460 |
| AutoTuner | 0 | unavailable |  |  |  |  |  |  |  |

The agent used the full budget of 10. Two of those runs hit the flow timeout and still have partial metrics. Three runs signed off.

### ibex

| Method | Runs | Signoff | Clock (ns) | Area | Power (W) | Setup WNS | Hold WNS | DRC | Runtime (s) |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 1 | no | 8.0 SDC | 172822 | 0.06550 | -0.551 | 0.421 | 0 | 3080 |
| Random | 10 | yes | 10.531 | 150786 | 0.04352 | 0.099 | 0.317 | 0 | 1257 |
| Agent | 1 | yes | 9.000 | 162093 | 0.05643 | 0.017 | 0.420 | 0 | 6945 |
| AutoTuner | 0 | error |  |  |  |  |  |  |  |

The agent stopped after the first run because that 9.0 ns result signed off and the search treated the clock gap as converged. The default row uses the SDC period because the result record has no clock override.

Every scored trial, including failures, is in `results/final_benchmark_results.json`.

## 6. Leaderboards

Smallest passing clock. Default does not appear because it never signed off.

| Rank | Design | Method | Clock (ns) | Setup WNS | Hold WNS | DRC | Area | Power (W) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | gcd | Agent | 2.867 | 0.000085 | 0.568 | 0 | 4146.48 | 0.002682 |
| 2 | gcd | Random | 4.113 | 0.476 | 0.558 | 0 | 3361.97 | 0.001570 |
| 1 | aes | Agent | 4.822 | 0.017 | 0.480 | 0 | 101032 | 0.3293 |
| 2 | aes | Random | 6.261 | 0.611 | 0.517 | 0 | 92547.5 | 0.2379 |
| 1 | ibex | Agent | 9.000 | 0.017 | 0.420 | 0 | 162093 | 0.05643 |
| 2 | ibex | Random | 10.531 | 0.099 | 0.317 | 0 | 150786 | 0.04352 |

See `plots/leaderboard_summary.png`.

## 7. Success-Rate Analysis

Signoff rate is signoff count divided by scored runs. A finished flow that misses setup or hold is not a success.

| Design | Method | Scored runs | Finished (`ok`) | Signoff | Signoff rate |
| --- | --- | ---: | ---: | ---: | ---: |
| gcd | Default | 1 | 1 | 0 | 0% |
| gcd | Random | 10 | 6 | 4 | 40% |
| gcd | Agent | 8 | 8 | 3 | 38% |
| aes | Default | 1 | 1 | 0 | 0% |
| aes | Random | 10 | 2 | 1 | 10% |
| aes | Agent | 10 | 8 | 3 | 30% |
| ibex | Default | 1 | 1 | 0 | 0% |
| ibex | Random | 10 | 8 | 6 | 60% |
| ibex | Agent | 1 | 1 | 1 | 100% |

Pooled signoff rate is 0/3 for default, 11/30 (36.7%) for random, and 7/19 (36.8%) for the agent. The agent rate on IBEX is one run. The AES agent rate is the clearest gain: 3 signoffs in 10 runs against 1 in 10 for random.

See `plots/success_rate_comparison.png`.

## 8. Failure Analysis

Scored flow failures and the separate unscored interruptions are both listed. An unscored interruption was continued later and is not a second scored trial.

| Class | Count | Runs |
| --- | ---: | --- |
| Placement density above 1.0 (FLW-0024) | 5 | gcd random 5 and 10; aes random 2 and 8; ibex random 2 |
| Detailed placement check failed (DPL-0033) | 5 | gcd random 7 and 8; aes random 6 and 9; ibex random 7 |
| Global routing congestion (GRT-0116) | 2 | aes random 4 and 5 |
| Other ORFS error | 1 | aes random 7, make error 2 during detailed placement |
| Flow timeout | 2 | aes agent 6 (8032 s) and 9 (9933 s) |
| Unscored interruption | 6 | aes random 3, 9, and 10; aes agent search steps 3 and 5; ibex default |

gcd random failures 5, 7, 8, and 10 are stored in the campaign file only as `ORFS exited with status 2`. The classes above come from the matching `stdout.log` lines in `results/p33_gcd_runs`. The other classes are the causes stored in the checkpoint.

Finished runs that missed timing, and therefore did not sign off, are gcd random 2 and 9, five gcd agent runs, the AES and IBEX default runs, AES random 10, five AES agent runs, and IBEX random 3 and 6. Their DRC count is 0. The miss is setup WNS.

Random failures cluster on density, detailed placement, and AES congestion. The agent failures are timing misses and two AES timeouts, plus two pauses that were not scored.

## 9. Runtime Analysis

Runtime below is the wall clock of the best passing run, or the only default run.

| Design | Default (s) | Random best pass (s) | Agent best pass (s) | Agent / random |
| --- | ---: | ---: | ---: | ---: |
| gcd | 118.4 | 51.0 | 75.0 | 1.47× |
| aes | 2046 | 1491 | 2460 | 1.65× |
| ibex | 3080 | 1257 | 6945 | 5.53× |

Mean wall clock of scored runs is about 51 s for gcd random and 76 s for the gcd agent. AES random averages about 11 minutes on the nine trials that recorded a runtime. The AES agent averages about 70 minutes, pulled up by the two timeouts and one 105-minute passing run. IBEX random averages about 25 minutes. The single IBEX agent run took 116 minutes.

The agent is slower than random on every design. Most of the extra AES and IBEX time is detailed routing at the tighter clocks. See `plots/runtime_comparison.png`.

## 10. QoR Analysis

QoR here is area, power, and slack at the best passing clock. Default is included as the non-signoff reference.

| Design | Method | Clock (ns) | Area | Power (W) | Setup WNS | Hold WNS | DRC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gcd | Default | 1.100 | 5412.69 | 0.009850 | -1.460 | 0.532 | 0 |
| gcd | Random | 4.113 | 3361.97 | 0.001570 | 0.476 | 0.558 | 0 |
| gcd | Agent | 2.867 | 4146.48 | 0.002682 | 0.000085 | 0.568 | 0 |
| aes | Default | 3.600 | 130617 | 0.5729 | -0.081 | 0.483 | 0 |
| aes | Random | 6.261 | 92547.5 | 0.2379 | 0.611 | 0.517 | 0 |
| aes | Agent | 4.822 | 101032 | 0.3293 | 0.017 | 0.480 | 0 |
| ibex | Default | 8.0 SDC | 172822 | 0.06550 | -0.551 | 0.421 | 0 |
| ibex | Random | 10.531 | 150786 | 0.04352 | 0.099 | 0.317 | 0 |
| ibex | Agent | 9.000 | 162093 | 0.05643 | 0.017 | 0.420 | 0 |

Relative to the best random signoff, the agent result is:

| Design | Area | Power | Setup slack |
| --- | ---: | ---: | --- |
| gcd | +23.3% | +70.8% | 0.000 ns, just closed |
| aes | +9.2% | +38.4% | 0.017 ns |
| ibex | +7.5% | +29.7% | 0.017 ns |

Hold slack stays positive for every best result. DRC is 0 on every finished flow in this set, including the default runs that miss setup. The QoR cost of the tighter agent clock is area and power, not DRC.

Plots: `plots/area_comparison.png`, `plots/power_comparison.png`, `plots/setup_wns_comparison.png`, `plots/hold_wns_comparison.png`.

## 11. Key Findings

1. EDA Pilot outperformed Default ORFS on signoff. Default setup WNS is -1.460 ns on gcd, -0.081 ns on AES, and -0.551 ns on IBEX. The agent signed off all three.
2. EDA Pilot outperformed Random Search on passing clock by 30.3% on gcd, 23.0% on AES, and 14.5% on IBEX.
3. The passing agent clocks are still slower than the default targets: 2.867 ns versus 1.1 ns on gcd, 4.822 ns versus 3.6 ns on AES, and 9.0 ns versus the 8.0 ns IBEX SDC. The gain versus default is signoff, not a faster clock.
4. Signoff rate improves clearly on AES (30% versus 10%). It does not improve on gcd (38% versus 40%). The IBEX agent rate is 1 of 1 run.
5. Random Search wins area, power, and runtime at its looser passing clocks.
6. AutoTuner added no QoR result.

## 12. Limitations

- One seed and one platform. The random and agent sequences are not repeated.
- The IBEX agent stopped after a single passing run, so its 100% signoff rate is not a 10-trial rate.
- Two AES agent runs and one IBEX default attempt were paused and lost. The lost attempts are unscored. The AES search was continued, so some of that work was repeated.
- gcd flow-error text is in the run logs. The campaign JSON stores only exit status 2 for those four trials.
- AutoTuner has no scores. gcd and AES never found the executable. IBEX found it and then failed inside Ray before a sample.
- Default IBEX clock is the SDC value of 8.0 ns. The trial record itself leaves clock empty.
- Area and power units are the ORFS metadata units. They are compared within a design only.

## 13. Future Work

- Repair the AutoTuner environment so HyperOpt is visible to Ray, then run the budget-10 sweep for gcd, AES, and IBEX. Do not copy scores from the other methods.
- Repeat random and agent at more seeds before treating the 23–30% clock gains as stable.
- Keep the IBEX agent from being summarized as a 100% method until it has a full budget or an explicit early-stop sample size.
- Add the stored ORFS error line to gcd failure records so later reports do not need the raw logs.

## Answer to the comparison questions

**Did EDA Pilot outperform Random Search?** Yes on the primary objective. The passing clock is 30.3% tighter on gcd, 23.0% tighter on AES, and 14.5% tighter on IBEX. It did not outperform random on area, power, or runtime. Signoff rate is better on AES, about the same overall (36.8% versus 36.7%), and slightly worse on gcd.

**Did EDA Pilot outperform Default ORFS?** Yes on signoff. Default signed off 0 of 3 designs. The agent signed off 3 of 3. The agent clocks are slower than the default targets because those targets miss setup. Versus the failing default runs, the agent also uses less area and less power on every design, at the cost of more runtime on AES and IBEX.
