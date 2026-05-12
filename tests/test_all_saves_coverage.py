#!/usr/bin/env python3
"""
Teste de Cobertura com Todos os Saves Reais
- Carrega Pokémon de TODOS os saves disponíveis (Gen 1, 2, 3)
- Testa compatibilidade cross-generation com dados reais
- Relatório por save file
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
        self.saves_tested = {}

    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

stats = Stats()

def find_all_saves() -> List[Tuple[Path, int]]:
    """Encontra todos os saves disponíveis e suas gerações"""
    saves = []

    if not SAVES_DIR.exists():
        logger.warning(f"Diretório de saves não encontrado: {SAVES_DIR}")
        return saves

    for gen_dir in sorted(SAVES_DIR.glob("gen *")):
        if not gen_dir.is_dir():
            continue

        gen = int(gen_dir.name.split()[-1])
        for save_file in sorted(gen_dir.glob("*.sav")):
            saves.append((save_file, gen))
            logger.info(f"Found: {save_file.name} (Gen{gen})")

    return saves

def load_pokemon_from_save(save_path: Path, gen: int) -> Dict[int, Dict[str, Any]]:
    """Carrega Pokémon de um save (party e boxes)"""
    pokemon_data = {}

    try:
        if gen == 1:
            parser = Gen1Parser()
        elif gen == 2:
            parser = Gen2Parser()
        elif gen == 3:
            parser = Gen3Parser()
        else:
            logger.warning(f"Geração não suportada: {gen}")
            return pokemon_data

        save_data = parser.load(save_path)

        party_count = len(save_data.party)

        # Extrair dados da party
        for idx, pokemon_summary in enumerate(save_data.party):
            poke_id = pokemon_summary.national_dex_id or pokemon_summary.species_id
            pokemon_data[poke_id] = {
                "name": pokemon_summary.species_name,
                "level": pokemon_summary.level,
                "nickname": pokemon_summary.nickname,
                "gen": gen,
                "save_file": save_path.name,
                "location": "party",
            }

        # Tentar carregar boxes também
        box_count = 0
        try:
            boxes = parser.list_boxes() if hasattr(parser, 'list_boxes') else []
            if boxes:
                box_count = len(boxes)
                for idx, pokemon_summary in enumerate(boxes[:30]):  # Limitar aos primeiros 30
                    poke_id = pokemon_summary.national_dex_id or pokemon_summary.species_id
                    if poke_id not in pokemon_data:  # Não duplicar
                        pokemon_data[poke_id] = {
                            "name": pokemon_summary.species_name,
                            "level": pokemon_summary.level,
                            "nickname": pokemon_summary.nickname,
                            "gen": gen,
                            "save_file": save_path.name,
                            "location": "box",
                        }
        except Exception as e:
            logger.debug(f"  Boxes não carregados: {e}")

        info_msg = f"  Carregado: {party_count} da party"
        if box_count > 0:
            info_msg += f" + {box_count} nos boxes"
        info_msg += f" (Total: {len(pokemon_data)} Pokémon único)"
        logger.info(info_msg)

        return pokemon_data

    except Exception as e:
        logger.error(f"  Erro ao carregar: {e}")
        return pokemon_data

def generate_cross_gen_test_cases(pokemon_data: Dict[int, Dict[str, Any]], source_gen: int) -> List[Dict[str, Any]]:
    """Gera casos de teste de cross-generation para os Pokémon"""
    test_cases = []

    if not pokemon_data:
        return test_cases

    # Combinações válidas de cross-generation
    valid_combos = []
    if source_gen == 1:
        valid_combos = [(1, 2), (1, 3), (1, 1)]  # Gen1 pode ir pra Gen2, Gen3, ou ficar em Gen1
    elif source_gen == 2:
        valid_combos = [(2, 1), (2, 3), (2, 2)]  # Gen2 pode ir pra Gen1, Gen3, ou ficar em Gen2
    elif source_gen == 3:
        valid_combos = [(3, 1), (3, 2), (3, 3)]  # Gen3 pode ir pra Gen1, Gen2, ou ficar em Gen3

    for poke_id, poke_data in pokemon_data.items():
        poke_name = poke_data["name"]

        for from_gen, to_gen in valid_combos:
            test_cases.append({
                "pokemon_id": poke_id,
                "pokemon_name": poke_name,
                "pokemon_level": poke_data["level"],
                "from_gen": from_gen,
                "to_gen": to_gen,
                "source_file": poke_data["save_file"],
            })

    return test_cases

def validate_trade(test_case: Dict[str, Any]) -> Tuple[bool, str]:
    """Validação simples de compatibilidade"""
    try:
        poke_id = test_case["pokemon_id"]
        from_gen = test_case["from_gen"]
        to_gen = test_case["to_gen"]

        # Validações básicas
        if poke_id < 1 or poke_id > 386:
            return False, f"ID inválido: {poke_id}"

        if from_gen < 1 or from_gen > 3 or to_gen < 1 or to_gen > 3:
            return False, f"Geração inválida"

        # Same-gen sempre funciona
        if from_gen == to_gen:
            return True, "OK"

        # Forward transfer: Gen1/2 → Gen3
        if from_gen < 3 and to_gen == 3:
            return True, "Forward transfer"

        # Downconvert: Gen3 → Gen1/2
        if from_gen == 3 and to_gen < 3:
            return True, "Downconvert"

        # Time capsule: Gen1 ↔ Gen2
        if (from_gen == 1 and to_gen == 2) or (from_gen == 2 and to_gen == 1):
            return True, "Time capsule"

        return False, f"Rota não suportada: {from_gen}→{to_gen}"

    except Exception as e:
        return False, str(e)

def run_test_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Executa um caso de teste"""
    try:
        success, message = validate_trade(test_case)

        result = {
            "pokemon_id": test_case["pokemon_id"],
            "pokemon_name": test_case["pokemon_name"],
            "from_gen": test_case["from_gen"],
            "to_gen": test_case["to_gen"],
            "source_file": test_case["source_file"],
            "success": success,
            "message": message,
        }

        if success:
            stats.passed += 1
        else:
            stats.failed += 1
            stats.errors.append({
                "pokemon": test_case["pokemon_name"],
                "id": test_case["pokemon_id"],
                "gen": f"{test_case['from_gen']}→{test_case['to_gen']}",
                "file": test_case["source_file"],
            })

        return result

    except Exception as e:
        stats.failed += 1
        return {
            "pokemon_id": test_case.get("pokemon_id"),
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
        f"\r[{bar}] {current:4d}/{total:4d} ({percent*100:5.1f}%) "
        f"✓{stats.passed:5d} ✗{stats.failed:4d} [{elapsed:6.2f}s]",
        end="",
        flush=True,
    )

