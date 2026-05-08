from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_real_save_battle_validation.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_real_save_battle_validation", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_real_save_validation_builds_same_generation_specs() -> None:
    runner = load_runner_module()
    teams = [runner.SaveTeam(2, f"save-{idx}", f"player-{idx}", [object()] * 6) for idx in range(3)]

    specs = runner._battle_specs(teams, 2, 10)

    assert len(specs) == 10
    assert all(spec.generation == 2 for spec in specs)
    assert all(spec.p1.generation == spec.p2.generation == 2 for spec in specs)
    assert all(spec.p1.save_label != spec.p2.save_label for spec in specs)
    assert {spec.p1_active for spec in specs}.issubset(set(range(6)))
    assert {spec.p2_active for spec in specs}.issubset(set(range(6)))


def test_real_save_validation_writes_reports_from_real_saves(tmp_path, monkeypatch) -> None:
    runner = load_runner_module()
    monkeypatch.setattr(runner, "REPORT_ROOT", tmp_path)

    paths = runner.build_reports(count=1, turn_limit=80)

    assert len(paths) == 3
    for generation, path in enumerate(paths, start=1):
        content = path.read_text(encoding="utf-8")
        assert path.parent == tmp_path
        assert f"Real Save Battle Validation Gen {generation}" in content
        assert "battle_count: 1" in content
        assert "generation: " in content
        assert "p1_team:" in content
        assert "p2_team:" in content
        assert "logs:" in content
        assert "summary: pass=" in content
