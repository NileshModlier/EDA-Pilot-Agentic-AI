# OpenROAD smoke test

Checked: 2026-10-17

The OpenROAD binary is absent, so the version command and the gcd flow were not started.

| Check | Result | Detail |
| --- | --- | --- |
| openroad -version (build tree) | FAIL | /home/administrator/OpenROAD-flow-scripts/tools/OpenROAD/build/bin/openroad is not executable. -version was not run. |
| openroad -version (install tree) | FAIL | /home/administrator/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad is not executable. -version was not run. |
| gcd metadata.json | FAIL | No metadata.json under flow/reports/sky130hd/gcd. The gcd flow was not started. |

Summary: smoke test failed. Missing: openroad -version (build tree), openroad -version (install tree), gcd metadata.json.
