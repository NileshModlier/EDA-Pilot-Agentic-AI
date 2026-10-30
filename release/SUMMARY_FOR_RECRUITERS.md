# EDA Pilot AI: one-page summary for recruiters

**Nilesh P Raghavan** · [github.com/NileshModlier/EDA-Pilot-AI](https://github.com/NileshModlier/EDA-Pilot-AI) · Completed October 2026

## What was built

An **AI agent that tunes computer-chip design software safely**. Turning a chip design into a manufacturable layout takes from minutes to hours per attempt, and the default settings often fail timing requirements. EDA Pilot AI lets an AI agent choose what to try next, while a protective software layer checks every choice against approved limits *before* anything runs. The project was built end to end: agent, safety layer, integration with industry-standard open-source chip tools, a benchmark harness and full documentation.

## Technologies

| Area | Skills shown |
| --- | --- |
| AI agents | LangGraph (agent workflows), LangChain, structured AI outputs (Pydantic) |
| AI tool integration | Model Context Protocol (MCP): built an MCP server with four tools |
| Chip design (EDA) | OpenROAD, OpenROAD Flow Scripts, Yosys, KLayout, SkyWater 130 nm PDK, static timing analysis |
| Software engineering | Python, pytest (48 automated tests), subprocess security, file locking, JSON data pipelines |
| Systems | Windows + WSL (Linux) integration, GNU Make, long-running job orchestration, checkpoint and resume |
| Data and communication | Benchmark design, matplotlib charts, technical writing, architecture diagrams |

## Measurable achievements

- **3 of 3** chip designs met all signoff checks with the agent, against **0 of 3** with the default settings.
- **14.5%–30.3% shorter passing clock periods** (that is, faster chips) than random search on the same budget: gcd 30.3%, AES 23.0%, Ibex RISC-V core 14.5%.
- **Tripled the success rate** on the AES design (30% against 10% for random search).
- **Zero unsafe actions.** Every parameter was validated before execution, with no shell commands and no edits to design files.
- **52 real chip-design runs** (about 21 hours of compute), with every result, failure and interruption published.
- **48 automated tests** that run without the chip tools installed.

## Engineering complexity

- **Six-layer system:** benchmark harness → AI agent → MCP server → safety guardrails → Windows-to-Linux execution bridge → chip-design tools.
- **Safety by design:** the AI can only *suggest*. Code decides, launches and measures.
- **Real-world operations:** handled runs of up to 2 hours, timeouts, interrupted jobs and resumable campaigns.
- **Scientific honesty:** results report the trade-offs too (the faster designs used more area and power) and the limits of the study (one random seed, one technology).

## In one sentence

*Designed and benchmarked a safety-first AI agent for semiconductor physical design that met timing on every test chip where the default flow failed, with passing clock periods up to 30% shorter than random search.*

**Keywords:** AI agents · LangGraph · MCP · LLM tooling · EDA · OpenROAD · physical design · timing closure · VLSI · RISC-V · Python · benchmarking