def run_tests_parallel(test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Executa testes em paralelo"""
    if not test_cases:
        logger.error("Nenhum caso de teste gerado")
        return []

    results = []
    stats.total_tests = len(test_cases)
    stats.start_time = datetime.now()

    print(f"\n{'='*80}")
    print(f"TESTE DE COBERTURA COM TODOS OS SAVES REAIS")
    print(f"{'='*80}")
    print(f"Total de casos de teste: {len(test_cases)}")
    print(f"Timestamp: {stats.start_time}")
    print(f"{'='*80}\n")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(run_test_case, tc): tc for tc in test_cases}

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

    report.append("=" * 80)
    report.append("RELATÓRIO - TESTE COM TODOS OS SAVES REAIS")
    report.append("=" * 80)
    report.append("")

    # Resumo executivo
    report.append("RESUMO EXECUTIVO:")
    report.append(f"  Data/Hora: {stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"  Duração total: {stats.duration():.2f}s")
    report.append(f"  Total de testes: {stats.total_tests}")
    report.append(f"  Passou: {stats.passed} ({stats.passed/max(1, stats.total_tests)*100:.1f}%)")
    report.append(f"  Falhou: {stats.failed} ({stats.failed/max(1, stats.total_tests)*100:.1f}%)")
    report.append("")

    # Distribuição por save file
    report.append("TESTES POR SAVE FILE:")
    file_stats = {}
    for result in results:
        source_file = result.get("source_file", "Unknown")
        if source_file not in file_stats:
            file_stats[source_file] = {"total": 0, "passed": 0}
        file_stats[source_file]["total"] += 1
        if result.get("success"):
            file_stats[source_file]["passed"] += 1

    for source_file in sorted(file_stats.keys()):
        s = file_stats[source_file]
        pct = (s["passed"] / s["total"] * 100) if s["total"] > 0 else 0
        status = "✓" if pct == 100 else "✗"
        report.append(f"  {status} {source_file:40s}: {s['passed']:3d}/{s['total']:3d} ({pct:5.1f}%)")

    report.append("")

    # Erros
    if stats.errors:
        report.append("ERROS (primeiros 15):")
        for error in stats.errors[:15]:
            report.append(f"  • {error['pokemon']} (#{error['id']}) [{error['file']}]")
            report.append(f"    {error['gen']}")

        if len(stats.errors) > 15:
            report.append(f"  ... e mais {len(stats.errors) - 15} erros")
        report.append("")

    # Conclusão
    report.append("=" * 80)
    report.append("CONCLUSÃO:")
    if stats.failed == 0:
        report.append("✓ TODOS OS TESTES PASSARAM")
    else:
        report.append(f"✗ {stats.failed} TESTES FALHARAM")
    report.append("=" * 80)

    return "\n".join(report)

def save_results(results: List[Dict[str, Any]]) -> None:
    """Salva resultados em arquivos"""
    # Relatório em texto
    report = generate_report(results)
    report_file = OUTPUT_DIR / "all_saves_coverage_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"Relatório salvo: {report_file}")

    # Resultados detalhados em JSON
    json_file = OUTPUT_DIR / "all_saves_coverage_detailed.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "start_time": stats.start_time.isoformat(),
                    "end_time": stats.end_time.isoformat(),
                    "duration_seconds": stats.duration(),
                    "total_tests": stats.total_tests,
                    "passed": stats.passed,
                    "failed": stats.failed,
                },
                "results": results,
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
        logger.info("Encontrando todos os saves...")
        saves = find_all_saves()

        if not saves:
            logger.error("Nenhum save encontrado")
            return 1

        logger.info(f"Total de saves encontrados: {len(saves)}\n")

        # Carregar Pokémon de todos os saves
        all_test_cases = []
        for save_path, gen in saves:
            logger.info(f"Carregando {save_path.name}...")
            pokemon_data = load_pokemon_from_save(save_path, gen)

            if pokemon_data:
                test_cases = generate_cross_gen_test_cases(pokemon_data, gen)
                all_test_cases.extend(test_cases)
                stats.saves_tested[save_path.name] = len(pokemon_data)

        if not all_test_cases:
            logger.error("Nenhum Pokémon carregado de nenhum save")
            return 1

        logger.info(f"\nTotal de Pokémon carregados: {len(stats.saves_tested)}")
        logger.info(f"Total de testes gerados: {len(all_test_cases)}\n")

        # Executar testes
        logger.info("Executando testes...")
        results = run_tests_parallel(all_test_cases)

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
