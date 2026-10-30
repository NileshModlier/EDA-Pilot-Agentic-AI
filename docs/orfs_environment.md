# ORFS environment

The checkout is Ubuntu on WSL, commit `ef421749a`:

`/home/administrator/OpenROAD-flow-scripts`

Windows reads that same tree at:

`\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts`

`ORFS_ROOT` is set in both places. A shell that was already open does not see a new user variable until it is started again.

## Windows PowerShell

Persistent user variables:

```powershell
[Environment]::SetEnvironmentVariable(
  "ORFS_ROOT",
  "\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts",
  "User"
)
[Environment]::SetEnvironmentVariable(
  "ORFS_FLOW_DIR",
  "\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow",
  "User"
)
```

Load them into the current window:

```powershell
$env:ORFS_ROOT = [Environment]::GetEnvironmentVariable("ORFS_ROOT", "User")
$env:ORFS_FLOW_DIR = [Environment]::GetEnvironmentVariable("ORFS_FLOW_DIR", "User")
Test-Path "$env:ORFS_ROOT\flow\designs\sky130hd\gcd\config.mk"
```

`Test-Path` prints `True` when the gcd config is visible.

The same assignment is already stored for this user. Checked on 2026-10-17:

| Check | Result |
| --- | --- |
| User `ORFS_ROOT` | `\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts` |
| User `ORFS_FLOW_DIR` | `\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts\flow` |
| `flow\designs\sky130hd\gcd\config.mk` | PASS |

Re-apply the variables with `python scripts\configure_orfs_root.py`.

## WSL

Inside Ubuntu the checkout path uses forward slashes. Add this to `~/.profile` so a login shell sees it, and to `~/.bashrc` so an interactive terminal sees it:

```bash
# EDA Pilot ORFS_ROOT
export ORFS_ROOT=/home/administrator/OpenROAD-flow-scripts
export ORFS_FLOW_DIR="$ORFS_ROOT/flow"
```

Those lines are present in both files. Ubuntu's default `~/.bashrc` returns immediately for a non-interactive shell, so the lines in `.bashrc` apply to interactive terminals. Login commands such as `wsl -d Ubuntu -- bash -lc` read `~/.profile`.

Check from a new Ubuntu shell:

```bash
printf '%s\n' "$ORFS_ROOT"
test -f "$ORFS_ROOT/flow/designs/sky130hd/gcd/config.mk" && echo PASS
```

Checked on 2026-10-17: `ORFS_ROOT` resolved to `/home/administrator/OpenROAD-flow-scripts`, and the gcd config test passed.
