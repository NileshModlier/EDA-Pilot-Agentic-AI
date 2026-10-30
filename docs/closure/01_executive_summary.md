# Executive Summary

EDA Pilot AI is a closed loop around OpenROAD Flow Scripts. A LangGraph agent proposes clock and floorplan settings. An MCP server checks every setting against an allowlist, then launches Yosys, OpenROAD, and KLayout through WSL. The benchmark asked one question: can that loop find a smaller clock than default ORFS and random search, while still signing off?

Signoff means the flow finishes, DRC count is 0, setup WNS is at least 0, and hold WNS is at least 0. Area, power, and runtime are reported for that result. They do not override a tighter passing clock. The study used sky130hd gcd, AES, and Ibex, budget 10, and seed 1.

The agent signed off all three designs. Default ORFS signed off none. Setup WNS on the default runs was −1.460 ns on gcd, −0.081 ns on AES, and −0.551 ns on Ibex.

Against random search, the agent produced the smallest passing clock on every design:

| Design | EDA Pilot | Random search | Tighter clock |
| --- | ---: | ---: | ---: |
| gcd | 2.867 ns | 4.113 ns | 30.3% |
| AES | 4.822 ns | 6.261 ns | 23.0% |
| Ibex | 9.000 ns | 10.531 ns | 14.5% |

The passing agent clocks are still slower than the default targets, because those targets miss setup. The gain versus default is a legal signoff, not a faster failing clock.

Signoff rate is 3/8 on gcd, 3/10 on AES, and 1/1 on Ibex for the agent, against 4/10, 1/10, and 6/10 for random search. Pooled, that is 7/19 (36.8%) versus 11/30 (36.7%). The clear rate gain is AES. The Ibex agent stopped after its first passing run, so that 100% rate is a single sample.

Random search still wins area, power, and runtime at its looser clocks. The best agent results are 7–23% larger and 30–71% higher power, and the best agent runs take 1.5× to 5.5× as long. AutoTuner recorded no scored trials.

The project is complete as a measured baseline: a guarded agent, a real PDK flow, and a three-design comparison with the primary result in the agent’s favor.
