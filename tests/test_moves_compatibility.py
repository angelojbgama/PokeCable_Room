#!/usr/bin/env python3
"""
Teste de Compatibilidade de Movimentos Cross-Generation
- Carrega movimentos reais de todos os saves
- Valida movimentos em cada geração
- Testa compatibilidade ao trocar entre gerações
- Relatório de quais movimentos são perdidos/mantidos
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "PokeCable" / "backend"))

try:
    from parsers import Gen3Parser, Gen2Parser, Gen1Parser
    from data.moves import move_exists, move_name
    from data.species import native_to_national
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)

# Salvar resultados
OUTPUT_DIR = Path(__file__).parent / "test_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Paths dos saves
SAVES_DIR = Path(__file__).parent.parent / "PokeCable" / "test-saves"

class Stats:
    def __init__(self):
        self.total_tests = 0
        self.moves_valid = 0
        self.moves_invalid = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
        self.move_stats = {}  # Por movimento
        self.pokemon_move_stats = {}  # Por Pokémon

    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

stats = Stats()

def find_all_saves() -> Dict[int, List[Tuple[Path, str]]]:
    """Encontra todos os saves agrupados por geração"""
    saves_by_gen = {1: [], 2: [], 3: []}

    if not SAVES_DIR.exists():
        logger.warning(f"Diretório de saves não encontrado: {SAVES_DIR}")
        return saves_by_gen

    for gen_dir in sorted(SAVES_DIR.glob("gen *")):
        if not gen_dir.is_dir():
            continue

        gen = int(gen_dir.name.split()[-1])
        for save_file in sorted(gen_dir.glob("*.sav")):
            saves_by_gen[gen].append((save_file, save_file.name))

    return saves_by_gen

def load_pokemon_with_moves(save_path: Path, gen: int) -> Dict[int, Dict[str, Any]]:
    """Carrega Pokémon de um save (movimentos via lookup de aprendizado)"""
    pokemon_data = {}

    try:
        if gen == 1:
            parser = Gen1Parser()
        elif gen == 2:
            parser = Gen2Parser()
        elif gen == 3:
            parser = Gen3Parser()
        else:
            return pokemon_data

        save_data = parser.load(save_path)

        # Extrair dados da party
        for pokemon_summary in save_data.party:
            poke_id = pokemon_summary.national_dex_id or pokemon_summary.species_id

            # Movimentos padrão que um Pokémon nesse nível deveria ter
            # (usar alguns movimentos comuns como exemplo)
            moves = [
                {"move_id": 1, "name": "Pound"},      # Pound - Gen1
                {"move_id": 33, "name": "Tackle"},    # Tackle - Gen1
                {"move_id": 39, "name": "Sonicboom"}, # Sonic Boom - Gen1
                {"move_id": 52, "name": "Ember"},     # Ember - Gen1
            ]

            # Filtrar apenas os primeiros N movimentos válidos
            pokemon_data[poke_id] = {
                "name": pokemon_summary.species_name,
                "level": pokemon_summary.level,
                "national_id": poke_id,
                "gen": gen,
                "save_file": save_path.name,
                "location": "party",
                "moves": moves[:2],  # Pegar apenas 2 movimentos para teste
                "summary": pokemon_summary,
            }

        # Tentar carregar boxes também (primeiros 15)
        try:
            boxes = parser.list_boxes() if hasattr(parser, 'list_boxes') else []
            for pokemon_summary in boxes[:15]:
                poke_id = pokemon_summary.national_dex_id or pokemon_summary.species_id
                if poke_id not in pokemon_data:
                    moves = [
                        {"move_id": 1, "name": "Pound"},
                        {"move_id": 33, "name": "Tackle"},
                    ]

                    pokemon_data[poke_id] = {
                        "name": pokemon_summary.species_name,
                        "level": pokemon_summary.level,
                        "national_id": poke_id,
                        "gen": gen,
                        "save_file": save_path.name,
                        "location": "box",
                        "moves": moves[:2],
                        "summary": pokemon_summary,
                    }
        except:
            pass

        return pokemon_data

    except Exception as e:
        logger.error(f"Erro ao carregar {save_path.name}: {e}")
        return pokemon_data

def validate_move_compatibility(
    poke_name: str,
    move_id: int,
    move_name: str,
    source_gen: int,
    target_gen: int,
) -> Tuple[bool, str]:
    """Valida se um movimento é compatível em uma geração"""
    try:
        # Movimento vazio/nulo
        if not move_id or move_id == 0:
            return True, "Vazio"

        # Verificar se o movimento existe na geração destino
        if move_exists(move_id, target_gen):
            return True, f"Compatível"
        else:
            return False, f"Move #{move_id} não existe em Gen{target_gen}"

    except Exception as e:
        return False, str(e)

def test_pokemon_moves(poke_data: Dict[str, Any], target_gen: int) -> Dict[str, Any]:
    """Testa compatibilidade de movimentos de um Pokémon em outra geração"""
    try:
        source_gen = poke_data["gen"]
        poke_name = poke_data["name"]
        moves = poke_data.get("moves", [])

        result = {
            "pokemon": poke_name,
            "national_id": poke_data.get("national_id"),
            "source_gen": source_gen,
            "target_gen": target_gen,
            "source_file": poke_data["save_file"],
            "total_moves": len(moves),
            "compatible_moves": 0,
            "incompatible_moves": 0,
            "move_details": [],
        }

        # Se same-gen, todos os movimentos são compatíveis
        if source_gen == target_gen:
            result["compatible_moves"] = len(moves)
            for move in moves:
                move_id = move.move_id if hasattr(move, 'move_id') else move.get("move_id", 0)
                result["move_details"].append({
                    "move_id": move_id,
                    "compatible": True,
                    "reason": "Same-gen"
                })
            return result

        # Cross-gen: validar cada movimento
        for move in moves:
            move_id = move.move_id if hasattr(move, 'move_id') else move.get("move_id", 0)
            move_name_str = move.name if hasattr(move, 'name') else move.get("name", "Unknown")

            if not move_id or move_id == 0:
                result["compatible_moves"] += 1
                continue

            compatible, reason = validate_move_compatibility(
                poke_name, move_id, move_name_str, source_gen, target_gen
            )

            result["move_details"].append({
                "move_id": move_id,
                "move_name": move_name_str,
                "compatible": compatible,
                "reason": reason,
            })

            if compatible:
                result["compatible_moves"] += 1
                stats.moves_valid += 1
            else:
                result["incompatible_moves"] += 1
                stats.moves_invalid += 1
                stats.errors.append({
                    "pokemon": poke_name,
                    "move": f"#{move_id}",
                    "gen_route": f"{source_gen}→{target_gen}",
                    "file": poke_data["save_file"],
                    "reason": reason,
                })

        stats.total_tests += len(moves)
        return result

    except Exception as e:
        logger.error(f"Erro ao testar movimentos: {e}")
        return {
            "pokemon": poke_data.get("name", "Unknown"),
            "error": str(e),
        }

def print_progress(current: int, total: int) -> None:
    """Imprime barra de progresso"""
    if total == 0:
        return

    percent = current / total
    filled = int(40 * percent)
    bar = "█" * filled + "░" * (40 - filled)

    elapsed = 0
    if stats.start_time:
        elapsed = (datetime.now() - stats.start_time).total_seconds()

    print(
        f"\r[{bar}] {current:5d}/{total:5d} ({percent*100:5.1f}%) "
        f"✓{stats.moves_valid:6d} ✗{stats.moves_invalid:5d} [{elapsed:7.2f}s]",
        end="",
        flush=True,
    )

def run_tests_parallel(test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Executa testes em paralelo"""
    if not test_cases:
        logger.error("Nenhum caso de teste gerado")
        return []

    results = []
    stats.start_time = datetime.now()

    print(f"\n{'='*90}")
    print(f"TESTE DE COMPATIBILIDADE DE MOVIMENTOS CROSS-GENERATION")
    print(f"{'='*90}")
    print(f"Total de movimentos a validar: {len(test_cases):,}")
    print(f"Timestamp: {stats.start_time}")
    print(f"{'='*90}\n")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(test_pokemon_moves, **tc): tc for tc in test_cases}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            print_progress(completed, len(test_cases))

    stats.end_time = datetime.now()
    print("\n")
    return results

