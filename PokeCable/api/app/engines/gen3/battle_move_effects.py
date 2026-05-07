from __future__ import annotations
import math
import random
from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove
    from .battle_engine_core import CustomBattleEngine

from ...data.move_combat_data import get_move_combat_data
from .battle_damage import calculate_damage
from .battle_types import TYPE_CHART, get_type_multiplier
from .battle_pokemon import BattleMove
from .battle_move_properties import normalize_move_name
from .battle_ability_effects import apply_on_damage_ability_effects

def get_hit_count(move: BattleMove) -> int:
    """
    Retorna a quantidade de hits de um golpe (2, 3 ou 2-5).
    Segue as probabilidades da Gen 3.
    """
    move_name_norm = normalize_move_name(move.name)
    effect = move.effect.lower()
    
    if "hits twice" in effect or "hits 2 times" in effect:
        return 2
    
    if move_name_norm == "triplekick" or "triple kick" in effect:
        return 3

    if "hits 2-5 times" in effect:
        r = random.random()
        if r < 0.375: return 2
        if r < 0.750: return 3
        if r < 0.875: return 4
        return 5
        
    if "hits 3 times" in effect: # Ex: Triple Kick (embora a logica dele seja unica, aqui simplificamos)
        return 3
        
    return 1


def _build_move_from_id(move_id: int) -> BattleMove | None:
    data = get_move_combat_data(int(move_id))
    if not data:
        return None
    return BattleMove(
        move_id=int(move_id),
        name=str(data["name"]),
        type=str(data["type"]),
        power=int(data["power"]) if data.get("power") is not None else 0,
        accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else 100,
        pp=int(data["pp"]),
        max_pp=int(data["pp"]),
        priority=int(data.get("priority") or 0),
        damage_class=str(data["damage_class"]),
        effect=str(data.get("effect") or ""),
        effect_chance=data.get("effect_chance"),
    )


def _pokemon_at_slot(engine: "CustomBattleEngine", side_id: str, slot_idx: int | None) -> "BattlePokemon" | None:
    if slot_idx is None:
        return None
    side = engine.sides.get(side_id)
    if side is None or slot_idx < 0 or slot_idx >= len(side.active_indices):
        return None
    pokemon_index = side.active_indices[slot_idx]
    if pokemon_index < 0 or pokemon_index >= len(side.team):
        return None
    return side.team[pokemon_index]


def _apply_reactive_damage(
    engine: "CustomBattleEngine",
    source_side_id: str,
    source_slot_idx: int,
    target_side_id: str,
    target_slot_idx: int,
    target: "BattlePokemon",
    move: BattleMove,
    raw_damage: int,
    damage_class: str,
) -> int:
    if raw_damage <= 0 or target.current_hp <= 0:
        return 0

    multiplier = get_type_multiplier(move.type, target.types)
    target_tag = f"{target_side_id}{chr(97 + target_slot_idx)}"
    if multiplier == 0:
        engine.add_log(f"|-immune|{target_tag}: {target.nickname}")
        return 0

    damage = max(1, math.floor(raw_damage * multiplier))

    if target.substitute_hp > 0:
        target.substitute_hp = max(0, target.substitute_hp - damage)
        engine.add_log(f"|-activate|{target_tag}: {target.nickname}|Substitute|[damage]")
        if target.substitute_hp <= 0:
            engine.add_log(f"|-end|{target_tag}: {target.nickname}|Substitute")
        engine.add_log(f"|damage|{target_tag}: {target.nickname}|{engine._condition(target)}")
        return damage

    if target.endure_active and damage >= target.current_hp and target.current_hp > 1:
        damage = target.current_hp - 1

    target.current_hp = max(0, target.current_hp - damage)
    target.last_damage_taken = damage
    target.last_damage_class = damage_class
    target.last_damage_move_type = move.type
    target.last_damage_source_side = source_side_id
    target.last_damage_source_slot = source_slot_idx
    target.damage_taken_this_turn = max(target.damage_taken_this_turn, damage)

    if target.bide_turns is not None and target.bide_turns > 0:
        target.bide_damage += damage
        target.bide_target_side = source_side_id
        target.bide_target_slot = source_slot_idx

    if multiplier > 1:
        engine.add_log("|-supereffective|")
    elif 0 < multiplier < 1:
        engine.add_log("|-resisted|")

    engine.add_log(f"|damage|{target_tag}: {target.nickname}|{engine._condition(target)}")
    if target.current_hp <= 0:
        engine.add_log(f"|faint|{target_tag}: {target.nickname}")
        if target.destiny_bond:
            source_target = _pokemon_at_slot(engine, source_side_id, source_slot_idx)
            if source_target and source_target.current_hp > 0:
                source_target.current_hp = 0
                engine.add_log(f"|-activate|{target_tag}: {target.nickname}|move: Destiny Bond")
                engine.add_log(f"|faint|{source_side_id}{chr(97 + source_slot_idx)}: {source_target.nickname}")

    return damage

