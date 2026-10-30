"""Point ORFS_ROOT at the Ubuntu checkout and check that the path resolves.

Windows gets a user environment variable. Ubuntu gets the same checkout in
~/.bashrc. Already-open terminals keep their old environment until they start
again.
"""

from __future__ import annotations

import base64
import os
import subprocess
import winreg
from pathlib import Path

WINDOWS_ROOT = r"\\wsl$\Ubuntu\home\administrator\OpenROAD-flow-scripts"
WINDOWS_FLOW = WINDOWS_ROOT + r"\flow"


def configure() -> dict[str, str]:
    _set_user_variable("ORFS_ROOT", WINDOWS_ROOT)
    _set_user_variable("ORFS_FLOW_DIR", WINDOWS_FLOW)
    bashrc = _ensure_bashrc()
    windows_root = _read_user_variable("ORFS_ROOT")
    windows_flow = _read_user_variable("ORFS_FLOW_DIR")
    gcd = Path(WINDOWS_ROOT) / "flow" / "designs" / "sky130hd" / "gcd" / "config.mk"
    linux_root = _wsl_login_value("ORFS_ROOT")
    linux_gcd = _wsl_ok(
        ["bash", "-lc", 'test -f "$ORFS_ROOT/flow/designs/sky130hd/gcd/config.mk"']
    )
    return {
        "bashrc": bashrc,
        "windows_root": windows_root or "",
        "windows_flow": windows_flow or "",
        "windows_gcd": "PASS" if gcd.is_file() else "FAIL",
        "linux_root": linux_root or "",
        "linux_gcd": "PASS" if linux_gcd else "FAIL",
    }


def _set_user_variable(name: str, value: str) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    os.environ[name] = value


def _read_user_variable(name: str) -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _kind = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None
    return str(value)


def _ensure_bashrc() -> str:
    script = """
set -e
block=$(printf '%s\\n' '# EDA Pilot ORFS_ROOT' 'export ORFS_ROOT=/home/administrator/OpenROAD-flow-scripts' 'export ORFS_FLOW_DIR="$ORFS_ROOT/flow"')
for file in "$HOME/.bashrc" "$HOME/.profile"; do
  touch "$file"
  if grep -F "export ORFS_ROOT=/home/administrator/OpenROAD-flow-scripts" "$file" >/dev/null; then
    echo "$file PRESENT"
  else
    printf '\\n%s\\n' "$block" >> "$file"
    echo "$file ADDED"
  fi
done
"""
    text = _wsl_script(script)
    if "ADDED" not in text and "PRESENT" not in text:
        raise RuntimeError(text or "could not update the Ubuntu shell startup files")
    return text.replace("\n", "; ")


def _wsl_login_value(name: str) -> str | None:
    if name != "ORFS_ROOT":
        raise ValueError(name)
    text = _wsl_script('printf "%s" "$ORFS_ROOT"')
    return text or None


def _wsl_ok(args: list[str]) -> bool:
    if args[:2] == ["bash", "-lc"]:
        try:
            _wsl_script(args[2])
        except RuntimeError:
            return False
        return True
    completed = subprocess.run(
        ["wsl", "-d", "Ubuntu", "--", *args],
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return completed.returncode == 0


def _wsl_script(script: str) -> str:
    """Run a bash script inside Ubuntu without the outer shell expanding variables."""

    payload = base64.b64encode(script.replace("\r\n", "\n").replace("\r", "\n").encode()).decode()
    completed = subprocess.run(
        [
            "wsl",
            "-d",
            "Ubuntu",
            "--",
            "bash",
            "-lc",
            f"printf '%s' {payload} | base64 -d > /tmp/eda_orfs_env.sh && bash -l /tmp/eda_orfs_env.sh",
        ],
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    text = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        raise RuntimeError(text or "Ubuntu script failed")
    return text


if __name__ == "__main__":
    result = configure()
    for key, value in result.items():
        print(f"{key}={value}")
