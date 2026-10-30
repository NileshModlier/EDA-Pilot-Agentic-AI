# Benchmark readiness

Checked: 2026-10-17. No finish run and no benchmark sweep was started.

| Item | Status | Detail |
| --- | --- | --- |
| ORFS_ROOT | PASS | Windows user variable `\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts`. Ubuntu login shell `/home/administrator/OpenROAD-flow-scripts`. gcd `config.mk` resolves in both. |
| OpenROAD binary | FAIL | `tools/OpenROAD/build/bin/openroad` and `tools/install/OpenROAD/bin/openroad` are absent. |
| gcd | PASS | `config.mk`, `constraint.sdc`, and `autotuner.json` are in the checkout. |
| aes | PASS | `config.mk`, `constraint.sdc`, and `autotuner.json` are in the checkout. |
| ibex | PASS | `config.mk`, `constraint.sdc`, and `autotuner.json` are in the checkout. |
| Metadata | FAIL | No `flow/reports/sky130hd/gcd/**/metadata.json`. The gcd flow was not started. |
| MCP tools | PASS | P1 server is present and was not changed. |
| Agent | PASS | P2 LangGraph agent is present and was not changed. |
| Benchmark framework | PASS | P3 harness is present and was not changed. |

## Can P3.3 start?

NO.

Blockers:

1. OpenROAD is not built, so `openroad -version` cannot run.
2. `cmake` and `swig` are missing on Ubuntu 26.04.
3. `sudo` needs an interactive password, so `sudo ./setup.sh` was not run.
4. This checkout's `etc/DependencyInstaller.sh` rejects Ubuntu 26.04. KLayout packages are listed for 20.04, 22.04, and 24.04 only.
5. gcd `metadata.json` does not exist.

Build steps for a supported Ubuntu or WSL distro are in `docs/openroad_build.md`. Environment variables are in `docs/orfs_environment.md`.
