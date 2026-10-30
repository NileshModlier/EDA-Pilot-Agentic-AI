# Changelog

All notable changes to EDA Pilot AI are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-10-29

First public release. The measured study is complete: sky130hd `gcd`, `aes` and `ibex`, budget 10, seed 1.

### Added
- **Release package.** README, architecture, benchmark results, case study, executive summary, technology stack, lessons learned, roadmap, interview guide, release notes, recruiter and hiring-manager summaries, and `citations.bib`.
- **Diagrams.** `diagrams/architecture.svg`, `architecture.mmd` (Mermaid), `architecture.drawio` (diagrams.net) and `technology_stack.svg`.
- **Plots.** The seven comparison figures redrawn from `results/final_benchmark_results.json` with `scripts/make_release_plots.py`, plus a new `search_trajectory.png` that shows the clock tried at every scored run.
- **Assets.** Logo, banner, and screenshots rendered from recorded logs and real tool output.
- **Reports.** `reports/final_benchmark_report.md` and `reports/benchmark_summary.md` as release copies of the P3.4 analysis, with the numbers unchanged, plus a `reports/README.md` index.
- **Repository tooling.** GitHub Actions workflow (`pytest` on Python 3.11, 3.12 and 3.13), issue and pull-request templates, and `.gitattributes`.

### Changed
- Package version `0.1.0` → `1.0.0` in `pyproject.toml` and `eda_pilot/__init__.py`. No behaviour changed.

### Results recorded in this release
- The agent signed off 3 of 3 designs. Default ORFS signed off 0 of 3.
- Best passing clock vs random search: `gcd` 2.867 vs 4.113 ns (−30.3%), `aes` 4.822 vs 6.261 ns (−23.0%), `ibex` 9.000 vs 10.531 ns (−14.5%).
- 52 scored runs and 6 unscored interruptions, all kept in the record.

## [0.1.0] — 2026-10-17 → 2026-10-29

Development releases. The package version stayed at `0.1.0` while the work moved through the phases below. They are listed newest first.

### P3.4 / P3.5 — analysis and closure (2026-10-29)

**Added**
- `results/final_benchmark_results.json`: every scored trial, per-method summaries and unscored interruptions.
- `reports/final_benchmark_report.md`: leaderboards, success rate, failure classes, runtime and QoR analysis.
- Closure set in `docs/closure/`: executive summary, overview, README draft, resume bullets, LinkedIn post, interview talking points, diagrams, lessons, roadmap.

### P3.3 — benchmark campaign (2026-10-18 → 2026-10-29)

**Added**
- `gcd` campaign (default, random, agent, AutoTuner row) in `results/benchmark_campaign/`.
- Checkpointed `aes` and `ibex` campaign with resume support (`scripts/resume_campaign.py`, `results/campaign_checkpoint.json`).
- Decision logs for every agent session in `results/benchmark_campaign/logs/`.

**Fixed**
- Interrupted flows whose manifests still said `running` were recorded as unscored attempts and not counted as trials. The same sample or clock search continued in a new flow variant.

### WSL execution bridge (2026-10-18)

**Added**
- When `ORFS_ROOT` is a `\\wsl$\<distro>\…` path on Windows, `run_flow` runs the same validated argv through `wsl.exe -d <distro> -- bash -lc`. It sources `env.sh`, runs `make … finish`, then `make … metadata-generate`.
- Tests: `test_wsl_launch_quotes_the_linux_flow`, `test_local_make_is_not_sent_to_wsl`.

**Fixed**
- `run_flow` failed with `FileNotFoundError` (WinError 2) because GNU Make exists only inside WSL.
- `finish` alone does not write `metadata.json`. Metadata generation is now part of each launch.

### Environment validation and design catalog (2026-10-17)

**Added**
- `aes` and `ibex` on sky130hd in `configs/allowed_parameters.json`, using ranges from the ORFS `autotuner.json` files.
- Environment, ORFS discovery, OpenROAD smoke and MCP validation reports in `reports/`.
- Toolchain recorded: OpenROAD `26Q4-110-g91e5f5ff2f`, Yosys 0.68+, KLayout 0.30.0, GNU Make 4.4.1, Ubuntu 26.04 LTS on WSL.

### P3.0 — benchmark harness (2026-10-17)

**Added**
- `benchmarks/`: default (one unmodified run), seeded random search over executable knobs, OpenROAD AutoTuner wrapper, agent runner, and `compare_results.py` (rank by smallest passing clock).
- Unavailable or failed methods are recorded as such, with no metrics filled in.

### P2.0 — LangGraph agent (2026-10-17)

**Added**
- `agent/`: five-node StateGraph (`analyse → propose → validate → run → check`), Pydantic proposal models (≤ 3 changes with reasons), an offline clock-search advisor, an optional chat-model advisor via `EDA_PILOT_MODEL`, a 0.05 ns convergence rule, and a JSONL decision log.

### P1.0 — MCP server (2026-10-17)

**Added**
- `eda_pilot/server.py`: MCP server `eda-pilot-orfs` (MCP Python SDK 2.x) with `list_params`, `run_flow`, `get_metrics` and `read_report`.
- `mcp_tools/`: allowlist validation, fixed argv builder (`shell=False`), private SDC per run, run budget with a file lock, timeout with process-tree kill, METRICS2.1 extraction, and capped report tails.
- `tests/` with a `make` stand-in, so OpenROAD is not needed to test.

[1.0.0]: https://github.com/NileshModlier/EDA-Pilot-AI/releases/tag/v1.0.0