def apply_move_effects(
    engine: CustomBattleEngine, 
    attacker: BattlePokemon, 
    defender: BattlePokemon, 
    move: BattleMove, 
    damage: int, 
    side_id: str,
    move_index: int = 0
):
    """
    Analisa o efeito do golpe e aplica as consequencias secundarias na engine.
    """
    effect = move.effect.lower().replace("’", "'")
    move_name_norm = normalize_move_name(move.name)
    battle_weather = engine._effective_weather() if hasattr(engine, "_effective_weather") else engine.weather
    peer_side_id = "p2" if side_id == "p1" else "p1"
    attacker_slot_idx = next(
        (i for i, p_idx in enumerate(engine.sides[side_id].active_indices) if engine.sides[side_id].team[p_idx] == attacker),
        0,
    )

    # 0. Efeitos de defesa e setup que nao dependem de acertar um alvo
    if move_name_norm in {"protect", "detect"}:
        # A Gen 3 reduz a chance de sucesso em usos consecutivos; mantemos uma
        # aproximacao simples e deterministica o bastante para o jogo base.
        success_chance = 1.0 if attacker.consecutive_protects == 0 else (1 / (2 ** attacker.consecutive_protects))
        if random.random() <= success_chance:
            attacker.is_protected = True
            attacker.consecutive_protects += 1
            engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|{move.name}")
        else:
            attacker.consecutive_protects = 0
            engine.add_log("|-fail|")
        return

    if move_name_norm == "endure":
        attacker.endure_active = True
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Endure")
        return

    if move_name_norm == "substitute":
        if attacker.substitute_hp > 0:
            engine.add_log("|-fail|")
            return
        substitute_hp = max(1, attacker.max_hp // 4)
        if attacker.current_hp <= substitute_hp:
            engine.add_log("|-fail|")
            return
        attacker.current_hp -= substitute_hp
        attacker.substitute_hp = substitute_hp
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Substitute")
        engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|Substitute")
        return

    if move_name_norm == "recover":
        if attacker.current_hp >= attacker.max_hp:
            engine.add_log("|-fail|")
            return
        heal_amount = max(1, math.floor(attacker.max_hp / 2))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        engine.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] move: Recover")
        return

    if move_name_norm == "focusenergy":
        if attacker.focus_energy:
            engine.add_log("|-fail|")
            return
        attacker.focus_energy = True
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Focus Energy")
        return

    if move_name_norm in {"raindance", "sunnyday", "sandstorm", "hail"}:
        weather_key = {
            "raindance": "rain",
            "sunnyday": "sun",
            "sandstorm": "sandstorm",
            "hail": "hail",
        }[move_name_norm]
        if engine.weather == weather_key:
            engine.add_log("|-fail|")
            return
        turns = 5
        engine.set_weather(weather_key, turns)
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|{move.name}")
        return

    if move_name_norm in {"morningsun", "synthesis", "moonlight"}:
        if attacker.current_hp >= attacker.max_hp:
            engine.add_log("|-fail|")
            return
        if battle_weather == "sun":
            heal_ratio = 2 / 3
        elif battle_weather == "none":
            heal_ratio = 1 / 2
        else:
            heal_ratio = 1 / 4
        heal_amount = max(1, math.floor(attacker.max_hp * heal_ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        engine.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] move: {move.name}")
        return

    if move_name_norm == "haze":
        for battle_side in engine.sides.values():
            for pkmn in battle_side.active_list:
                pkmn.stat_stages = {key: 0 for key in pkmn.stat_stages}
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Haze")
        return

    if move_name_norm in {"doubleteam", "minimize"}:
        boost = 1 if move_name_norm == "doubleteam" else 2
        _apply_stat_boost(engine, attacker, side_id, "evasion", boost)
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|{move.name}")
        return

    if move_name_norm == "refresh":
        if attacker.status_condition not in {"brn", "par", "psn", "tox"}:
            engine.add_log("|-fail|")
            return
        old_status = attacker.status_condition
        attacker.status_condition = None
        attacker.toxic_turns = 0
        engine.add_log(f"|-curestatus|{side_id}a: {attacker.nickname}|{old_status}|[from] move: Refresh")
        return

    if move_name_norm in {"healbell", "aromatherapy"}:
        cured_any = False
        for ally_idx, ally in enumerate(engine.sides[side_id].team):
            if ally.current_hp <= 0:
                continue
            if move_name_norm == "healbell" and ally.ability == "soundproof":
                continue
            if ally.status_condition in {"brn", "par", "psn", "tox"} or ally.nightmare_active:
                old_status = ally.status_condition
                ally.status_condition = None
                ally.toxic_turns = 0
                ally.nightmare_active = False
                slot_tag = f"{side_id}{chr(97 + ally_idx)}"
                if old_status:
                    engine.add_log(f"|-curestatus|{slot_tag}: {ally.nickname}|{old_status}|[from] move: {move.name}")
                else:
                    engine.add_log(f"|-end|{slot_tag}: {ally.nickname}|move: Nightmare|[from] move: {move.name}")
                cured_any = True
        if not cured_any:
            engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|{move.name}")
        return

    if move_name_norm == "spikes":
        side = engine.sides[peer_side_id]
        if side.spikes_layers >= 3:
            engine.add_log("|-fail|")
            return
        side.spikes_layers += 1
        engine.add_log(f"|-sidestart|{peer_side_id}: {side.player_name}|move: Spikes")
        return

    if move_name_norm == "painsplit":
        if defender is None or defender.current_hp <= 0:
            engine.add_log("|-fail|")
            return
        avg_hp = math.floor((attacker.current_hp + defender.current_hp) / 2)
        attacker.current_hp = min(attacker.max_hp, avg_hp)
        defender.current_hp = min(defender.max_hp, avg_hp)
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Pain Split")
        engine.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] move: Pain Split")
        engine.add_log(f"|-damage|{peer_side_id}a: {defender.nickname}|{engine._condition(defender)}|[from] move: Pain Split")
        return

    if move_name_norm == "psychup":
        attacker.stat_stages = defender.stat_stages.copy()
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Psych Up")
        return

    if move_name_norm == "attract":
        if attacker.gender is None or defender.gender is None or attacker.gender == defender.gender:
            engine.add_log("|-fail|")
            return
        if defender.ability == "oblivious":
            engine.add_log("|-fail|")
            return
        if defender.attracted_to_side is not None:
            engine.add_log("|-fail|")
            return
        defender.attracted_to_side = side_id
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Attract")
        return

    if move_name_norm == "foresight":
        if defender.foresight_active:
            engine.add_log("|-fail|")
            return
        defender.foresight_active = True
        defender.stat_stages["evasion"] = 0
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Foresight")
        return

    if move_name_norm == "disable":
        if defender.last_move_id is None or defender.disable_turns > 0 or defender.disable_move_id is not None:
            engine.add_log("|-fail|")
            return
        disabled_move = next((m for m in defender.moves if m.move_id == defender.last_move_id), None)
        if disabled_move is None:
            engine.add_log("|-fail|")
            return
        disabled_name = disabled_move.name.lower().replace("-", "").replace(" ", "")
        if disabled_name in {"struggle", "metronome", "mimic", "mirrormove"}:
            engine.add_log("|-fail|")
            return
        defender.disable_move_id = defender.last_move_id
        defender.disable_turns = random.randint(1, 8)
        engine.add_log(f"|-activate|{peer_side_id}a: {defender.nickname}|move: Disable|[of] {disabled_move.name}")
        return

    if move_name_norm == "encore":
        if defender.last_move_id is None or defender.encore_turns > 0:
            engine.add_log("|-fail|")
            return
        encore_move_index = next((i for i, m in enumerate(defender.moves) if m.move_id == defender.last_move_id), None)
        if encore_move_index is None:
            engine.add_log("|-fail|")
            return
        target_move = defender.moves[encore_move_index]
        target_name = target_move.name.lower().replace("-", "").replace(" ", "")
        if target_name in {"struggle", "metronome", "mimic", "mirrormove"}:
            engine.add_log("|-fail|")
            return
        defender.encore_move_index = encore_move_index
        defender.encore_turns = random.randint(2, 6)
        engine.add_log(f"|-activate|{peer_side_id}a: {defender.nickname}|move: Encore")
        return

    if move_name_norm == "leechseed":
        if defender.substitute_hp > 0 or defender.leech_seed_recipient is not None:
            engine.add_log("|-fail|")
            return
        if "grass" in defender.types:
            engine.add_log("|-fail|")
            return
        defender.leech_seed_recipient = side_id
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Leech Seed")
        return

    if move_name_norm == "mimic":
        if defender.last_move_id is None:
            engine.add_log("|-fail|")
            return
        copied_move = _build_move_from_id(defender.last_move_id)
        if copied_move is None:
            engine.add_log("|-fail|")
            return
        copied_name = copied_move.name.lower().replace("-", "").replace(" ", "")
        if copied_name in {"struggle", "metronome", "mimic", "mirrormove"}:
            engine.add_log("|-fail|")
            return
        attacker.moves[move_index] = copied_move
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Mimic")
        return

    if move_name_norm == "spite":
        if defender.last_move_id is None:
            engine.add_log("|-fail|")
            return
        target_move_index = next((i for i, m in enumerate(defender.moves) if m.move_id == defender.last_move_id), None)
        if target_move_index is None:
            engine.add_log("|-fail|")
            return
        target_move = defender.moves[target_move_index]
        if target_move.pp <= 0:
            engine.add_log("|-fail|")
            return
        target_move.pp = max(0, target_move.pp - 4)
        engine.add_log(f"|-activate|{peer_side_id}a: {defender.nickname}|move: Spite")
        return

    if move_name_norm == "futuresight":
        peer_side = engine.sides[peer_side_id]
        if peer_side.future_sight_turns > 0:
            engine.add_log("|-fail|")
            return
        future_damage, _ = calculate_damage(
            attacker,
            defender,
            move,
            False,
            weather=engine.weather,
            defender_semi_invulnerable=defender.semi_invulnerable,
            attacking_side=engine.sides[side_id],
            defending_side=peer_side,
            random_factor=random.randint(85, 100),
        )
        peer_side.future_sight_turns = 2
        peer_side.future_sight_damage = max(0, future_damage)
        peer_side.future_sight_source_side = side_id
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Future Sight")
        return

    if move_name_norm == "helpinghand":
        if engine.format != "doubles":
            engine.add_log("|-fail|")
            return
        side = engine.sides[side_id]
        partner_slot_idx = next(
            (i for i, p_idx in enumerate(side.active_indices) if i != attacker_slot_idx and side.team[p_idx].current_hp > 0),
            None,
        )
        if partner_slot_idx is None:
            engine.add_log("|-fail|")
            return
        partner = side.team[side.active_indices[partner_slot_idx]]
        partner.helping_hand_turns = 1
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Helping Hand")
        return

    if move_name_norm == "followme":
        if engine.format != "doubles":
            engine.add_log("|-fail|")
            return
        attacker.follow_me_turns = 1
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Follow Me")
        return

    if move_name_norm == "snatch":
        if engine.format != "doubles":
            engine.add_log("|-fail|")
            return
        attacker.snatch_turns = 1
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Snatch")
        return

    if move_name_norm == "stockpile":
        if attacker.stockpile_count >= 3:
            engine.add_log("|-fail|")
            return
        attacker.stockpile_count += 1
        _apply_stat_boost(engine, attacker, side_id, "def", 1)
        _apply_stat_boost(engine, attacker, side_id, "spd", 1)
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Stockpile")
        return

    if move_name_norm == "swallow":
        if attacker.stockpile_count <= 0:
            engine.add_log("|-fail|")
            return
        stockpiles = max(1, min(3, attacker.stockpile_count))
        heal_ratio = {1: 0.25, 2: 0.5, 3: 1.0}[stockpiles]
        heal = max(1, math.floor(attacker.max_hp * heal_ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)
        attacker.stockpile_count = 0
        engine.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] move: Swallow")
        return

    if move_name_norm == "spitup":
        if attacker.stockpile_count <= 0:
            engine.add_log("|-fail|")
            return
        attacker.stockpile_count = 0
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Spit Up")
        return

    if move_name_norm == "wish":
        side = engine.sides[side_id]
        side.wish_turns[attacker_slot_idx] = 2
        side.wish_amounts[attacker_slot_idx] = max(1, math.floor(attacker.max_hp / 2))
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Wish")
        return

    if move_name_norm == "yawn":
        if defender.status_condition is not None or defender.yawn_turns > 0:
            engine.add_log("|-fail|")
            return
        defender.yawn_turns = 2
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Yawn")
        return

    if move_name_norm == "ingrain":
        if attacker.ingrain:
            engine.add_log("|-fail|")
            return
        attacker.ingrain = True
        engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: Ingrain")
        return

    if move_name_norm == "meanlook":
        if defender.trapped_by_side is not None or defender.ingrain:
            engine.add_log("|-fail|")
            return
        defender.trapped_by_side = side_id
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Mean Look")
        return

    if move_name_norm in {"lockon", "mindreader"}:
        attacker.lock_on_turns = 1
        engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: {move.name}")
        return

    if move_name_norm == "nightmare":
        if defender.status_condition != "slp" or defender.nightmare_active:
            engine.add_log("|-fail|")
            return
        defender.nightmare_active = True
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Nightmare")
        return

    if move_name_norm == "torment":
        if defender.torment_turns > 0 or defender.last_move_id is None:
            engine.add_log("|-fail|")
            return
        defender.torment_turns = random.randint(2, 5)
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Torment")
        return

    if move_name_norm == "roleplay":
        if not defender.ability:
            engine.add_log("|-fail|")
            return
        attacker.ability = defender.ability
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Role Play")
        return

    if move_name_norm == "skillswap":
        attacker.ability, defender.ability = defender.ability, attacker.ability
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Skill Swap")
        return

    if move_name_norm == "conversion":
        candidate_types = list(dict.fromkeys(move.type for move in attacker.moves if move.type))
        if not candidate_types:
            engine.add_log("|-fail|")
            return
        attacker.types = [random.choice(candidate_types)]
        engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: Conversion")
        return

    if move_name_norm == "conversion2":
        last_move_type = defender.last_damage_move_type
        if not last_move_type:
            engine.add_log("|-fail|")
            return
        candidate_types = [
            type_name
            for type_name in TYPE_CHART.keys()
            if get_type_multiplier(type_name, [last_move_type]) <= 0.5
        ]
        if not candidate_types:
            engine.add_log("|-fail|")
            return
        attacker.types = [random.choice(candidate_types)]
        engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: Conversion 2")
        return

    if move_name_norm == "curse":
        if "ghost" in attacker.types:
            if defender.curse_active:
                engine.add_log("|-fail|")
                return
            attacker.current_hp = max(1, attacker.current_hp - max(1, math.floor(attacker.max_hp / 2)))
            defender.curse_active = True
            engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: Curse")
            return
        _apply_stat_boost(engine, attacker, side_id, "atk", 1)
        _apply_stat_boost(engine, attacker, side_id, "def", 1)
        _apply_stat_drop(engine, attacker, side_id, "spe", 1)
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Curse")
        return

    if move_name_norm == "bellydrum":
        if attacker.current_hp <= max(1, attacker.max_hp // 2):
            engine.add_log("|-fail|")
            return
        attacker.current_hp = max(1, attacker.current_hp - max(1, attacker.max_hp // 2))
        attacker.stat_stages["atk"] = 6
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Belly Drum")
        engine.add_log(f"|-boost|{side_id}a: {attacker.nickname}|atk|6")
        return

    if move_name_norm == "transform":
        attacker.types = list(defender.types)
        attacker.ability = defender.ability
        attacker.stats = deepcopy(defender.stats)
        attacker.stat_stages = defender.stat_stages.copy()
        attacker.moves = deepcopy(defender.moves)
        engine.add_log(f"|-transform|{side_id}a: {attacker.nickname}|{peer_side_id}a: {defender.nickname}")
        return

    if move_name_norm == "uproar":
        if attacker.uproar_turns <= 0:
            attacker.uproar_turns = random.randint(2, 5)
            attacker.locked_move_index = move_index
        engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: Uproar")
        return

    if move_name_norm in {"growth", "calmmind", "bulkup", "dragondance", "meditate", "harden", "amnesia", "agility", "defensecurl", "cosmicpower"}:
        if move_name_norm == "growth":
            _apply_stat_boost(engine, attacker, side_id, "atk", 1)
            _apply_stat_boost(engine, attacker, side_id, "spa", 1)
        elif move_name_norm == "calmmind":
            _apply_stat_boost(engine, attacker, side_id, "spa", 1)
            _apply_stat_boost(engine, attacker, side_id, "spd", 1)
        elif move_name_norm == "bulkup":
            _apply_stat_boost(engine, attacker, side_id, "atk", 1)
            _apply_stat_boost(engine, attacker, side_id, "def", 1)
        elif move_name_norm == "dragondance":
            _apply_stat_boost(engine, attacker, side_id, "atk", 1)
            _apply_stat_boost(engine, attacker, side_id, "spe", 1)
        elif move_name_norm == "meditate":
            _apply_stat_boost(engine, attacker, side_id, "atk", 1)
        elif move_name_norm == "harden":
            _apply_stat_boost(engine, attacker, side_id, "def", 1)
        elif move_name_norm == "amnesia":
            _apply_stat_boost(engine, attacker, side_id, "spd", 2)
        elif move_name_norm == "agility":
            _apply_stat_boost(engine, attacker, side_id, "spe", 2)
        elif move_name_norm == "defensecurl":
            _apply_stat_boost(engine, attacker, side_id, "def", 1)
        elif move_name_norm == "cosmicpower":
            _apply_stat_boost(engine, attacker, side_id, "def", 1)
            _apply_stat_boost(engine, attacker, side_id, "spd", 1)
        engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|{move.name}")
        return

    if "user's attack and special attack by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "atk", 1)
        _apply_stat_boost(engine, attacker, side_id, "spa", 1)
        return
    if "user's special attack and special defense by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "spa", 1)
        _apply_stat_boost(engine, attacker, side_id, "spd", 1)
        return
    if "user's attack and defense by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "atk", 1)
        _apply_stat_boost(engine, attacker, side_id, "def", 1)
        return
    if "user's attack and speed by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "atk", 1)
        _apply_stat_boost(engine, attacker, side_id, "spe", 1)
        return
    if "user's attack by two stages" in effect:
        _apply_stat_boost(engine, attacker, side_id, "atk", 2)
        return
    if "user's defense by two stages" in effect:
        _apply_stat_boost(engine, attacker, side_id, "def", 2)
        return
    if "user's defense by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "def", 1)
        return
    if "user's special attack by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "spa", 1)
        return
    if "user's special defense by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "spd", 1)
        return
    if "user's speed by two stages" in effect:
        _apply_stat_boost(engine, attacker, side_id, "spe", 2)
        return
    if "user's speed by one stage" in effect:
        _apply_stat_boost(engine, attacker, side_id, "spe", 1)
        return
    if "all of the user's stats by one stage" in effect:
        for stat_name in ("atk", "def", "spa", "spd", "spe"):
            _apply_stat_boost(engine, attacker, side_id, stat_name, 1)
        return
    if "target's attack by two stages" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "atk", 2)
        return
    if "target's attack by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "atk", 1)
        return
    if "target's defense by two stages" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "def", 2)
        return
    if "target's defense by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "def", 1)
        return
    if "target's special attack by two stages" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "spa", 2)
        return
    if "target's special attack by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "spa", 1)
        return
    if "target's special defense by two stages" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "spd", 2)
        return
    if "target's special defense by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "spd", 1)
        return
    if "target's speed by two stages" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "spe", 2)
        return
    if "target's speed by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "spe", 1)
        return
    if "target's accuracy by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "accuracy", 1)
        return
    if "target's evasion by one stage" in effect:
        _apply_stat_drop(engine, defender, peer_side_id, "evasion", 1)
        return
    if "all of the target's stats by one stage" in effect:
        for stat_name in ("atk", "def", "spa", "spd", "spe"):
            _apply_stat_drop(engine, defender, peer_side_id, stat_name, 1)
        return

    # Task 8.4: Bide (ID 117 ou 20 em testes)
    if move.move_id == 117 or move.move_id == 20:
        if attacker.bide_turns is None:
            attacker.bide_turns = 2
            attacker.bide_damage = 0
            attacker.locked_move_index = move_index
            attacker.bide_target_side = None
            attacker.bide_target_slot = None
            engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|Bide")
        elif attacker.bide_turns > 1: # Turno 1 de espera (2 -> 1)
            attacker.bide_turns -= 1
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{side_id}a|[still]")
            engine.add_log(f"|message|{attacker.nickname} is storing energy!")
        else: # Turno final de liberação
            dmg = attacker.bide_damage * 2
            attacker.bide_turns = None
            attacker.locked_move_index = None
            target_to_hit = _pokemon_at_slot(engine, attacker.bide_target_side or peer_side_id, attacker.bide_target_slot)
            target_side_id = attacker.bide_target_side or peer_side_id
            target_slot_idx = attacker.bide_target_slot if attacker.bide_target_slot is not None else 0
            if target_to_hit is None or target_to_hit.current_hp <= 0:
                target_to_hit = defender if defender.current_hp > 0 else None
                target_side_id = peer_side_id
                target_slot_idx = engine._active_slot_for_pokemon(peer_side_id, target_to_hit) if target_to_hit else 0
            if target_to_hit is None or dmg <= 0:
                engine.add_log("|-fail|")
                attacker.bide_target_side = None
                attacker.bide_target_slot = None
                return
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{target_side_id}{chr(97 + target_slot_idx)}")
            _apply_reactive_damage(
                engine,
                side_id,
                attacker_slot_idx,
                target_side_id,
                target_slot_idx,
                target_to_hit,
                move,
                dmg,
                "physical",
            )
            attacker.bide_target_side = None
            attacker.bide_target_slot = None
        return

    # 0. Efeitos Secundarios e status puros (ex: Thunderbolt, Thunder Wave)
    if defender.current_hp > 0 and (damage > 0 or move.damage_class == "status"):
        apply_status = False
        apply_volatile = False

        if move.effect_chance:
            chance = move.effect_chance / 100.0
            apply_status = random.random() < chance
            apply_volatile = random.random() < chance
        elif move.damage_class == "status":
            apply_status = True
            apply_volatile = True

        if move_name_norm == "fakeout":
            apply_volatile = True

        if defender.ability == "shield-dust" and move.damage_class != "status":
            apply_status = False
            apply_volatile = False

        if apply_status:
            if "paralyze" in effect:
                engine.set_status(defender, "par", peer_side_id, attacker)
            elif "burn" in effect:
                engine.set_status(defender, "brn", peer_side_id, attacker)
            elif "freeze" in effect:
                engine.set_status(defender, "frz", peer_side_id, attacker)
            elif move_name_norm == "toxic":
                engine.set_status(defender, "tox", peer_side_id, attacker)
            elif "poison" in effect:
                engine.set_status(defender, "psn", peer_side_id, attacker)
            elif "sleep" in effect:
                engine.set_status(defender, "slp", peer_side_id, attacker)

        # Task 7.1: Efeitos Volateis baseados em Chance
        if apply_volatile:
            if "confusion" in effect and defender.confusion_turns == 0 and defender.ability != "own-tempo":
                defender.confusion_turns = random.randint(2, 5)
                engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|confusion")
            elif "flinch" in effect:
                if defender.ability == "inner-focus":
                    engine.add_log(f"|-ability|{peer_side_id}a: {defender.nickname}|Inner Focus")
                else:
                    defender.is_flinching = True

    if move_name_norm in {"whirlpool", "firespin", "wrap", "clamp", "sandtomb"} and damage > 0 and defender.current_hp > 0:
        defender.trapped_by_side = side_id
        defender.partial_trap_name = move.name
        defender.partial_trap_turns = random.randint(2, 5)
        engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|move: {move.name}")

    apply_on_damage_ability_effects(engine, attacker, defender, move, damage, side_id, peer_side_id)

    if move_name_norm in {"selfdestruct", "explosion"} and attacker.current_hp > 0:
        attacker.current_hp = 0
        engine.add_log(f"|faint|{side_id}a: {attacker.nickname}")

    # 1. Recoil (Dano de recuo)
    if "user receives" in effect and "damage" in effect:
        recoil_percent = 0.0
        if "1/4" in effect: recoil_percent = 0.25
        elif "1/3" in effect: recoil_percent = 0.33
        elif "1/2" in effect: recoil_percent = 0.5
        
        if recoil_percent > 0:
            recoil_damage = max(1, math.floor(damage * recoil_percent))
            attacker.current_hp = max(0, attacker.current_hp - recoil_damage)
            engine.add_log(f"|-damage|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] recoil")
            if attacker.current_hp <= 0:
                engine.add_log(f"|faint|{side_id}a: {attacker.nickname}")

    # Task 8.8: Recharge moves
    if "user foregoes its next turn to recharge" in effect:
        attacker.must_recharge = True

    # Task 8.8: Rage moves
    if "hits every turn for 2-3 turns" in effect:
        if attacker.rage_turns == 0:
            attacker.rage_turns = random.randint(2, 3)
            attacker.locked_move_index = move_index
            engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: {move.name}")

    if move_name_norm == "furycutter":
        if damage > 0:
            attacker.fury_cutter_hits = min(4, attacker.fury_cutter_hits + 1)
        else:
            attacker.fury_cutter_hits = 0

    if move_name_norm == "rollout":
        if damage > 0:
            attacker.rollout_turns = min(4, attacker.rollout_turns + 1)
        else:
            attacker.rollout_turns = 0

    if move_name_norm == "rapidspin" and damage > 0:
        attacker.partial_trap_turns = 0
        attacker.partial_trap_name = None
        attacker.trapped_by_side = None
        engine.sides[side_id].spikes_layers = 0
        if attacker.leech_seed_recipient is not None:
            attacker.leech_seed_recipient = None
        engine.add_log(f"|-clearnegativeboost|{side_id}a: {attacker.nickname}")

    # 2. Draining (Dreno de HP)
    if "recovers half the damage" in effect or "hp is restored by half" in effect or "drains half the damage" in effect:
        drain_amount = max(1, math.floor(damage / 2))
        # Liquid Ooze check
        if defender.ability == "liquid-ooze":
            attacker.current_hp = max(0, attacker.current_hp - drain_amount)
            engine.add_log(f"|-damage|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] ability: Liquid Ooze|[of] {peer_side_id}a: {defender.nickname}")
        else:
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + drain_amount)
            engine.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] drain|[of] {peer_side_id}a: {defender.nickname}")

    # 3. Stat Changes (Self)
    if move.damage_class == "status":
        if "raises user's attack by two stages" in effect:
            _apply_stat_boost(engine, attacker, side_id, "atk", 2)
        elif "raises user's defense by two stages" in effect:
            _apply_stat_boost(engine, attacker, side_id, "def", 2)
        elif "raises user's speed by two stages" in effect:
            _apply_stat_boost(engine, attacker, side_id, "spe", 2)
        elif "raises user's attack" in effect:
            _apply_stat_boost(engine, attacker, side_id, "atk", 1)
        elif move_name_norm == "swagger":
            _apply_stat_boost(engine, defender, peer_side_id, "atk", 2)
            if defender.confusion_turns == 0 and defender.ability != "own-tempo":
                defender.confusion_turns = random.randint(2, 5)
                engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|confusion")
        elif move_name_norm == "taunt":
            defender.taunt_turns = 3
            engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Taunt")
        
        # Task 8.1: Side Effects
        if "reflect" in move_name_norm:
            side = engine.sides[side_id]
            if side.reflect_turns == 0:
                side.reflect_turns = 5
                engine.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Reflect")
            else: engine.add_log("|-fail|")
        elif "lightscreen" in move_name_norm:
            side = engine.sides[side_id]
            if side.light_screen_turns == 0:
                side.light_screen_turns = 5
                engine.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Light Screen")
            else: engine.add_log("|-fail|")
        elif "safeguard" in move_name_norm:
            side = engine.sides[side_id]
            if side.safeguard_turns == 0:
                side.safeguard_turns = 5
                engine.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Safeguard")
            else: engine.add_log("|-fail|")
        elif "mist" in move_name_norm:
            side = engine.sides[side_id]
            if side.mist_turns == 0:
                side.mist_turns = 5
                engine.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Mist")
            else: engine.add_log("|-fail|")
        
        # Task 8.2: Baton Pass e Memento
        elif "batonpass" in move_name_norm:
            if engine.sides[side_id].has_available_pokemon(exclude_active=True):
                slot_idx = 0
                for i, idx in enumerate(engine.sides[side_id].active_indices):
                    if engine.sides[side_id].team[idx] == attacker:
                        slot_idx = i
                        break
                engine.baton_pass_slots[(side_id, slot_idx)] = {
                    "stat_stages": attacker.stat_stages.copy(),
                    "substitute_hp": attacker.substitute_hp,
                    "confusion_turns": attacker.confusion_turns,
                    "leech_seed_recipient": attacker.leech_seed_recipient,
                    "perish_song_turns": attacker.perish_song_turns,
                    "stockpile_count": attacker.stockpile_count,
                    "ingrain": attacker.ingrain,
                }
                engine.add_log(f"|move|{side_id}{chr(97 + slot_idx)}: {attacker.nickname}|Baton Pass|{side_id}{chr(97 + slot_idx)}")
            else: engine.add_log("|-fail|")
        elif "memento" in move_name_norm:
            if defender.current_hp > 0:
                attacker.current_hp = 0
                engine.add_log(f"|faint|{side_id}a: {attacker.nickname}")
                _apply_stat_drop(engine, defender, peer_side_id, "atk", 2)
                _apply_stat_drop(engine, defender, peer_side_id, "spa", 2)
            else: engine.add_log("|-fail|")
        
        # Task 8.3: Sacrificio
        elif "perishsong" in move_name_norm:
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Perish Song|{side_id}a")
            for s in engine.sides.values():
                for p_idx in s.active_indices:
                    p = s.team[p_idx]
                    if p.current_hp > 0 and p.perish_song_turns is None and p.ability != "soundproof":
                        p.perish_song_turns = 3
                        side_tag = "p1" if s == engine.sides["p1"] else "p2"
                        s_idx = s.active_indices.index(p_idx)
                        engine.add_log(f"|-start|{side_tag}{chr(97 + s_idx)}: {p.nickname}|perish3")
        elif "destinybond" in move_name_norm:
            attacker.destiny_bond = True
            engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Destiny Bond")

        # Task 8.4: Counters
        elif "counter" in move_name_norm:
            source_side_id = attacker.last_damage_source_side
            source_slot_idx = attacker.last_damage_source_slot
            if (
                attacker.last_damage_taken <= 0
                or attacker.last_damage_class != "physical"
                or source_side_id is None
                or source_slot_idx is None
            ):
                engine.add_log("|-fail|")
                return
            source_target = _pokemon_at_slot(engine, source_side_id, source_slot_idx)
            if source_target is None or source_target.current_hp <= 0 or source_side_id == side_id:
                engine.add_log("|-fail|")
                return
            target_to_hit = source_target
            target_side_id = source_side_id
            target_slot_idx = source_slot_idx
            if engine.format == "doubles":
                follow_me_target = next(
                    (
                        (idx, pokemon)
                        for idx, p_idx in enumerate(engine.sides[source_side_id].active_indices)
                        if (pokemon := engine.sides[source_side_id].team[p_idx]).current_hp > 0 and pokemon.follow_me_turns > 0
                    ),
                    None,
                )
                if follow_me_target is not None and follow_me_target[1] is not source_target:
                    target_slot_idx, target_to_hit = follow_me_target
            dmg = attacker.last_damage_taken * 2
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Counter|{target_side_id}{chr(97 + target_slot_idx)}")
            _apply_reactive_damage(
                engine,
                side_id,
                attacker_slot_idx,
                target_side_id,
                target_slot_idx,
                target_to_hit,
                move,
                dmg,
                "physical",
            )
            return
        elif "mirrorcoat" in move_name_norm:
            source_side_id = attacker.last_damage_source_side
            source_slot_idx = attacker.last_damage_source_slot
            if (
                attacker.last_damage_taken <= 0
                or attacker.last_damage_class != "special"
                or source_side_id is None
                or source_slot_idx is None
            ):
                engine.add_log("|-fail|")
                return
            source_target = _pokemon_at_slot(engine, source_side_id, source_slot_idx)
            if source_target is None or source_target.current_hp <= 0 or source_side_id == side_id:
                engine.add_log("|-fail|")
                return
            target_to_hit = source_target
            target_side_id = source_side_id
            target_slot_idx = source_slot_idx
            if engine.format == "doubles":
                follow_me_target = next(
                    (
                        (idx, pokemon)
                        for idx, p_idx in enumerate(engine.sides[source_side_id].active_indices)
                        if (pokemon := engine.sides[source_side_id].team[p_idx]).current_hp > 0 and pokemon.follow_me_turns > 0
                    ),
                    None,
                )
                if follow_me_target is not None and follow_me_target[1] is not source_target:
                    target_slot_idx, target_to_hit = follow_me_target
            dmg = attacker.last_damage_taken * 2
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Mirror Coat|{target_side_id}{chr(97 + target_slot_idx)}")
            _apply_reactive_damage(
                engine,
                side_id,
                attacker_slot_idx,
                target_side_id,
                target_slot_idx,
                target_to_hit,
                move,
                dmg,
                "special",
            )
            return

    # 4. Stat Changes (Target)
    if "lower" in effect and "stats" not in effect:
        if "lowers target's attack" in effect:
            _apply_stat_drop(engine, defender, peer_side_id, "atk", 1)
        elif "lowers target's defense" in effect:
            _apply_stat_drop(engine, defender, peer_side_id, "def", 1)

