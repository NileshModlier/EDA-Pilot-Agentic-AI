# OpenROAD AutoTuner setup

The benchmark looks for AutoTuner in this order:

1. `ORFS_AUTOTUNER`, when that value is a path to a file
2. `openroad_autotuner` on `PATH`
3. `tools/AutoTuner/autotuner_env` inside `ORFS_ROOT`
4. An importable `autotuner.distributed` module

`python scripts/validate_benchmark_env.py` reports whether it is installed, which version answered, and the executable path. This machine does not have that program yet. The steps below are the upstream install path.

## 1. Check out OpenROAD-flow-scripts

AutoTuner is part of the [OpenROAD-flow-scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts) tree. The flow checkout is also what `ORFS_ROOT` points at.

```shell
git clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git
cd OpenROAD-flow-scripts
```

The sky130hd designs used by the benchmark are:

- `flow/designs/sky130hd/gcd`
- `flow/designs/sky130hd/aes`
- `flow/designs/sky130hd/ibex`

Each directory needs `config.mk`, `constraint.sdc`, and `autotuner.json`. When `autotuner.json` is present, `list_params` uses its ranges and keeps them inside `configs/allowed_parameters.json`.

## 2. Install AutoTuner

The upstream installer is a bash script and the documentation pins its virtualenv to Python 3.8. On Windows, run these commands in WSL from the repository root:

```shell
./tools/AutoTuner/installer.sh
./tools/AutoTuner/setup.sh
```

`installer.sh` creates `tools/AutoTuner/autotuner_env` and installs the `openroad_autotuner` command into that environment. `setup.sh` activates it. Leave the environment active, or call the binary by its full path.

Confirm the command answers:

```shell
openroad_autotuner --help
```

The module form, from `tools/AutoTuner` with the virtualenv active, is:

```shell
python3 -m autotuner.distributed --help
```

## 3. Point EDA Pilot at it

From PowerShell, after the checkout and the virtualenv exist:

```powershell
$env:ORFS_ROOT = "C:\path\to\OpenROAD-flow-scripts"
$env:ORFS_AUTOTUNER = "C:\path\to\OpenROAD-flow-scripts\tools\AutoTuner\autotuner_env\bin\openroad_autotuner"
python scripts\validate_benchmark_env.py
```

Inside WSL the binary is usually `tools/AutoTuner/autotuner_env/bin/openroad_autotuner`. A Windows virtualenv uses `Scripts\openroad_autotuner.exe`. The validator accepts either path.

A passing AutoTuner block in `reports/environment_validation.md` shows:

- installed: yes
- a version line from `--version` or the installed package metadata
- the executable path

## 4. Leave the sweep for the benchmark

Do not start `tune --samples` while preparing the machine. The benchmark harness is the program that launches AutoTuner, and only after this report is clean. Re-run `python scripts/validate_benchmark_env.py` after each install step. Installation details that change upstream live in [Instructions for AutoTuner](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/docs/user/InstructionsForAutoTuner.md).
