# Benchmark summary

Smallest clock period with DRC = 0, setup WNS >= 0, and hold WNS >= 0.

Budget 10. Seed 1. Platform sky130hd. gcd was not rerun.

## Leaderboards

Smallest clock period with DRC = 0, setup WNS >= 0, and hold WNS >= 0.

gcd / sky130hd / budget 10
  default: 1 runs, signoff no, clock 1.1, setup -1.45954, hold 0.532397, DRC 0.0, area 5412.69, power 0.00985037, runtime 118.364
  random: 10 runs, signoff yes, clock 4.112638, setup 0.476453, hold 0.557782, DRC 0.0, area 3361.97, power 0.00157044, runtime 51.032
  autotuner: unavailable (OpenROAD AutoTuner executable was not found. Set ORFS_AUTOTUNER or install openroad_autotuner. No AutoTuner metrics were recorded.)
  agent: 8 runs, signoff yes, clock 2.867, setup 8.4821e-05, hold 0.568337, DRC 0.0, area 4146.48, power 0.00268209, runtime 74.979
  agent has the smallest passing clock, 2.867 ns. Unavailable methods are autotuner.

aes / sky130hd / budget 10
  default: 1 runs, signoff no, clock 3.6, setup -0.0805747, hold 0.483049, DRC 0.0, area 130617.0, power 0.572873, runtime 2046.323
  random: 10 runs, signoff yes, clock 6.260532, setup 0.610598, hold 0.517489, DRC 0.0, area 92547.5, power 0.237907, runtime 1490.845
  autotuner: unavailable (OpenROAD AutoTuner executable was not found. Set ORFS_AUTOTUNER or install openroad_autotuner. No AutoTuner metrics were recorded.)
  agent: 10 runs, signoff yes, clock 4.822, setup 0.0166596, hold 0.479924, DRC 0.0, area 101032.0, power 0.329286, runtime 2459.98
  agent has the smallest passing clock, 4.822 ns. Unavailable methods are autotuner.

