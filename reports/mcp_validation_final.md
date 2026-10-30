# MCP validation

Checked: 2026-10-17. Designs `gcd`, `aes`, and `ibex` on `sky130hd`. Tool modules were called as they are. No server, agent, or benchmark file was edited.

The configured flow directory `\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow` is visible to the Windows process. `make` is not on the Windows PATH. WSL `wsl.exe` is present.

## list_params

| Design | Parameters | Executable | Status |
| --- | --- | --- | --- |
| gcd | 10 | 9 | PASS |
| aes | 9 | 8 | PASS |
| ibex | 9 | 8 | PASS |

`_FR_LAYER_ADJUST` is the non-executable knob on each design.

## run_flow

`run_flow(design, "sky130hd", None)` was called for each design with an isolated runs directory, an empty parameter set, and a 20 second timeout. Each call accepted the design config, reserved a run id, and wrote a manifest with status `running`. Process start then raised `FileNotFoundError` (`WinError 2`, the system cannot find the file specified). The argv head is:

```
make -C \\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow DESIGN_CONFIG=./designs/sky130hd/<design>/config.mk
```

The argv ends with `FLOW_VARIANT=p1<run_id>` and `finish`. No Make process was created, and no new flow variant was built.

| Design | Status |
| --- | --- |
| gcd | FAIL |
| aes | FAIL |
| ibex | FAIL |

## get_metrics

`get_metrics` only accepts a `p1` plus 32-hex variant, so the `base` directory cannot be addressed directly. The real `metadata.json` for each design was copied under a legal variant and passed to `get_metrics` and `extract_metrics`. Both returned the same values.

| Design | Area | Power | Setup WNS | Hold WNS | DRC | Runtime | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gcd | 5412.69 | 0.00985037 | -1.45954 | 0.532397 | 0 | missing | PASS for five fields |
| aes | 130617 | 0.572873 | -0.0805747 | 0.483049 | 0 | missing | PASS for five fields |
| ibex | 172822 | 0.0655049 | -0.551246 | 0.420976 | 0 | missing | PASS for five fields |

Runtime is missing because `finish__runtime__total` and `total_time` are clock strings (`0:04.43`, `0:00:46.290000`). The parser accepts only finite numbers. Wall-clock totals from the Make elapsed table are in `results/design_metrics.json`: gcd 124 s, aes 2623 s, ibex 4094 s.

## read_report

The same legal-variant copy was used. Each call returned the real report file.

| Design | Timing | DRC report | Congestion | Status |
| --- | --- | --- | --- | --- |
| gcd | `6_finish.rpt`, 200 lines | `5_route_drc.rpt`, 0 bytes | `5_global_route.rpt`, 200 lines | PASS |
| aes | `6_finish.rpt`, 200 lines | `5_route_drc.rpt`, 0 bytes | `5_global_route.rpt`, 200 lines | PASS |
| ibex | `6_finish.rpt`, 200 lines | `5_route_drc.rpt`, 0 bytes | `5_global_route.rpt`, 200 lines | PASS |

The DRC count used by the tools is `detailedroute__route__drc_errors` in `metadata.json`, which is 0 for all three designs. The `.rpt` file itself is empty.

## Tool summary

| Tool | gcd | aes | ibex |
| --- | --- | --- | --- |
| list_params | PASS | PASS | PASS |
| run_flow | FAIL | FAIL | FAIL |
| get_metrics | PASS, runtime missing | PASS, runtime missing | PASS, runtime missing |
| read_report | PASS | PASS | PASS |
