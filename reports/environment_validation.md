# Benchmark environment validation

Checked: 2026-10-17

No ORFS finish run and no benchmark sweep was started.

| Dependency | Result | Detail |
| --- | --- | --- |
| ORFS_ROOT | FAIL | ORFS_ROOT is unset. Point it at an OpenROAD-flow-scripts checkout. |
| ORFS flow directory | FAIL | Set ORFS_ROOT or ORFS_FLOW_DIR to the flow directory that contains designs/. |
| gcd design files | FAIL | Flow directory is unavailable, so config.mk, constraint.sdc, and autotuner.json were not found. |
| list_params gcd | PASS | 10 parameters, 9 executable, source configs/allowed_parameters.json. |
| autotuner ranges gcd | FAIL | autotuner.json is not in the flow tree. The allowlist holds the upstream ranges until that file is present. |
| run_flow gcd | FAIL | validation error: ORFS is not configured. Set ORFS_ROOT to an OpenROAD-flow-scripts checkout. finish was not started. |
| aes design files | FAIL | Flow directory is unavailable, so config.mk, constraint.sdc, and autotuner.json were not found. |
| list_params aes | PASS | 9 parameters, 8 executable, source configs/allowed_parameters.json. |
| autotuner ranges aes | FAIL | autotuner.json is not in the flow tree. The allowlist holds the upstream ranges until that file is present. |
| run_flow aes | FAIL | validation error: ORFS is not configured. Set ORFS_ROOT to an OpenROAD-flow-scripts checkout. finish was not started. |
| ibex design files | FAIL | Flow directory is unavailable, so config.mk, constraint.sdc, and autotuner.json were not found. |
| list_params ibex | PASS | 9 parameters, 8 executable, source configs/allowed_parameters.json. |
| autotuner ranges ibex | FAIL | autotuner.json is not in the flow tree. The allowlist holds the upstream ranges until that file is present. |
| run_flow ibex | FAIL | validation error: ORFS is not configured. Set ORFS_ROOT to an OpenROAD-flow-scripts checkout. finish was not started. |
| AutoTuner detection | PASS | Searched ORFS_AUTOTUNER, PATH, the ORFS AutoTuner virtualenv, and the autotuner.distributed module. |
| AutoTuner installed | FAIL | AutoTuner is not installed. Install steps are in docs/autotuner_setup.md. |
| AutoTuner version | FAIL | No version command returned a version. Install steps are in docs/autotuner_setup.md. |
| AutoTuner executable | FAIL | No executable path was found. Install steps are in docs/autotuner_setup.md. |
| metadata generation | FAIL | The metrics parser accepts a METRICS2.1 sample. No metadata.json from ORFS is on disk, and no flow was started. |
| report parsing | PASS | read_tail returned the timing, DRC, and congestion sample. |
| benchmark framework | PASS | benchmark.py, run_random.py, run_autotuner.py, run_agent.py, and compare_results.py import. |

Summary: list_params is ready for gcd, aes, and ibex where those rows passed. Still failing: ORFS_ROOT, ORFS flow directory, gcd design files, autotuner ranges gcd, run_flow gcd, aes design files, autotuner ranges aes, run_flow aes, ibex design files, autotuner ranges ibex, run_flow ibex, AutoTuner installed, AutoTuner version, AutoTuner executable, metadata generation. Install the failing tools, then run this script again. AutoTuner setup is documented in docs/autotuner_setup.md.
