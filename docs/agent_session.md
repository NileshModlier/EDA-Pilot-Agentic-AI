# Example agent session

Target: `gcd` on `sky130hd`. Budget: 10 runs. Objective: the smallest `_SDC_CLK_PERIOD` with DRC count 0, setup WNS >= 0, and hold WNS >= 0.

This transcript is the session written to `runs/decision_log.jsonl`. OpenROAD is not installed in this workspace, so the runs used the same make stand-in as the unit tests. That stand-in returns one fixed result: setup WNS `-0.012`, hold WNS `0.005`, DRC count `0`. None of the 10 runs meet signoff. The loop still stays inside the allowlist and stops when the budget is exhausted.

Advisor: offline clock search. No chat model was configured. `validate` called the P1 parameter checker before every `run_flow`.

## Result

```text
stop: run budget exhausted
iterations: 10
remaining_runs: 0
```

Best run, kept because every iteration had the same metrics and none passed:

```json
{
  "iteration": 1,
  "run_id": "b2527b296c8549da97fa94f519acac31",
  "clock_period": 1.1,
  "passed": false,
  "parameters": { "_SDC_CLK_PERIOD": 1.1 },
  "metrics": {
    "setup_wns": -0.012,
    "hold_wns": 0.005,
    "drc_count": 0.0
  },
  "duration": 0.116
}
```

On a live ORFS checkout, a later passing run with a smaller clock replaces this best run.

## Iteration 1

Diagnosis: no completed run yet. The proposal starts at the design default.

```json
{
  "changes": [
    {
      "parameter": "_SDC_CLK_PERIOD",
      "value": 1.1,
      "reason": "Start at the design default clock period of 1.1 ns."
    }
  ]
}
```

`run_flow` returned status `ok`. Check result: `fail`, because setup WNS is `-0.012`.

## Iteration 2

Diagnosis: `Timing failing because setup WNS is -0.012 ns while DRC is clean.` The timing report tail was read before that sentence was written.

Proposal: raise `_SDC_CLK_PERIOD` to `3.05`, still below the allowlist maximum of `5.0`. Check result: `fail`.

## Iterations 3 through 10

Each failure moves the search upward. Every value is inside `[0.8, 5.0]`.

| iteration | _SDC_CLK_PERIOD | result | duration (s) |
| --- | --- | --- | --- |
| 1 | 1.1 | fail | 0.116 |
| 2 | 3.05 | fail | 0.121 |
| 3 | 4.025 | fail | 0.125 |
| 4 | 4.513 | fail | 0.112 |
| 5 | 4.756 | fail | 0.111 |
| 6 | 4.878 | fail | 0.121 |
| 7 | 4.939 | fail | 0.115 |
| 8 | 4.97 | fail | 0.115 |
| 9 | 4.985 | fail | 0.114 |
| 10 | 5.0 | fail | 0.114 |

Iteration 10 uses the maximum legal period, `5.0`. The next check sees `remaining_runs == 0` and stops. No eleventh run starts.

## Rejected proposal

A proposal of `_SDC_CLK_PERIOD` `9.5` does not reach `run_flow`. The validate node returns:

```text
validation error: _SDC_CLK_PERIOD value 9.5 is outside [0.8, 5]
```

The same node rejects a duplicated parameter and a run that would pass the agent's budget. Those checks are the P1 validator plus the agent's remaining-run counter.
