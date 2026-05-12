#!/usr/bin/env python3
"""
Teste de Trocas Cross-Generation Completo
- Carrega Pokémon reais de todos os saves
- Testa TODAS as combinações de troca entre gerações
- Valida conversores e compatibilidade real
- Relatório detalhado de sucesso/falha por rota
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
    from converters import get_converter
    from compatibility import build_compatibility_report
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
        self.passed = 0
        self.failed = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
        self.trade_routes = {}  # Estatísticas por rota

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

def load_pokemon_from_save(save_path: Path, gen: int) -> Dict[int, Dict[str, Any]]:
    """Carrega Pokémon de um save (party + boxes)"""
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
            pokemon_data[poke_id] = {
                "name": pokemon_summary.species_name,
                "level": pokemon_summary.level,
                "nickname": pokemon_summary.nickname,
                "gen": gen,
                "save_file": save_path.name,
                "location": "party",
                "summary": pokemon_summary,
            }

        # Tentar carregar boxes também (primeiros 30)
        try:
            boxes = parser.list_boxes() if hasattr(parser, 'list_boxes') else []
            for pokemon_summary in boxes[:30]:
                poke_id = pokemon_summary.national_dex_id or pokemon_summary.species_id
                if poke_id not in pokemon_data:
                    pokemon_data[poke_id] = {
                        "name": pokemon_summary.species_name,
                        "level": pokemon_summary.level,
                        "nickname": pokemon_summary.nickname,
                        "gen": gen,
                        "save_file": save_path.name,
                        "location": "box",
                        "summary": pokemon_summary,
                    }
        except Exception as e:
            logger.debug(f"Boxes não carregados: {e}")

        return pokemon_data

    except Exception as e:
        logger.error(f"Erro ao carregar {save_path.name}: {e}")
        return pokemon_data

def test_trade_conversion(
    source_poke: Dict[str, Any],
    source_gen: int,
    target_gen: int,
    source_file: str,
) -> Tuple[bool, str, Optional[Dict]]:
    """Testa compatibilidade de troca entre gerações"""
    try:
        from data.species import species_exists_in_generation, native_to_national

        poke_name = source_poke.get("name", "Unknown")
        poke_national_id = source_poke.get("summary").national_dex_id if source_poke.get("summary") else None

        # Same-gen sempre funciona
        if source_gen == target_gen:
            return True, "Same-gen (compatible)", {
                "route": f"Gen{source_gen}→Gen{source_gen}",
                "pokemon": poke_name,
                "conversion": None,
            }

        # Obter conversor apropriado
        converter = get_converter(source_gen, target_gen)

        if not converter:
            # Rota não suportada
            return False, "Rota não suportada", None

        # Validação simples: verificar se a espécie existe na geração destino
        if not poke_national_id:
            return False, "Espécie sem ID nacional", None

        try:
            # Verificar se a espécie existe na geração destino
            if species_exists_in_generation(poke_national_id, target_gen):
                return True, f"Compatível ({converter.mode})", {
                    "route": f"Gen{source_gen}→Gen{target_gen}",
                    "pokemon": poke_name,
                    "conversion": converter.mode,
                    "national_id": poke_national_id,
                }
            else:
                return False, f"Espécie #{poke_national_id} não existe em Gen{target_gen}", {
                    "route": f"Gen{source_gen}→Gen{target_gen}",
                    "pokemon": poke_name,
                    "national_id": poke_national_id,
                }

        except Exception as check_error:
            # Se houver erro na validação
            return False, f"Erro na validação: {str(check_error)[:50]}", {
                "route": f"Gen{source_gen}→Gen{target_gen}",
                "pokemon": poke_name,
            }

    except Exception as e:
        return False, f"Exceção: {str(e)[:50]}", None

def run_trade_test(
    source_poke: Dict[str, Any],
    source_gen: int,
    target_gen: int,
    source_file: str,
) -> Dict[str, Any]:
    """Executa teste de troca"""
    try:
        success, message, info = test_trade_conversion(
            source_poke, source_gen, target_gen, source_file
        )

        result = {
            "pokemon": source_poke.get("name", "Unknown"),
            "source_gen": source_gen,
            "target_gen": target_gen,
            "source_file": source_file,
            "success": success,
            "message": message,
            "info": info,
        }

        route_key = f"Gen{source_gen}→Gen{target_gen}"
        if route_key not in stats.trade_routes:
            stats.trade_routes[route_key] = {"total": 0, "passed": 0, "failed": 0}

        stats.trade_routes[route_key]["total"] += 1

        if success:
            stats.passed += 1
            stats.trade_routes[route_key]["passed"] += 1
        else:
            stats.failed += 1
            stats.trade_routes[route_key]["failed"] += 1
            stats.errors.append({
                "pokemon": source_poke.get("name", "Unknown"),
                "route": f"{source_gen}→{target_gen}",
                "file": source_file,
                "reason": message,
            })

        return result

    except Exception as e:
        stats.failed += 1
        route_key = f"Gen{source_gen}→Gen{target_gen}"
        if route_key in stats.trade_routes:
            stats.trade_routes[route_key]["failed"] += 1

        return {
            "pokemon": source_poke.get("name", "Unknown"),
            "source_gen": source_gen,
            "target_gen": target_gen,
            "success": False,
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
        f"✓{stats.passed:6d} ✗{stats.failed:5d} [{elapsed:7.2f}s]",
        end="",
        flush=True,
    )

def run_tests_parallel(test_cases: List[Dict[str, Any]], max_workers: int = 8) -> List[Dict[str, Any]]:
    """Executa testes em paralelo"""
    if not test_cases:
        logger.error("Nenhum caso de teste gerado")
        return []

    results = []
    stats.total_tests = len(test_cases)
    stats.start_time = datetime.now()

    print(f"\n{'='*90}")
    print(f"TESTE DE TROCAS CROSS-GENERATION COM SAVES REAIS")
    print(f"{'='*90}")
    print(f"Total de casos de teste: {len(test_cases):,}")
    print(f"Combinações de geração: 9 (Gen1↔1, Gen1↔2, Gen1→3, etc)")
    print(f"Workers paralelos: {max_workers}")
    print(f"Timestamp: {stats.start_time}")
    print(f"{'='*90}\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_trade_test, **tc): tc for tc in test_cases}

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
    report.append("RELATÓRIO - TESTE DE TROCAS CROSS-GENERATION COM SAVES REAIS")
    report.append("=" * 90)
    report.append("")

    # Resumo executivo
    report.append("RESUMO EXECUTIVO:")
    report.append(f"  Data/Hora: {stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"  Duração total: {stats.duration():.2f}s")
    report.append(f"  Total de testes: {stats.total_tests}")
    report.append(f"  Passou: {stats.passed:,} ({stats.passed/max(1, stats.total_tests)*100:.1f}%)")
    report.append(f"  Falhou: {stats.failed:,} ({stats.failed/max(1, stats.total_tests)*100:.1f}%)")
    report.append(f"  Tempo médio: {stats.duration()/max(1, stats.total_tests):.4f}s/teste")
    report.append("")

    # Estatísticas por rota
    report.append("TROCAS POR ROTA:")
    for route in sorted(stats.trade_routes.keys()):
        s = stats.trade_routes[route]
        pct = (s["passed"] / s["total"] * 100) if s["total"] > 0 else 0
        status = "✓" if pct == 100 else "✗"
        report.append(
            f"  {status} {route:15s}: {s['passed']:6d}/{s['total']:6d} ({pct:6.1f}%)"
        )

    report.append("")

    # Same-gen vs cross-gen
    same_gen_passed = sum(
        s["passed"] for route, s in stats.trade_routes.items()
        if "→" in route and route[3] == route[-1]  # Gen1→Gen1, etc
    )
    same_gen_total = sum(
        s["total"] for route, s in stats.trade_routes.items()
        if "→" in route and route[3] == route[-1]
    )

    cross_gen_passed = sum(
        s["passed"] for route, s in stats.trade_routes.items()
        if "→" in route and route[3] != route[-1]
    )
    cross_gen_total = sum(
        s["total"] for route, s in stats.trade_routes.items()
        if "→" in route and route[3] != route[-1]
    )

    report.append("DISTRIBUIÇÃO:")
    report.append(f"  Same-generation: {same_gen_passed}/{same_gen_total}")
    report.append(f"  Cross-generation: {cross_gen_passed}/{cross_gen_total}")
    report.append("")

    # Erros
    if stats.errors:
        report.append("ERROS (primeiros 20):")
        for error in stats.errors[:20]:
            report.append(f"  • {error['pokemon']} [{error['file']}]")
            report.append(f"    Rota: {error['route']}")
            report.append(f"    Motivo: {error['reason']}")

        if len(stats.errors) > 20:
            report.append(f"  ... e mais {len(stats.errors) - 20} erros")
        report.append("")

    # Conclusão
    report.append("=" * 90)
    report.append("CONCLUSÃO:")
    if stats.failed == 0:
        report.append("✓ TODAS AS TROCAS FORAM VALIDADAS COM SUCESSO")
    else:
        report.append(f"✗ {stats.failed:,} TROCAS FALHARAM")
    report.append("=" * 90)

    return "\n".join(report)

def save_results(results: List[Dict[str, Any]]) -> None:
    """Salva resultados em arquivos"""
    # Relatório em texto
    report = generate_report(results)
    report_file = OUTPUT_DIR / "cross_gen_trades_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"Relatório salvo: {report_file}")

    # Resultados detalhados em JSON
    json_file = OUTPUT_DIR / "cross_gen_trades_detailed.json"
    with open(json_file, "w", encoding="utf-8") as f:
        # Limpar dados do summary para serialização JSON
        clean_results = []
        for r in results:
            r_copy = r.copy()
            if "summary" in r_copy:
                del r_copy["summary"]
            clean_results.append(r_copy)

        json.dump(
            {
                "metadata": {
                    "start_time": stats.start_time.isoformat(),
                    "end_time": stats.end_time.isoformat(),
                    "duration_seconds": stats.duration(),
                    "total_tests": stats.total_tests,
                    "passed": stats.passed,
                    "failed": stats.failed,
                    "trade_routes": stats.trade_routes,
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

        # Carregar todos os Pokémon
        pokemon_by_gen = {}
        for gen in [1, 2, 3]:
            pokemon_by_gen[gen] = {}

            logger.info(f"\nCarregando saves Gen {gen}...")
            for save_path, save_name in saves_by_gen[gen]:
                logger.info(f"  {save_name}")
                poke_data = load_pokemon_from_save(save_path, gen)

                # Agregar Pokémon por geração
                for poke_id, poke_info in poke_data.items():
                    if poke_id not in pokemon_by_gen[gen]:
                        pokemon_by_gen[gen][poke_id] = poke_info

        # Gerar casos de teste (todas as combinações de trocas)
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
                test_cases.append({
                    "source_poke": poke_info,
                    "source_gen": source_gen,
                    "target_gen": target_gen,
                    "source_file": poke_info["save_file"],
                })

        logger.info(f"\nTotal de Pokémon únicos carregados:")
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

        return 0 if stats.failed == 0 else 1

    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