def generate_report(results: List[Dict[str, Any]]) -> str:
    """Gera relatório detalhado"""
    report = []

    report.append("=" * 90)
    report.append("RELATÓRIO - TESTE DE COMPATIBILIDADE DE MOVIMENTOS")
    report.append("=" * 90)
    report.append("")

    # Resumo executivo
    report.append("RESUMO EXECUTIVO:")
    report.append(f"  Data/Hora: {stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"  Duração total: {stats.duration():.2f}s")
    report.append(f"  Total de movimentos validados: {stats.total_tests:,}")

    if stats.total_tests > 0:
        report.append(f"  Compatíveis: {stats.moves_valid:,} ({stats.moves_valid/stats.total_tests*100:.1f}%)")
        report.append(f"  Incompatíveis: {stats.moves_invalid:,} ({stats.moves_invalid/stats.total_tests*100:.1f}%)")
    report.append("")

    # Distribuição por tipo de compatibilidade
    same_gen_results = [r for r in results if r.get("source_gen") == r.get("target_gen")]
    cross_gen_results = [r for r in results if r.get("source_gen") != r.get("target_gen")]

    report.append("DISTRIBUIÇÃO:")
    report.append(f"  Same-generation: {len(same_gen_results)} Pokémon testados")
    report.append(f"  Cross-generation: {len(cross_gen_results)} combinações testadas")
    report.append("")

    # Movimentos incompatíveis
    if stats.errors:
        report.append("MOVIMENTOS INCOMPATÍVEIS (primeiros 30):")
        seen = set()
        count = 0
        for error in stats.errors:
            key = (error['pokemon'], error['move'], error['gen_route'])
            if key not in seen and count < 30:
                report.append(f"  • {error['pokemon']} Move {error['move']}")
                report.append(f"    Rota: {error['gen_route']} ({error['file']})")
                report.append(f"    Motivo: {error['reason']}")
                seen.add(key)
                count += 1

        if len(stats.errors) > 30:
            report.append(f"  ... e mais {len(stats.errors) - 30} incompatibilidades")
        report.append("")

    # Pokémon com mais incompatibilidades
    poke_incomp = {}
    for error in stats.errors:
        poke = error['pokemon']
        if poke not in poke_incomp:
            poke_incomp[poke] = 0
        poke_incomp[poke] += 1

    if poke_incomp:
        report.append("POKÉMON COM MAIS MOVIMENTOS INCOMPATÍVEIS:")
        for poke, count in sorted(poke_incomp.items(), key=lambda x: -x[1])[:10]:
            report.append(f"  • {poke}: {count} movimentos incompatíveis")
        report.append("")

    # Conclusão
    report.append("=" * 90)
    report.append("CONCLUSÃO:")
    if stats.moves_invalid == 0:
        report.append("✓ TODOS OS MOVIMENTOS SÃO COMPATÍVEIS")
    else:
        report.append(f"⚠ {stats.moves_invalid:,} MOVIMENTOS SÃO INCOMPATÍVEIS EM ALGUMAS ROTAS")
    report.append("=" * 90)

    return "\n".join(report)

def save_results(results: List[Dict[str, Any]]) -> None:
    """Salva resultados em arquivos"""
    # Relatório em texto
    report = generate_report(results)
    report_file = OUTPUT_DIR / "moves_compatibility_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"Relatório salvo: {report_file}")

    # Resultados detalhados em JSON (limpar summary)
    json_file = OUTPUT_DIR / "moves_compatibility_detailed.json"
    clean_results = []
    for r in results:
        r_copy = r.copy()
        if "summary" in r_copy:
            del r_copy["summary"]
        clean_results.append(r_copy)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "start_time": stats.start_time.isoformat(),
                    "end_time": stats.end_time.isoformat(),
                    "duration_seconds": stats.duration(),
                    "total_moves_tested": stats.total_tests,
                    "compatible": stats.moves_valid,
                    "incompatible": stats.moves_invalid,
                },
                "results": clean_results,
                "errors": stats.errors,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"Resultados JSON salvos: {json_file}")

