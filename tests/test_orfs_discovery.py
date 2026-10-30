"""ORFS discovery rows for a local tree. The test does not call WSL."""

from __future__ import annotations

from pathlib import Path

from scripts.discover_orfs import discover


def _tree(root: Path, *, missing: str | None = None) -> None:
    for design in ("gcd", "aes", "ibex"):
        folder = root / "flow" / "designs" / "sky130hd" / design
        folder.mkdir(parents=True)
        for name in ("config.mk", "constraint.sdc", "autotuner.json"):
            if missing == f"{design}/{name}":
                continue
            (folder / name).write_text("ok\n", encoding="utf-8")
    (root / "flow" / "Makefile").write_text("all:\n", encoding="utf-8")


def test_design_files_pass_and_unset_root_fails(tmp_path: Path) -> None:
    _tree(tmp_path)
    checks = {
        item.name: item
        for item in discover(
            {"ORFS_ROOT": ""},
            root=tmp_path,
            commit="ef421749a",
            make_path="/usr/bin/make",
            openroad_path=None,
            search=False,
        )
    }

    assert checks["ORFS_ROOT environment variable"].result == "FAIL"
    assert checks["ORFS checkout"].result == "PASS"
    assert "ef421749a" in checks["ORFS checkout"].detail
    for design in ("gcd", "aes", "ibex"):
        assert checks[f"{design} directory"].result == "PASS"
        for name in ("config.mk", "constraint.sdc", "autotuner.json"):
            assert checks[f"{design} {name}"].result == "PASS"
    assert checks["OpenROAD binary"].result == "FAIL"
    assert checks["GNU make in Ubuntu"].result == "PASS"


def test_missing_autotuner_file_fails(tmp_path: Path) -> None:
    _tree(tmp_path, missing="aes/autotuner.json")
    checks = {
        item.name: item
        for item in discover(
            {"ORFS_ROOT": str(tmp_path)},
            root=tmp_path,
            search=False,
        )
    }

    assert checks["ORFS_ROOT environment variable"].result == "PASS"
    assert checks["aes autotuner.json"].result == "FAIL"
    assert checks["gcd autotuner.json"].result == "PASS"
