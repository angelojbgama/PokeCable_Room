from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove
    from .battle_engine_core import CustomBattleEngine

from .battle_move_properties import move_makes_contact, normalize_move_name

WEATHER_SUPPRESSING_ABILITIES = {"air-lock", "cloud-nine"}

CRITICAL_IMMUNITY_ABILITIES = {"battle-armor", "shell-armor"}

STATUS_IMMUNITY_ABILITIES: dict[str, set[str]] = {
    "slp": {"insomnia", "vital-spirit"},
    "par": {"limber"},
    "psn": {"immunity"},
    "tox": {"immunity"},
    "brn": {"water-veil"},
    "frz": {"magma-armor"},
}

VOLATILE_IMMUNITY_ABILITIES: dict[str, set[str]] = {
    "confusion": {"own-tempo"},
    "attract": {"oblivious"},
}

SOUNDPROOF_BLOCKED_MOVES = {
    "growl",
    "roar",
    "sing",
    "supersonic",
    "screech",
    "snore",
    "uproar",
    "metalsound",
    "grasswhistle",
    "hypervoice",
}


def is_weather_suppressed(ability: str | None) -> bool:
    return bool(ability and ability in WEATHER_SUPPRESSING_ABILITIES)


def is_status_immune(ability: str | None, status: str) -> bool:
    return bool(ability and ability in STATUS_IMMUNITY_ABILITIES.get(status, set()))


def is_volatile_immune(ability: str | None, volatile_name: str) -> bool:
    return bool(ability and ability in VOLATILE_IMMUNITY_ABILITIES.get(volatile_name, set()))


def blocks_soundproof(move: BattleMove) -> bool:
    """Retorna True se Soundproof deve anular o golpe."""
    move_name_norm = normalize_move_name(move.name)
    return move_name_norm in SOUNDPROOF_BLOCKED_MOVES


def blocks_critical_hits(ability: str | None) -> bool:
    return bool(ability and ability in CRITICAL_IMMUNITY_ABILITIES)

def apply_ability_immunities(move: BattleMove, defender: BattlePokemon, type_multiplier: float) -> float | None:
    """
    Retorna o novo multiplicador de dano se a habilidade conferir imunidade.
    Retorna None se a habilidade nao afetar este golpe.
    """
    ability = defender.ability
    move_type = move.type
    
    if not ability:
        return None
        
    # Gen 3 Immunities
    if ability == "levitate" and move_type == "ground":
        return 0.0
        
    if ability == "flash-fire" and move_type == "fire":
        return 0.0
        
    if ability == "water-absorb" and move_type == "water":
        return 0.0
        
    if ability == "volt-absorb" and move_type == "electric":
        return 0.0
        
    if ability == "wonder-guard" and move.power > 0:
        # Imune a tudo que NAO seja Super Effective
        if type_multiplier <= 1.0:
            return 0.0

    return None


def apply_on_damage_ability_effects(
    engine: "CustomBattleEngine",
    attacker: BattlePokemon,
    defender: BattlePokemon,
    move: BattleMove,
    damage: int,
    side_id: str,
    peer_side_id: str,
) -> None:
    """Aplica habilidades que disparam apos o dano ser resolvido."""
    if damage <= 0:
        return

    move_name_norm = normalize_move_name(move.name)

    if defender.ability == "color-change" and move.power > 0 and move_name_norm != "struggle" and defender.current_hp > 0:
        defender.types = [move.type]
        engine.add_log(f"|-singlemove|{peer_side_id}a: {defender.nickname}|Color Change")

    if not move_makes_contact(move):
        return

    if defender.ability == "rough-skin":
        recoil = max(1, attacker.max_hp // 16)
        attacker.current_hp = max(0, attacker.current_hp - recoil)
        engine.add_log(f"|-damage|{side_id}a: {attacker.nickname}|{engine._condition(attacker)}|[from] ability: Rough Skin")
        if attacker.current_hp <= 0:
            engine.add_log(f"|faint|{side_id}a: {attacker.nickname}")
        return

    if defender.ability == "static" and attacker.current_hp > 0:
        if random.randint(1, 3) == 1:
            engine.set_status(attacker, "par", side_id, defender)
        return

    if defender.ability == "poison-point" and attacker.current_hp > 0:
        if random.randint(1, 3) == 1:
            engine.set_status(attacker, "psn", side_id, defender)
        return

    if defender.ability == "flame-body" and attacker.current_hp > 0:
        if random.randint(1, 3) == 1:
            engine.set_status(attacker, "brn", side_id, defender)
        return

    if defender.ability == "effect-spore" and attacker.current_hp > 0:
        if random.randint(1, 10) == 1:
            effect = random.choice(["slp", "psn", "par"])
            engine.set_status(attacker, effect, side_id, defender)
        return

    if defender.ability == "cute-charm" and attacker.current_hp > 0 and attacker.ability != "oblivious":
        attacker_gender = str(attacker.gender or "").lower()
        defender_gender = str(defender.gender or "").lower()
        if attacker_gender and defender_gender and attacker_gender != defender_gender:
            if attacker_gender not in {"genderless", "none", ""} and defender_gender not in {"genderless", "none", ""}:
                if random.randint(1, 3) == 1:
                    attacker.attracted_to_side = peer_side_id
                    engine.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: Attract|[from] ability: Cute Charm")
