# IBEX validation

Checked: 2026-10-17. Platform `sky130hd`, flow variant `base`.

Command, from `/home/administrator/OpenROAD-flow-scripts/flow` after sourcing `env.sh`:

```
make DESIGN_CONFIG=./designs/sky130hd/ibex/config.mk
```

Exit code: **0**. The completed stage files were already present, so Make reprinted the elapsed table and did not rebuild the flow. `make metadata-generate` for this design also exited 0.

| Stage | Check | Result |
| --- | --- | --- |
| Synthesis | `1_2_yosys.v` 2,158,537 bytes, `1_synth.odb` 11,926,764 bytes, `1_2_yosys.log` contains `End of script` | PASS |
| Floorplan | `2_floorplan.odb` 14,130,666 bytes | PASS |
| Placement | `3_place.odb` 15,772,251 bytes | PASS |
| CTS | `4_cts.odb` 15,924,158 bytes | PASS |
| Routing | `5_route.odb` 37,243,404 bytes | PASS |
| Final GDS | `6_final.gds` 22,120,568 bytes, `6_1_merged.gds` 22,120,568 bytes | PASS |

Elapsed total: **4094 s**. Peak memory: **1863 MB**. Route stage `5_2_route` elapsed **3525 s**.

Artifacts: `/home/administrator/OpenROAD-flow-scripts/flow/results/sky130hd/ibex/base/`.
