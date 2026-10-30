# AES leaderboard

Success means the flow finished with DRC = 0, setup WNS >= 0, and hold WNS >= 0.

Smallest clock period with DRC = 0, setup WNS >= 0, and hold WNS >= 0.

aes / sky130hd / budget 10
  default: 1 runs, signoff no, clock 3.6, setup -0.0805747, hold 0.483049, DRC 0.0, area 130617.0, power 0.572873, runtime 2046.323
  random: 10 runs, signoff yes, clock 6.260532, setup 0.610598, hold 0.517489, DRC 0.0, area 92547.5, power 0.237907, runtime 1490.845
  autotuner: unavailable (OpenROAD AutoTuner executable was not found. Set ORFS_AUTOTUNER or install openroad_autotuner. No AutoTuner metrics were recorded.)
  agent: 10 runs, signoff yes, clock 4.822, setup 0.0166596, hold 0.479924, DRC 0.0, area 101032.0, power 0.329286, runtime 2459.98
  agent has the smallest passing clock, 4.822 ns. Unavailable methods are autotuner.

## Success rate

| Design | Method | Runs | Finished | Signoff | Success rate | Area | Power | Setup WNS | Hold WNS | DRC | Runtime (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aes | default | 1 | 1 | 0 | 0% | 130617 | 0.572873 | -0.0805747 | 0.483049 | 0 | 2046.32 |
| aes | random | 10 | 2 | 1 | 10% | 92547.5 | 0.237907 | 0.610598 | 0.517489 | 0 | 1490.85 |
| aes | agent | 10 | 8 | 3 | 30% | 101032 | 0.329286 | 0.0166596 | 0.479924 | 0 | 2459.98 |

## Failure analysis

| Failure class | Count | Runs |
| --- | --- | --- |
| Placement density above 1.0 | 2 | aes random trial 2, aes random trial 8 |
| Benchmark process interrupted | 4 | aes random trial 3, aes random trial 10, aes agent trial 3, aes agent trial 5 |
| Global routing congestion | 2 | aes random trial 4, aes random trial 5 |
| Detailed placement check failed | 3 | aes random trial 6, aes random trial 9, aes random trial 9 |
| Other flow error | 1 | aes random trial 7 |