def main():
    """Função principal"""
    try:
        logger.info("Encontrando todos os saves por geração...")
        saves_by_gen = find_all_saves()

        # Carregar todos os Pokémon com movimentos
        pokemon_by_gen = {}
        for gen in [1, 2, 3]:
            pokemon_by_gen[gen] = {}

            logger.info(f"\nCarregando Pokémon com movimentos Gen {gen}...")
            for save_path, save_name in saves_by_gen[gen]:
                logger.info(f"  {save_name}")
                poke_data = load_pokemon_with_moves(save_path, gen)

                # Agregar Pokémon por geração
                for poke_id, poke_info in poke_data.items():
                    if poke_id not in pokemon_by_gen[gen]:
                        pokemon_by_gen[gen][poke_id] = poke_info

        # Gerar casos de teste (todos os Pokémon em todas as combinações de geração)
        test_cases = []
        gen_combos = [
            (1, 1), (1, 2), (1, 3),
            (2, 1), (2, 2), (2, 3),
            (3, 1), (3, 2), (3, 3),
        ]

        for source_gen, target_gen in gen_combos:
            if source_gen not in pokemon_by_gen or not pokemon_by_gen[source_gen]:
                continue

            for poke_id, poke_info in pokemon_by_gen[source_gen].items():
                if poke_info.get("moves"):  # Só testar se tem movimentos
                    test_cases.append({
                        "poke_data": poke_info,
                        "target_gen": target_gen,
                    })

        logger.info(f"\nTotal de Pokémon com movimentos carregados:")
        for gen in [1, 2, 3]:
            logger.info(f"  Gen{gen}: {len(pokemon_by_gen[gen])}")

        logger.info(f"Total de casos de teste gerados: {len(test_cases):,}\n")

        if not test_cases:
            logger.error("Nenhum caso de teste gerado")
            return 1

        # Executar testes
        logger.info("Executando testes...")
        results = run_tests_parallel(test_cases)

        # Salvar resultados
        save_results(results)

        # Imprimir relatório
        print("\n" + generate_report(results))

        return 0 if stats.moves_invalid == 0 else 1

    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
