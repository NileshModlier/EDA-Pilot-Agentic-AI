# ORFS discovery

Checked: 2026-10-17

No ORFS finish run was started.

| Check | Result | Detail |
| --- | --- | --- |
| ORFS_ROOT environment variable | FAIL | ORFS_ROOT is unset in this Windows process. |
| ORFS checkout | PASS | \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts, commit ef421749a |
| flow/Makefile | PASS | \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow\Makefile |
| gcd directory | PASS | \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow\designs\sky130hd\gcd |
| gcd config.mk | PASS | 378 bytes |
| gcd constraint.sdc | PASS | 603 bytes |
| gcd autotuner.json | PASS | 1522 bytes |
| aes directory | PASS | \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow\designs\sky130hd\aes |
| aes config.mk | PASS | 693 bytes |
| aes constraint.sdc | PASS | 607 bytes |
| aes autotuner.json | PASS | 1393 bytes |
| ibex directory | PASS | \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow\designs\sky130hd\ibex |
| ibex config.mk | PASS | 811 bytes |
| ibex constraint.sdc | PASS | 611 bytes |
| ibex autotuner.json | PASS | 1394 bytes |
| GNU make in Ubuntu | PASS | /usr/bin/make |
| OpenROAD binary | FAIL | tools/OpenROAD/build/bin/openroad is not built. |

Summary: gcd, aes, and ibex design files passed. Still failing: ORFS_ROOT environment variable, OpenROAD binary. No finish run was started.
