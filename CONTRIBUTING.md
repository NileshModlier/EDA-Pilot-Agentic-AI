# Contributing to EDA Pilot AI

Thank you for your interest. EDA Pilot is a small, measured project: every claim in the README traces back to a file in `results/`. Contributions are welcome when they keep it that way.

## Ground rules

1. **The model never gets on the launch path.** `analyse` and `propose` may suggest. `validate`, `run` and `check` stay in code. A pull request that lets a model build `make` arguments, choose a report path, or skip validation will not be merged.
2. **New knobs enter through the allowlist.** Add a parameter to `configs/allowed_parameters.json`, with its type, range, default, `apply` mode and `default_source`, and add a test. A design `autotuner.json` may tighten a range. It may never add a name or widen a range.
3. **Never fill in a number.** A method that did not run is `unavailable`. A run that crashed is an `error` with its cause. Metrics that are missing are `null`. Do not copy values from another method or estimate them.
4. **Benchmark results are append-only.** `results/final_benchmark_results.json` is the v1.0 record. New campaigns go in new files and new report sections. They do not overwrite the v1.0 rows.

## Development setup

```bash
git clone https://github.com/NileshModlier/EDA-Pilot-AI.git
cd EDA-Pilot-AI
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

The test suite uses `tests/fake_make.py` as a stand-in for GNU Make, so you do not need OpenROAD to work on the server, the agent or the harness. A real flow needs an OpenROAD-flow-scripts checkout. See [docs/technology_stack.md](docs/technology_stack.md).

## Making a change

1. Open an issue first for anything larger than a fix, and describe the behaviour you expect.
2. Create a branch: `feat/<short-name>`, `fix/<short-name>` or `docs/<short-name>`.
3. Keep commits focused. Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `bench:`).
4. Add or update tests. Every rejection path in `mcp_tools/validation.py` and `mcp_tools/run_flow.py` has a test, and new ones should too.
5. Run `python -m pytest` and make sure all tests pass.
6. Update the docs that your change touches (README tables, `ARCHITECTURE.md`, `CHANGELOG.md`).
7. Open a pull request that explains what changed, why, and how you verified it.

### Adding a design or platform

- Add the design under `configs/allowed_parameters.json` → `designs.<name>.platforms.<platform>.parameters`, using the ranges from that design's ORFS `autotuner.json`.
- Record where each default comes from in `default_source`.
- Mark any knob that would rewrite a platform file as `"apply": "unsupported"` with a `reason`.
- Add catalog tests similar to `tests/test_design_catalog.py`.

### Contributing benchmark results

- State the platform, designs, budget, seed, ORFS and OpenROAD versions, host and timeout.
- Commit the raw per-trial JSON, the decision logs and the generated report.
- Keep unscored interruptions separate from scored trials, as v1.0 does.
- Regenerate plots with `python scripts/make_release_plots.py <results.json> <out_dir>`.

## Code style

- Python 3.11+, type hints throughout, `from __future__ import annotations`.
- Pydantic models use `extra="forbid"`.
- Subprocesses always use an argument list and `shell=False`.
- Error messages are plain sentences that name the parameter and the rule that was broken.

## Reporting security issues

If you find a way to make the server start a process with arguments it did not build itself, rewrite a file outside `.eda_pilot/`, or read outside the run's report directories, please do **not** open a public issue. Contact the maintainer privately through the GitHub profile [@NileshModlier](https://github.com/NileshModlier) and include a minimal reproduction.

## Code of conduct

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