ibex / sky130hd / budget 10
  default: 1 runs, signoff no, clock None, setup -0.551246, hold 0.420976, DRC 0.0, area 172822.0, power 0.0655049, runtime 3080.309
  random: 10 runs, signoff yes, clock 10.531467, setup 0.0987077, hold 0.316812, DRC 0.0, area 150786.0, power 0.0435235, runtime 1256.824
  autotuner: error (algorithm(
                  ^^^^^^^^^^^^^^
  File "/home/administrator/OpenROAD-flow-scripts/tools/AutoTuner/src/autotuner/distributed.py", line 488, in set_algorithm
    algorithm = HyperOptSearch(
                ^^^^^^^^^^^^^^^
  File "/home/administrator/OpenROAD-flow-scripts/tools/AutoTuner/autotuner_env/lib/python3.12/site-packages/ray/tune/search/hyperopt/hyperopt_search.py", line 163, in __init__
    hpo is not None
AssertionError: HyperOpt must be installed! Run `pip install hyperopt`.)
  agent: 1 runs, signoff yes, clock 9.0, setup 0.0165974, hold 0.420391, DRC 0.0, area 162093.0, power 0.0564333, runtime 6945.369
  agent has the smallest passing clock, 9.0 ns. Unavailable methods are autotuner.

## Success rate

| Design | Method | Runs | Finished | Signoff | Success rate | Area | Power | Setup WNS | Hold WNS | DRC | Runtime (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gcd | default | 1 | 1 | 0 | 0% | 5412.69 | 0.00985037 | -1.45954 | 0.532397 | 0 | 118.364 |
| gcd | random | 10 | 6 | 4 | 40% | 3361.97 | 0.00157044 | 0.476453 | 0.557782 | 0 | 51.032 |
| gcd | agent | 8 | 8 | 3 | 38% | 4146.48 | 0.00268209 | 8.4821e-05 | 0.568337 | 0 | 74.979 |
| aes | default | 1 | 1 | 0 | 0% | 130617 | 0.572873 | -0.0805747 | 0.483049 | 0 | 2046.32 |
| aes | random | 10 | 2 | 1 | 10% | 92547.5 | 0.237907 | 0.610598 | 0.517489 | 0 | 1490.85 |
| aes | agent | 10 | 8 | 3 | 30% | 101032 | 0.329286 | 0.0166596 | 0.479924 | 0 | 2459.98 |
| ibex | default | 1 | 1 | 0 | 0% | 172822 | 0.0655049 | -0.551246 | 0.420976 | 0 | 3080.31 |
| ibex | random | 10 | 8 | 6 | 60% | 150786 | 0.0435235 | 0.0987077 | 0.316812 | 0 | 1256.82 |
| ibex | agent | 1 | 1 | 1 | 100% | 162093 | 0.0564333 | 0.0165974 | 0.420391 | 0 | 6945.37 |

## Failed runs

- aes random trial 2: [ERROR FLW-0024] Place density exceeds 1.0 (current PLACE_DENSITY_LB_ADDON =  0.121488). Please check if the value of  PLACE_DENSITY_LB_ADDON is between 0 and 0.99.
- aes random trial 3: The benchmark process exited during floorplan repair_timing. Synthesis had finished. Placement, CTS, routing, and GDS were not produced.
- aes random trial 4: [ERROR GRT-0116] Global routing finished with congestion. Check the congestion regions in the DRC Viewer.
- aes random trial 5: [ERROR GRT-0116] Global routing finished with congestion. Check the congestion regions in the DRC Viewer.
- aes random trial 6: [ERROR DPL-0033] detailed placement checks failed during check placement.
- aes random trial 7: make: *** [Makefile:525: results/sky130hd/aes/p146290ebcd29e43a7a6acd1bdca7ed173/3_5_place_dp.odb] Error 2
- aes random trial 8: [ERROR FLW-0024] Place density exceeds 1.0 (current PLACE_DENSITY_LB_ADDON =  0.078671). Please check if the value of  PLACE_DENSITY_LB_ADDON is between 0 and 0.99.
- aes random trial 9: The benchmark process exited during detailed placement. This attempt was not scored. The same sample continued in a new flow.
- aes random trial 9: [ERROR DPL-0033] detailed placement checks failed during check placement.
- aes random trial 10: The benchmark process exited during detailed routing. This attempt was not scored. The same sample continued in a new flow.
- aes agent trial 3: The paused benchmark process exited during detailed routing. This attempt was not scored. The agent session continued in a new run.
- aes agent trial 5: The paused benchmark process exited during detailed routing. This attempt was not scored. The same clock search continued in a new flow.
- ibex default trial 1: The paused benchmark process exited during detailed routing. This attempt was not scored. The default flow continued in a new run.
- ibex random trial 2: [ERROR FLW-0024] Place density exceeds 1.0 (current PLACE_DENSITY_LB_ADDON =  0.121488). Please check if the value of  PLACE_DENSITY_LB_ADDON is between 0 and 0.99.
- ibex random trial 7: [ERROR DPL-0033] detailed placement checks failed during check placement.

## Failure analysis

| Failure class | Count | Runs |
| --- | --- | --- |
| Placement density above 1.0 | 3 | aes random trial 2, aes random trial 8, ibex random trial 2 |
| Benchmark process interrupted | 5 | aes random trial 3, aes random trial 10, aes agent trial 3, aes agent trial 5, ibex default trial 1 |
| Global routing congestion | 2 | aes random trial 4, aes random trial 5 |
| Detailed placement check failed | 4 | aes random trial 6, aes random trial 9, aes random trial 9, ibex random trial 7 |
| Other flow error | 1 | aes random trial 7 |

Recovered aes work: default and random trial 1 are the original completed flows. Failed and interrupted random trials stay in the record and were not rerun.
