# AES validation

Checked: 2026-10-17. Platform `sky130hd`, flow variant `base`.

Command, from `/home/administrator/OpenROAD-flow-scripts/flow` after sourcing `env.sh`:

```
make DESIGN_CONFIG=./designs/sky130hd/aes/config.mk
```

Exit code: **0**. The completed stage files were already present, so Make reprinted the elapsed table and did not rebuild the flow. `make metadata-generate` for this design also exited 0.

| Stage | Check | Result |
| --- | --- | --- |
| Synthesis | `1_2_yosys.v` 1,463,236 bytes, `1_synth.odb` 8,535,595 bytes, `1_2_yosys.log` contains `End of script` | PASS |
| Floorplan | `2_floorplan.odb` 9,914,918 bytes | PASS |
| Placement | `3_place.odb` 11,917,205 bytes | PASS |
| CTS | `4_cts.odb` 12,024,084 bytes | PASS |
| Routing | `5_route.odb` 31,857,095 bytes | PASS |
| Final GDS | `6_final.gds` 19,462,484 bytes, `6_1_merged.gds` 19,462,484 bytes | PASS |

Elapsed total: **2623 s**. Peak memory: **1297 MB**. Route stage `5_2_route` elapsed **2308 s**.

Artifacts: `/home/administrator/OpenROAD-flow-scripts/flow/results/sky130hd/aes/base/`.
