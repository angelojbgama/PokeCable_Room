from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Adiciona o backend ao path para importar os parsers reais
BACKEND_PATH = str(Path(__file__).parent.parent.parent / "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from app.main import app
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser

SAVE_ROOT = Path(__file__).parent.parent.parent.parent / "save"

def get_save_path(relative: str) -> Path:
    path = SAVE_ROOT / relative
    if not path.exists():
        pytest.skip(f"Save real ausente: {path}")
    return path

class TestE2ERealSaves:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def simulate_trade(self, room_name: str, player_a_data: dict, player_b_data: dict):
        """
        Orquestra uma troca completa entre dois WebSockets.
        """
        import time
        with self.client.websocket_connect("/ws") as ws_a, \
             self.client.websocket_connect("/ws") as ws_b:
            
            # 1. Join Room Player A (Create)
            print(f"\n[Test] Player A creating {room_name}")
            ws_a.send_json({
                "type": "create_room",
                "room_name": room_name,
                "password": "test-password",
                "player_name": player_a_data["name"],
                "generation": player_a_data["generation"],
                "game": player_a_data["game"]
            })
            
            # Pequeno delay para garantir criacao
            time.sleep(0.1)

            # 2. Join Room Player B (Join)
            print(f"[Test] Player B joining {room_name}")
            ws_b.send_json({
                "type": "join_room",
                "room_name": room_name,
                "password": "test-password",
                "player_name": player_b_data["name"],
                "generation": player_b_data["generation"],
                "game": player_b_data["game"]
            })

            # Consome mensagens de ambos ate room_ready
            def wait_for_ready():
                ready_a = False
                ready_b = False
                for _ in range(30):
                    # Intercala leituras
                    if not ready_a:
                        m = ws_a.receive_json()
                        print(f"[Test] Player A received: {m['type']}")
                        if m["type"] == "room_ready": ready_a = True
                        if m["type"] == "error": pytest.fail(f"A error: {m.get('message')}")
                    if not ready_b:
                        m = ws_b.receive_json()
                        print(f"[Test] Player B received: {m['type']}")
                        if m["type"] == "room_ready": ready_b = True
                        if m["type"] == "error": pytest.fail(f"B error: {m.get('message')}")
                    if ready_a and ready_b:
                        return True
                return False

            assert wait_for_ready(), "Room never became ready for both players"

            # 3. Enviar Ofertas
            print("[Test] Sending offers...")
            ws_a.send_json({"type": "send_trade_offer", "payload": player_a_data["payload"]})
            ws_b.send_json({"type": "send_trade_offer", "payload": player_b_data["payload"]})

            # Receber as ofertas (peer_offered)
            def wait_for_offers():
                offered_a = False
                offered_b = False
                for _ in range(20):
                    if not offered_a:
                        m = ws_a.receive_json()
                        print(f"[Test] Player A received: {m['type']}")
                        if m["type"] == "peer_offered": offered_a = True
                    if not offered_b:
                        m = ws_b.receive_json()
                        print(f"[Test] Player B received: {m['type']}")
                        if m["type"] == "peer_offered": offered_b = True
                    if offered_a and offered_b:
                        return True
                return False

            assert wait_for_offers()

            # 4. Confirmar Troca
            print("[Test] Confirming trade...")
            ws_a.send_json({"type": "confirm_trade"})
            ws_b.send_json({"type": "confirm_trade"})

            # 5. Finalizar (trade_completed)
            final_payload_a = None
            final_payload_b = None
            for _ in range(20):
                if not final_payload_a:
                    m = ws_a.receive_json()
                    print(f"[Test] Player A received: {m['type']}")
                    if m["type"] == "trade_completed": final_payload_a = m["payload"]
                if not final_payload_b:
                    m = ws_b.receive_json()
                    print(f"[Test] Player B received: {m['type']}")
                    if m["type"] == "trade_completed": final_payload_b = m["payload"]
                if final_payload_a and final_payload_b:
                    break
            
            assert final_payload_a is not None
            assert final_payload_b is not None
            
            print("[Test] Trade completed successfully!")
            return final_payload_a, final_payload_b

    def test_e2e_gen2_to_gen2_real_saves(self):
        """Troca entre Crystal e Silver (Same Gen)"""
        crystal_path = get_save_path("gen 2/Pokémon - Crystal Version.sav")
        silver_path = get_save_path("gen 2/Pokémon - Silver Version.sav")
        
        p_crystal = Gen2Parser()
        p_crystal.load(crystal_path)
        
        p_silver = Gen2Parser()
        p_silver.load(silver_path)
        
        # Prepara dados Player A (Crystal)
        payload_a = p_crystal.export_pokemon("party:0").to_dict()
        data_a = {
            "name": p_crystal.get_player_name(),
            "generation": 2,
            "game": "pokemon_crystal",
            "payload": payload_a
        }
        
        # Prepara dados Player B (Silver)
        payload_b = p_silver.export_pokemon("party:0").to_dict()
        data_b = {
            "name": p_silver.get_player_name(),
            "generation": 2,
            "game": "pokemon_silver",
            "payload": payload_b
        }
        
        received_by_a, received_by_b = self.simulate_trade("room-gen2", data_a, data_b)
        
        # Valida se os parsers aceitam o que foi recebido
        # Player A (Crystal) recebe o que Player B (Silver) enviou
        p_crystal.import_pokemon("party:0", received_by_a)
        assert p_crystal.validate()
        
        # Player B (Silver) recebe o que Player A (Crystal) enviou
        p_silver.import_pokemon("party:0", received_by_b)
        assert p_silver.validate()

    def test_e2e_gen1_to_gen3_real_saves(self):
        """Troca entre Yellow (Gen 1) e Ruby (Gen 3) (Cross Gen)"""
        yellow_path = get_save_path("gen 1/Pokémon - Yellow Version.sav")
        ruby_path = get_save_path("gen 3/Pokémon - Ruby Version.sav")
        
        p_yellow = Gen1Parser()
        p_yellow.load(yellow_path)
        
        p_ruby = Gen3Parser()
        p_ruby.load(ruby_path)
        
        # Prepara Player A (Gen 1)
        # Gen 1 envia canonical para Gen 3
        payload_a = p_yellow.export_canonical("party:0").to_dict()
        data_a = {
            "name": p_yellow.get_player_name(),
            "generation": 1,
            "game": "pokemon_yellow",
            "payload": payload_a
        }
        
        # Prepara Player B (Gen 3)
        # Gen 3 envia canonical para Gen 1
        payload_b = p_ruby.export_canonical("party:0").to_dict()
        data_b = {
            "name": p_ruby.get_player_name(),
            "generation": 3,
            "game": "pokemon_ruby",
            "payload": payload_b
        }
        
        received_by_a, received_by_b = self.simulate_trade("room-cross", data_a, data_b)
        
        # Gen 1 aplica o que recebeu da Gen 3 (via Canonical)
        # Nota: O parser do backend lida com a conversão se usarmos o converter adequado, 
        # mas aqui testamos se o payload retornado pelo servidor é válido para importação cross-gen.
        # No client real (R36S), o converter é chamado antes do import_pokemon.
        from pokecable_room.converters import get_converter
        
        # Jogador A (Gen 1) converte o payload canônico recebido para sua Gen 1
        conv_3_to_1 = get_converter(3, 1)
        conv_3_to_1.apply_to_save(p_yellow, "party:0", received_by_a)
        assert p_yellow.validate()
        
        # Jogador B (Gen 3) converte o payload canônico recebido para sua Gen 3
        conv_1_to_3 = get_converter(1, 3)
        conv_1_to_3.apply_to_save(p_ruby, "party:0", received_by_b)
        assert p_ruby.validate()
