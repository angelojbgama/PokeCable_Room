#!/usr/bin/env python3
"""
Test script to verify backend /analyze-save endpoint
"""
import sys
import json
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)


def test_backend(save_file: str, backend_url: str = "https://9kernel.vps-kinghost.net"):
    """Test the backend /analyze-save endpoint"""

    save_path = Path(save_file)
    if not save_path.exists():
        print(f"ERROR: Save file not found: {save_file}")
        return False

    if not save_path.suffix.lower() in ['.sav', '.srm']:
        print(f"WARNING: File extension is {save_path.suffix}, expected .sav or .srm")

    print(f"\n{'='*60}")
    print(f"Backend Test")
    print(f"{'='*60}")
    print(f"Save file:  {save_path.name}")
    print(f"Size:       {save_path.stat().st_size} bytes")
    print(f"Backend:    {backend_url}")
    print(f"Endpoint:   {backend_url}/analyze-save")
    print(f"{'='*60}\n")

    try:
        analyze_url = f"{backend_url}/analyze-save"
        print(f"[1] Conectando ao backend...")

        with open(save_path, "rb") as f:
            files = {"file": (save_path.name, f)}
            print(f"[2] Enviando arquivo ({save_path.stat().st_size} bytes)...")

            response = requests.post(analyze_url, files=files, timeout=30)

        print(f"[3] Resposta: HTTP {response.status_code}\n")

        if response.status_code != 200:
            print(f"ERROR: Backend returned {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

        data = response.json()

        print(f"✓ Generation: {data.get('generation')}")
        print(f"✓ Game: {data.get('game')}")
        print(f"✓ Total Pokémon: {len(data.get('pokemon', []))}")
        print(f"  - Party: {len([p for p in data.get('pokemon', []) if p.get('source') == 'party'])}")
        print(f"  - Boxes: {len([p for p in data.get('pokemon', []) if p.get('source') == 'boxes'])}")

        if data.get('pokemon'):
            print(f"\n[Party Pokémon]")
            for p in data.get('pokemon', []):
                if p.get('source') == 'party':
                    print(f"  - {p.get('display_summary')} (Lv. {p.get('level')})")

            print(f"\n[First 5 Box Pokémon]")
            count = 0
            for p in data.get('pokemon', []):
                if p.get('source') == 'boxes' and count < 5:
                    print(f"  - {p.get('display_summary')} (Lv. {p.get('level')})")
                    count += 1

        print(f"\n{'='*60}")
        print(f"✓ Backend está funcionando corretamente!")
        print(f"{'='*60}\n")

        # Save full response for debugging
        debug_file = Path("/tmp/pokecable_backend_test.json")
        with open(debug_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Debug: Resposta completa salva em {debug_file}")

        return True

    except requests.ConnectionError as e:
        print(f"ERROR: Não conseguiu conectar ao backend")
        print(f"  {e}")
        print(f"\nVerifique:")
        print(f"  - Backend URL está correto?")
        print(f"  - Servidor está rodando?")
        print(f"  - Internet está funcionando?")
        return False
    except requests.Timeout:
        print(f"ERROR: Backend não respondeu em 30 segundos")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Backend retornou resposta inválida")
        print(f"  {e}")
        print(f"  Response: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 test_backend.py <save_file> [backend_url]")
        print("\nExemplos:")
        print("  python3 test_backend.py pokemon.sav")
        print("  python3 test_backend.py pokemon.srm https://9kernel.vps-kinghost.net")
        sys.exit(1)

    save_file = sys.argv[1]
    backend_url = sys.argv[2] if len(sys.argv) > 2 else "https://9kernel.vps-kinghost.net"

    success = test_backend(save_file, backend_url)
    sys.exit(0 if success else 1)
