# Resume Bullet Points

Use these as written. Each number is from the sky130hd budget-10, seed-1 study.

- Built a guarded MCP server and LangGraph agent that tunes OpenROAD Flow Scripts, rejecting out-of-range parameters before GNU Make starts and launching Yosys, OpenROAD, and KLayout through WSL.
- Benchmarked the agent against default ORFS and seeded random search on sky130hd gcd, AES, and the Ibex RISC-V core at a budget of 10 runs.
- Delivered the tightest signoff clock on all three designs: 2.867 ns on gcd (30% tighter than random), 4.822 ns on AES (23% tighter), and 9.0 ns on Ibex (15% tighter), each with DRC = 0 and non-negative setup and hold slack.
- Signed off every design where default ORFS missed setup, by −1.460 ns on gcd, −0.081 ns on AES, and −0.551 ns on Ibex.
- Raised the AES signoff rate from 10% for random search to 30% for the agent, and published the full trial record, failure classes, and comparison plots.

Shorter pair, if a resume has room for only two lines:

- Developed an allowlisted LangGraph agent for OpenROAD on sky130hd and beat random search on passing clock by 30% (gcd), 23% (AES), and 15% (Ibex).
- Closed timing signoff on gcd, AES, and Ibex where the default flow failed setup, without accepting a parameter outside the published ranges.
