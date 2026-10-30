## What changed

<!-- One or two sentences. -->

## Why

<!-- Link the issue if there is one. -->

## How it was verified

- [ ] `python -m pytest` passes
- [ ] New rejection paths have tests
- [ ] Docs updated where behaviour changed (README, ARCHITECTURE.md, CHANGELOG.md)

## Guardrail checklist

- [ ] No model output reaches `make` arguments, report paths or file writes without validation in code
- [ ] New knobs are added only through `configs/allowed_parameters.json`
- [ ] Subprocesses use an argument list with `shell=False`
- [ ] Benchmark results are appended, not edited. Missing numbers stay `null`
