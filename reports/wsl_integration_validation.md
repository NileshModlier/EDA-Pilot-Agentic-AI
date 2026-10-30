# WSL flow execution validation

Checked: 2026-10-18. Execution-path handling only. Agent logic and benchmark logic were not modified.

## Launch path before the bridge

`run_flow` built this argument list and started it with `shell=False`:

```
make -C \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow DESIGN_CONFIG=./designs/sky130hd/<design>/config.mk FLOW_VARIANT=p1<run_id> finish
```

The process working directory was the same UNC flow directory. Windows has no `make`, so `CreateProcess` raised `FileNotFoundError` (`WinError 2`).

## WSL checkout

| Check | Result |
| --- | --- |
| Distro | Ubuntu |
| Linux flow | `/home/administrator/OpenROAD-flow-scripts/flow` |
| `Makefile` inside that directory | PASS |
| `wsl.exe` | `C:\Windows\System32\wsl.EXE` |

## Bridge

When the launcher is GNU make and the flow path is `\\wsl$\<distro>\...`, `run_flow` now starts:

```
wsl.exe -d Ubuntu -- bash -lc "set -eu; cd '/home/administrator/OpenROAD-flow-scripts/flow'; . ../env.sh; exec make -C '/home/administrator/OpenROAD-flow-scripts/flow' DESIGN_CONFIG=./designs/sky130hd/<design>/config.mk FLOW_VARIANT=p1<run_id> finish"
```

`shell` stays off. The bash script is one argument built from the existing allowlisted make tokens. The Windows process starts in `C:\Windows`. Make runs in `/home/administrator/OpenROAD-flow-scripts/flow` after `env.sh` puts OpenROAD and Yosys on `PATH`. A local or Python make launcher is left unchanged.

## run_flow results

Each call was `run_flow(<design>, "sky130hd")`. Status `ok` means the process exit code was 0. Each run used a new `p1` variant and wrote `6_final.gds`.

| Design | Status | Exit | Runtime (s) | Variant | Final GDS | Result |
| --- | --- | --- | --- | --- | --- | --- |
| gcd | ok | 0 | 137.134 | `p19103edf9fb2c40a6815e08ec5cb46888` | 974,128 bytes | PASS |
| aes | ok | 0 | 2150.511 | `p1e81bd7a502424aa89224cc483e4cfc56` | 19,462,484 bytes | PASS |
| ibex | ok | 0 | 3443.707 | `p1cebb07063e0040daa141e0c09d0c60d5` | 22,120,568 bytes | PASS |

## Can P3.3 start?

YES.