def _apply_stat_boost(engine, pokemon, side, stat, stages):
    changed = pokemon.modify_stage(stat, stages)
    if changed > 0:
        engine.add_log(f"|-boost|{side}a: {pokemon.nickname}|{stat}|{changed}")
    else: engine.add_log(f"|-notarget|{side}a: {pokemon.nickname}")

def _apply_stat_drop(engine, pokemon, side, stat, stages):
    # Task 9.1: Prevencao por Habilidades
    battle_side_id = side[:2]
    if engine.sides[battle_side_id].mist_turns > 0:
        engine.add_log(f"|-fail|{side}a: {pokemon.nickname}|mist")
        return
    if pokemon.ability in ["clear-body", "white-smoke"]:
        ability_name = pokemon.ability.replace("-", " ").title()
        engine.add_log(f"|-ability|{side}a: {pokemon.nickname}|{ability_name}")
        return
    if pokemon.ability == "keen-eye" and stat == "accuracy":
        engine.add_log(f"|-ability|{side}a: {pokemon.nickname}|Keen Eye")
        return
    if pokemon.ability == "hyper-cutter" and stat == "atk":
        engine.add_log(f"|-ability|{side}a: {pokemon.nickname}|Hyper Cutter")
        return

    changed = pokemon.modify_stage(stat, -stages)
    if changed < 0:
        engine.add_log(f"|-unboost|{side}a: {pokemon.nickname}|{stat}|{abs(changed)}")
    else: engine.add_log(f"|-notarget|{side}a: {pokemon.nickname}")
