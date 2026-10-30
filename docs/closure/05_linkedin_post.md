# LinkedIn Project Post

Paste the block below. It is ready to publish.

---

I finished EDA Pilot AI, a LangGraph agent that tunes OpenROAD Flow Scripts through a checked MCP interface.

The rule is strict. The agent can propose only allowlisted parameters. The server validates every value before make starts. On Windows, Yosys, OpenROAD, and KLayout run inside WSL. The goal is the smallest clock that still signs off: DRC = 0, setup WNS ≥ 0, and hold WNS ≥ 0.

I measured it on sky130hd gcd, AES, and the Ibex RISC-V core, budget 10, seed 1, against default ORFS and random search.

Default ORFS missed setup on all three designs. The agent signed off all three.

Best passing clocks:

- gcd: 2.867 ns, 30% tighter than random search
- AES: 4.822 ns, 23% tighter
- Ibex: 9.0 ns, 15% tighter

Random search still won area, power, and runtime at its slower clocks. That tradeoff is the result, and it is in the report with every trial.

The useful engineering lesson was the boundary. Analyse and propose may suggest a clock. They cannot launch a flow, invent a metric, or skip a range check.

#OpenROAD #EDA #VLSI #LangGraph #PhysicalDesign
