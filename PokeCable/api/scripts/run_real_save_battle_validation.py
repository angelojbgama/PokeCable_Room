from __future__ import annotations

import argparse
import copy
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


API_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = API_ROOT.parents[1]
BACKEND_ROOT = PROJECT_ROOT / "PokeCable" / "backend"
SAVE_ROOT = PROJECT_ROOT / "save"
REPORT_ROOT = PROJECT_ROOT / "PokeCable" / "docs" / "battle-validation"

for path in (API_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.engines.gen1.damage import calculate_damage_gen1
from app.engines.gen1.engine import BattleEngineGen1, BattleSideGen1
from app.engines.gen1.models import PokemonGen1
from app.engines.gen2.damage import calculate_damage_gen2
from app.engines.gen2.engine import BattleEngineGen2, BattleSideGen2
from app.engines.gen2.models import PokemonGen2
from app.engines.gen3.battle_damage import calculate_damage
from app.engines.gen3.battle_engine_core import BattleSide, CustomBattleEngine
from app.engines.gen3.battle_pokemon import BattlePokemon
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser


GEN1_SAVES = [
    "gen 1/Pokemon - Red Version.sav",
    "gen 1/Pokemon - Blue Version.sav",
    "gen 1/Pokemon - Yellow Version.sav",
]
GEN2_SAVES = [
    "gen 2/Pokemon - Gold Version.sav",
    "gen 2/Pokemon - Silver Version.sav",
    "gen 2/Pokemon - Crystal Version.sav",
]
GEN3_SAVES = [
    "gen 3/Pokemon - Ruby Version.sav",
    "gen 3/Pokemon - Sapphire Version.sav",
    "gen 3/Pokemon - Emerald Version.sav",
    "gen 3/Pokemon - FireRed Version.sav",
    "gen 3/Pokemon - LeafGreen Version.sav",
]
SEMI_INVULNERABLE_MOVES = {"fly", "dig", "dive", "bounce"}


@dataclass(frozen=True)
class SaveTeam:
    generation: int
    save_label: str
    player_name: str
    team: list[Any]


@dataclass(frozen=True)
class BattleSpec:
    generation: int
    battle_no: int
    p1: SaveTeam
    p2: SaveTeam
    p1_active: int
    p2_active: int


def _existing_save(relative_ascii: str) -> Path:
    ascii_path = SAVE_ROOT / relative_ascii
    if ascii_path.exists():
        return ascii_path
    unicode_path = SAVE_ROOT / relative_ascii.replace("Pokemon", "Pokémon")
    if unicode_path.exists():
        return unicode_path
    raise FileNotFoundError(f"Save real ausente: {ascii_path}")


def _load_gen1_team(relative: str) -> SaveTeam:
    path = _existing_save(relative)
    parser = Gen1Parser()
    parser.load(path)
    party = parser.list_party()
    if len(party) < 6:
        raise ValueError(f"{path} precisa ter 6 Pokemon na party para validacao 6v6.")
    team = [PokemonGen1.from_canonical(parser.export_canonical(f"party:{idx}").to_dict()) for idx in range(6)]
    return SaveTeam(1, path.name, parser.get_player_name(), team)


def _load_gen2_team(relative: str) -> SaveTeam:
    path = _existing_save(relative)
    parser = Gen2Parser()
    parser.load(path)
    party = parser.list_party()
    if len(party) < 6:
        raise ValueError(f"{path} precisa ter 6 Pokemon na party para validacao 6v6.")
    team = [PokemonGen2.from_canonical(parser.export_canonical(f"party:{idx}").to_dict()) for idx in range(6)]
    return SaveTeam(2, path.name, parser.get_player_name(), team)


def _load_gen3_team(relative: str) -> SaveTeam:
    path = _existing_save(relative)
    parser = Gen3Parser()
    parser.load(path)
    party = parser.list_party()
    if len(party) < 6:
        raise ValueError(f"{path} precisa ter 6 Pokemon na party para validacao 6v6.")
    team = [BattlePokemon.from_canonical(parser.export_canonical(f"party:{idx}").to_dict()) for idx in range(6)]
    return SaveTeam(3, path.name, parser.get_player_name(), team)


def _rotated_team(team: list[Any], active_index: int) -> list[Any]:
    cloned = copy.deepcopy(team)
    active = cloned.pop(active_index)
    return [active] + cloned


def _team_summary(team: list[Any]) -> list[str]:
    rows = []
    for idx, pokemon in enumerate(team, start=1):
        ability = getattr(pokemon, "ability", None) or "none"
        item = getattr(pokemon, "held_item_id", None) or "none"
        moves = ", ".join(move.name for move in pokemon.moves) or "none"
        rows.append(
            f"{idx}. {pokemon.nickname}/{pokemon.name} L{pokemon.level} "
            f"HP {pokemon.current_hp}/{pokemon.max_hp} types={','.join(pokemon.types)} "
            f"ability={ability} item={item} moves=[{moves}]"
        )
    return rows


def _move_key(move: Any) -> str:
    return str(getattr(move, "name", "")).lower().replace("-", "").replace(" ", "")


def _has_direct_damage_move(pokemon: Any) -> bool:
    return any(move.pp > 0 and move.damage_class != "status" and _move_key(move) not in SEMI_INVULNERABLE_MOVES for move in pokemon.moves)


def _first_alive_bench_index(side: Any) -> int | None:
    active_indices = set(getattr(side, "active_indices", [getattr(side, "active_index", 0)]))
    for idx, pokemon in enumerate(side.team):
        if idx in active_indices:
            continue
        if pokemon.current_hp > 0:
            return idx
    return None


def _ensure_switch_gen1(engine: BattleEngineGen1, side_id: str) -> bool:
    side = engine.sides[side_id]
    active = side.active_pokemon
    if active is not None and active.current_hp > 0 and engine.force_switch_player != side.player_id:
        return True
    next_index = _first_alive_bench_index(side)
    if next_index is None:
        return False
    if engine.force_switch_player == side.player_id:
        engine.submit_action(side.player_id, {"type": "switch", "index": next_index})
    else:
        engine._switch_in(side_id, next_index)
    return True


def _ensure_switch_gen2(engine: BattleEngineGen2, side_id: str) -> bool:
    side = engine.sides[side_id]
    active = side.active_pokemon
    if active is not None and active.current_hp > 0 and side.player_id not in engine.force_switch_players:
        return True
    next_index = _first_alive_bench_index(side)
    if next_index is None:
        return False
    if side.player_id in engine.force_switch_players:
        engine.submit_action(side.player_id, {"type": "switch", "index": next_index})
    else:
        engine._switch_in(side_id, next_index)
    return True


def _ensure_switch_gen3(engine: CustomBattleEngine, side_id: str) -> bool:
    side = engine.sides[side_id]
    request = engine.generate_request(side.player_id)
    active = side.active_pokemon
    if not request.get("forceSwitch") and active is not None and active.current_hp > 0:
        return True
    next_index = _first_alive_bench_index(side)
    if next_index is None:
        return False
    engine.submit_action(side.player_id, {"type": "switch", "index": next_index})
    return True


def _best_move_index_gen1(attacker: PokemonGen1, defender: PokemonGen1) -> int:
    best_idx = -1
    best_damage = -1
    for idx, move in enumerate(attacker.moves):
        if move.pp <= 0 or move.damage_class == "status":
            continue
        if _move_key(move) in SEMI_INVULNERABLE_MOVES and _has_direct_damage_move(attacker):
            continue
        damage, _ = calculate_damage_gen1(attacker, defender, move, is_critical=False, random_factor=255)
        if damage > best_damage:
            best_idx = idx
            best_damage = damage
    return best_idx


def _best_move_index_gen2(attacker: PokemonGen2, defender: PokemonGen2) -> int:
    best_idx = -1
    best_damage = -1
    for idx, move in enumerate(attacker.moves):
        if move.pp <= 0 or move.damage_class == "status":
            continue
        if _move_key(move) in SEMI_INVULNERABLE_MOVES and _has_direct_damage_move(attacker):
            continue
        damage, _ = calculate_damage_gen2(attacker, defender, move, is_critical=False, random_factor=255)
        if damage > best_damage:
            best_idx = idx
            best_damage = damage
    return best_idx


def _best_action_gen3(engine: CustomBattleEngine, side_id: str, attacker: BattlePokemon, defender: BattlePokemon) -> dict[str, Any]:
    request = engine.generate_request(engine.sides[side_id].player_id)
    if request.get("forceSwitch"):
        next_index = _first_alive_bench_index(engine.sides[side_id])
        return {"type": "switch", "index": next_index} if next_index is not None else {"type": "pass"}

    enabled_ids = {
        int(move["id"])
        for move in request.get("active", [{}])[0].get("moves", [])
        if not move.get("disabled")
    }
    best_idx = -1
    best_damage = -1
    for idx, move in enumerate(attacker.moves):
        if enabled_ids and move.move_id not in enabled_ids:
            continue
        if move.damage_class == "status":
            continue
        if _move_key(move) in SEMI_INVULNERABLE_MOVES and _has_direct_damage_move(attacker):
            continue
        damage, _ = calculate_damage(
            attacker,
            defender,
            move,
            is_critical=False,
            weather=engine._effective_weather() if hasattr(engine, "_effective_weather") else engine.weather,
            defender_semi_invulnerable=defender.semi_invulnerable,
            defending_side=engine.sides["p2" if side_id == "p1" else "p1"],
            random_factor=100,
            generation=3,
        )
        if damage > best_damage:
            best_idx = idx
            best_damage = damage
    return {"type": "move", "move_index": best_idx}


def _run_gen1(spec: BattleSpec, turn_limit: int) -> tuple[bool, list[str], BattleEngineGen1]:
    engine = BattleEngineGen1(
        f"real-save-gen1-{spec.battle_no}",
        BattleSideGen1("p1", spec.p1.player_name, _rotated_team(spec.p1.team, spec.p1_active)),
        BattleSideGen1("p2", spec.p2.player_name, _rotated_team(spec.p2.team, spec.p2_active)),
    )
    engine.start_battle()
    for _ in range(turn_limit):
        if engine.finished:
            break
        if not _ensure_switch_gen1(engine, "p1") or not _ensure_switch_gen1(engine, "p2"):
            break
        p1 = engine.sides["p1"].active_pokemon
        p2 = engine.sides["p2"].active_pokemon
        if p1 is None or p2 is None:
            break
        engine.submit_action("p1", {"type": "move", "move_index": _best_move_index_gen1(p1, p2)})
        engine.submit_action("p2", {"type": "move", "move_index": _best_move_index_gen1(p2, p1)})
    return engine.finished, engine.logs, engine


def _run_gen2(spec: BattleSpec, turn_limit: int) -> tuple[bool, list[str], BattleEngineGen2]:
    engine = BattleEngineGen2(
        f"real-save-gen2-{spec.battle_no}",
        BattleSideGen2("p1", spec.p1.player_name, _rotated_team(spec.p1.team, spec.p1_active)),
        BattleSideGen2("p2", spec.p2.player_name, _rotated_team(spec.p2.team, spec.p2_active)),
    )
    engine.start_battle()
    for _ in range(turn_limit):
        if engine.finished:
            break
        if not _ensure_switch_gen2(engine, "p1") or not _ensure_switch_gen2(engine, "p2"):
            break
        p1 = engine.sides["p1"].active_pokemon
        p2 = engine.sides["p2"].active_pokemon
        if p1 is None or p2 is None:
            break
        engine.submit_action("p1", {"type": "move", "move_index": _best_move_index_gen2(p1, p2)})
        engine.submit_action("p2", {"type": "move", "move_index": _best_move_index_gen2(p2, p1)})
    return engine.finished, engine.logs, engine


def _run_gen3(spec: BattleSpec, turn_limit: int) -> tuple[bool, list[str], CustomBattleEngine]:
    engine = CustomBattleEngine(
        f"real-save-gen3-{spec.battle_no}",
        BattleSide("p1", spec.p1.player_name, _rotated_team(spec.p1.team, spec.p1_active)),
        BattleSide("p2", spec.p2.player_name, _rotated_team(spec.p2.team, spec.p2_active)),
    )
    engine.start_battle()
    for _ in range(turn_limit):
        if engine.finished:
            break
        if not _ensure_switch_gen3(engine, "p1") or not _ensure_switch_gen3(engine, "p2"):
            break
        p1 = engine.sides["p1"].active_pokemon
        p2 = engine.sides["p2"].active_pokemon
        if p1 is None or p2 is None:
            break
        engine.submit_action("p1", _best_action_gen3(engine, "p1", p1, p2))
        if not engine.finished:
            engine.submit_action("p2", _best_action_gen3(engine, "p2", p2, p1))
    return engine.finished, engine.logs, engine


def _battle_specs(teams: list[SaveTeam], generation: int, count: int) -> list[BattleSpec]:
    specs = []
    for idx in range(count):
        p1 = teams[idx % len(teams)]
        p2 = teams[(idx + 1 + (idx // len(teams))) % len(teams)]
        if p1.save_label == p2.save_label:
            p2 = teams[(idx + 1) % len(teams)]
        specs.append(
            BattleSpec(
                generation=generation,
                battle_no=idx + 1,
                p1=p1,
                p2=p2,
                p1_active=idx % 6,
                p2_active=(idx * 2 + 1) % 6,
            )
        )
    return specs


def _write_generation_report(
    generation: int,
    specs: list[BattleSpec],
    runner: Callable[[BattleSpec, int], tuple[bool, list[str], Any]],
    turn_limit: int,
) -> Path:
    lines = [
        f"# Real Save Battle Validation Gen {generation}",
        "source: local .sav files parsed by pokecable_room parsers",
        "reference: pret disassemblies available under reference/pret when cloned",
        f"battle_count: {len(specs)}",
        f"turn_limit: {turn_limit}",
        "",
    ]
    pass_count = 0
    fail_count = 0

    for spec in specs:
        ok, logs, engine = runner(spec, turn_limit)
        pass_count += int(ok)
        fail_count += int(not ok)
        lines.extend(
            [
                f"## Battle {spec.battle_no}",
                f"generation: {generation}",
                f"p1_save: {spec.p1.save_label}",
                f"p2_save: {spec.p2.save_label}",
                f"p1_player: {spec.p1.player_name}",
                f"p2_player: {spec.p2.player_name}",
                f"result: {'PASS' if ok else 'FAIL'}",
                f"finished: {engine.finished}",
                f"turns: {engine.turn}",
                f"winner_id: {getattr(engine, 'winner_id', None)}",
                "p1_team:",
                *[f"  {row}" for row in _team_summary(engine.sides["p1"].team)],
                "p2_team:",
                *[f"  {row}" for row in _team_summary(engine.sides["p2"].team)],
                "logs:",
                *[f"  {log}" for log in logs],
                "",
            ]
        )

    lines.extend([f"summary: pass={pass_count} fail={fail_count} total={pass_count + fail_count}", ""])
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"real-save-gen{generation}-10-battles.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_reports(count: int = 10, turn_limit: int = 250) -> list[Path]:
    random.seed(1)
    gen1 = [_load_gen1_team(relative) for relative in GEN1_SAVES]
    gen2 = [_load_gen2_team(relative) for relative in GEN2_SAVES]
    gen3 = [_load_gen3_team(relative) for relative in GEN3_SAVES]
    return [
        _write_generation_report(1, _battle_specs(gen1, 1, count), _run_gen1, turn_limit),
        _write_generation_report(2, _battle_specs(gen2, 2, count), _run_gen2, turn_limit),
        _write_generation_report(3, _battle_specs(gen3, 3, count), _run_gen3, turn_limit),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real-save 6v6 battle validation for Gen 1, Gen 2 and Gen 3.")
    parser.add_argument("--count", type=int, default=10, help="Battles per generation.")
    parser.add_argument("--turn-limit", type=int, default=250, help="Maximum turns per battle.")
    args = parser.parse_args()
    for path in build_reports(count=args.count, turn_limit=args.turn_limit):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
