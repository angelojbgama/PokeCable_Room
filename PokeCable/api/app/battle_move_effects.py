from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove
    from .battle_engine_core import CustomBattleEngine

def get_hit_count(move: BattleMove) -> int:
    """
    Retorna a quantidade de hits de um golpe (2, 3 ou 2-5).
    Segue as probabilidades da Gen 3.
    """
    effect = move.effect.lower()
    
    if "hits twice" in effect or "hits 2 times" in effect:
        return 2
    
    if "hits 2-5 times" in effect:
        r = random.random()
        if r < 0.375: return 2
        if r < 0.750: return 3
        if r < 0.875: return 4
        return 5
        
    if "hits 3 times" in effect: # Ex: Triple Kick (embora a logica dele seja unica, aqui simplificamos)
        return 3
        
    return 1

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
    effect = move.effect.lower()
    move_name_norm = move.name.lower().replace("-", "").replace(" ", "")
    peer_side_id = "p2" if side_id == "p1" else "p1"

    # Task 8.4: Bide (ID 117 ou 20 em testes)
    if move.move_id == 117 or move.move_id == 20:
        if attacker.bide_turns is None:
            attacker.bide_turns = 2
            attacker.bide_damage = 0
            attacker.locked_move_index = move_index
            engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|Bide")
        elif attacker.bide_turns > 1: # Turno 1 de espera (2 -> 1)
            attacker.bide_turns -= 1
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{side_id}a|[still]")
            engine.add_log(f"|message|{attacker.nickname} is storing energy!")
        else: # Turno final de liberação
            dmg = attacker.bide_damage * 2
            attacker.bide_turns = None
            attacker.locked_move_index = None
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{peer_side_id}a")
            target_to_hit = engine.sides[peer_side_id].active_list[0]
            if dmg > 0:
                target_to_hit.current_hp = max(0, target_to_hit.current_hp - dmg)
                engine.add_log(f"|damage|{peer_side_id}a: {target_to_hit.nickname}|{engine._condition(target_to_hit)}")
                if target_to_hit.current_hp <= 0: engine.add_log(f"|faint|{peer_side_id}a: {target_to_hit.nickname}")
            else:
                engine.add_log("|-fail|")
        return

    # 0. Efeitos Secundarios baseados em Chance (ex: Thunderbolt 10% Paralyze)
    if move.effect_chance and defender.current_hp > 0 and damage > 0:
        if random.random() < (move.effect_chance / 100.0):
            if "paralyze" in effect:
                engine.set_status(defender, "par", peer_side_id, attacker)
            elif "burn" in effect:
                engine.set_status(defender, "brn", peer_side_id, attacker)
            elif "freeze" in effect:
                engine.set_status(defender, "frz", peer_side_id, attacker)
            elif "poison" in effect:
                engine.set_status(defender, "psn", peer_side_id, attacker)
            elif "sleep" in effect:
                engine.set_status(defender, "slp", peer_side_id, attacker)

        # Task 7.1: Efeitos Volateis baseados em Chance
        if random.random() < (move.effect_chance / 100.0):
            if "confusion" in effect and defender.confusion_turns == 0:
                defender.confusion_turns = random.randint(2, 5)
                engine.add_log(f"|-start|{peer_side_id}a: {defender.nickname}|confusion")
            elif "flinch" in effect:
                defender.is_flinching = True

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

    # 2. Draining (Dreno de HP)
    if "recovers half the damage" in effect or "hp is restored by half" in effect:
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
                    "perish_song_turns": attacker.perish_song_turns
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
                    if p.current_hp > 0 and p.perish_song_turns is None:
                        p.perish_song_turns = 3
                        side_tag = "p1" if s == engine.sides["p1"] else "p2"
                        s_idx = s.active_indices.index(p_idx)
                        engine.add_log(f"|-start|{side_tag}{chr(97 + s_idx)}: {p.nickname}|perish3")
        elif "destinybond" in move_name_norm:
            attacker.destiny_bond = True
            engine.add_log(f"|-singlemove|{side_id}a: {attacker.nickname}|Destiny Bond")
        
        # Task 8.4: Counters
        elif "counter" in move_name_norm:
            if attacker.last_damage_taken > 0 and attacker.last_damage_class == "physical":
                dmg = attacker.last_damage_taken * 2
                defender.current_hp = max(0, defender.current_hp - dmg)
                engine.add_log(f"|damage|{peer_side_id}a: {defender.nickname}|{engine._condition(defender)}")
                if defender.current_hp <= 0: engine.add_log(f"|faint|{peer_side_id}a: {defender.nickname}")
            else: engine.add_log("|-fail|")
        elif "mirrorcoat" in move_name_norm:
            if attacker.last_damage_taken > 0 and attacker.last_damage_class == "special":
                dmg = attacker.last_damage_taken * 2
                defender.current_hp = max(0, defender.current_hp - dmg)
                engine.add_log(f"|damage|{peer_side_id}a: {defender.nickname}|{engine._condition(defender)}")
                if defender.current_hp <= 0: engine.add_log(f"|faint|{peer_side_id}a: {defender.nickname}")
            else: engine.add_log("|-fail|")
        
    # Task 8.4: Bide
    if "bide" in move_name_norm:
        if attacker.bide_turns is None:
            attacker.bide_turns = 2
            attacker.bide_damage = 0
            attacker.locked_move_index = move_index
            engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|Bide")
        elif attacker.bide_turns > 1: # Turno 1 de espera (2 -> 1)
            attacker.bide_turns -= 1
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{side_id}a|[still]")
            engine.add_log(f"|message|{attacker.nickname} is storing energy!")
        else: # Turno final de liberação
            dmg = attacker.bide_damage * 2
            attacker.bide_turns = None
            attacker.locked_move_index = None
            engine.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{peer_side_id}a")
            target_to_hit = engine.sides[peer_side_id].active_list[0]
            if dmg > 0:
                target_to_hit.current_hp = max(0, target_to_hit.current_hp - dmg)
                engine.add_log(f"|damage|{peer_side_id}a: {target_to_hit.nickname}|{engine._condition(target_to_hit)}")
                if target_to_hit.current_hp <= 0: engine.add_log(f"|faint|{peer_side_id}a: {target_to_hit.nickname}")
            else:
                engine.add_log("|-fail|")

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
    if pokemon.ability in ["clear-body", "white-smoke"]:
        ability_name = pokemon.ability.replace("-", " ").title()
        engine.add_log(f"|-ability|{side}a: {pokemon.nickname}|{ability_name}")
        return

    changed = pokemon.modify_stage(stat, -stages)
    if changed < 0:
        engine.add_log(f"|-unboost|{side}a: {pokemon.nickname}|{stat}|{abs(changed)}")
    else: engine.add_log(f"|-notarget|{side}a: {pokemon.nickname}")
