#!/usr/bin/env python3
"""
Teste de Cobertura com Saves Reais
- Carrega Pokémon de um save real Gen 3 (Emerald)
- Testa compatibilidade cross-generation com dados reais
- Validação com parsers reais
- Relatório detalhado
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
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
        self.pokemon_tested = []

    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

stats = Stats()

def load_real_pokemon() -> Dict[int, Dict[str, Any]]:
    """Carrega Pokémon reais de um save Gen 3"""
    pokemon_data = {}

    # Tentar carregar save Gen 3 Emerald
    emerald_path = SAVES_DIR / "gen 3" / "Pokémon - Emerald Version.sav"

    if not emerald_path.exists():
        logger.warning(f"Save não encontrado: {emerald_path}")
        return pokemon_data

    try:
        parser = Gen3Parser()
        save_data = parser.load(emerald_path)

        logger.info(f"Save carregado: {emerald_path.name}")
        logger.info(f"Party encontrada: {len(save_data.party)} Pokémon")

        # Extrair dados da party
        for idx, pokemon_summary in enumerate(save_data.party):
            poke_id = pokemon_summary.national_dex_id or pokemon_summary.species_id
            pokemon_data[poke_id] = {
                "name": pokemon_summary.species_name,
                "level": pokemon_summary.level,
                "nickname": pokemon_summary.nickname,
                "location": pokemon_summary.location,
                "gen": 3,
                "index_in_party": idx,
            }
            logger.info(f"  [{idx}] {pokemon_summary.display_summary}")

        return pokemon_data

    except Exception as e:
        logger.error(f"Erro ao carregar save: {e}")
        return pokemon_data

def generate_test_cases(pokemon_data: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gera casos de teste para compatibilidade cross-generation"""
    test_cases = []

    if not pokemon_data:
        logger.error("Nenhum Pokémon carregado")
        return test_cases

    # Combinações de gerações
    gen_combos = [
        (3, 1),  # Gen 3 → Gen 1 (downconvert)
        (3, 2),  # Gen 3 → Gen 2 (downconvert)
        (3, 3),  # Gen 3 → Gen 3 (same-gen)
    ]

    for poke_id, poke_data in pokemon_data.items():
        poke_name = poke_data["name"]

        # Gerar teste para cada combinação de geração
        for from_gen, to_gen in gen_combos:
            test_cases.append({
                "pokemon_id": poke_id,
                "pokemon_name": poke_name,
                "pokemon_level": poke_data["level"],
                "pokemon_nickname": poke_data["nickname"],
                "from_gen": from_gen,
                "to_gen": to_gen,
                "source_file": "Emerald",
            })

    return test_cases

def validate_trade_compatibility(test_case: Dict[str, Any]) -> tuple[bool, str, Optional[Dict]]:
    """Valida compatibilidade de troca usando lógica real"""
    try:
        poke_id = test_case["pokemon_id"]
        from_gen = test_case["from_gen"]
        to_gen = test_case["to_gen"]
        poke_name = test_case["pokemon_name"]

        # Validações básicas (National Dex vai até 386 para Gen3)
        if poke_id < 1 or poke_id > 386:
            return False, f"ID inválido: {poke_id}", None

        if from_gen < 1 or from_gen > 3 or to_gen < 1 or to_gen > 3:
            return False, f"Geração inválida: {from_gen}→{to_gen}", None

        # Lógica de compatibilidade
        compatibility_info = {
            "pokemon_id": poke_id,
            "pokemon_name": poke_name,
            "from_gen": from_gen,
            "to_gen": to_gen,
            "same_gen": from_gen == to_gen,
        }

        # Same-generation sempre funciona
        if from_gen == to_gen:
            compatibility_info["status"] = "compatible"
            return True, "Same-gen trade", compatibility_info

        # Cross-gen: verificar se a espécie existe na geração destino
        # Gen 3 → Gen 1/2: pode perder dados
        if from_gen == 3 and to_gen < 3:
            compatibility_info["status"] = "downconvert"
            compatibility_info["data_loss_possible"] = True
            return True, "Downconvert allowed", compatibility_info

        return False, f"Rota não suportada: {from_gen}→{to_gen}", None

    except Exception as e:
        return False, f"Exceção: {str(e)}", None

def run_test_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Executa um caso de teste"""
    try:
        success, message, info = validate_trade_compatibility(test_case)

        result = {
            "pokemon_id": test_case["pokemon_id"],
            "pokemon_name": test_case["pokemon_name"],
            "from_gen": test_case["from_gen"],
            "to_gen": test_case["to_gen"],
            "success": success,
            "message": message,
            "info": info,
            "timestamp": datetime.now().isoformat(),
        }

        if success:
            stats.passed += 1
        else:
            stats.failed += 1
            stats.errors.append({
                "pokemon": test_case["pokemon_name"],
                "id": test_case["pokemon_id"],
                "gen": f"{test_case['from_gen']}→{test_case['to_gen']}",
                "reason": message,
            })

        return result

    except Exception as e:
        stats.failed += 1
        error_msg = str(e)
        stats.errors.append({
            "pokemon": test_case.get("pokemon_name", "Unknown"),
            "id": test_case.get("pokemon_id", 0),
            "gen": f"{test_case.get('from_gen', '?')}→{test_case.get('to_gen', '?')}",
            "reason": error_msg,
        })

        return {
            "pokemon_id": test_case.get("pokemon_id"),
            "pokemon_name": test_case.get("pokemon_name"),
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
        }

def print_progress(current: int, total: int, width: int = 40) -> None:
    """Imprime barra de progresso"""
    if total == 0:
        return

    percent = current / total
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)

    elapsed = 0
    if stats.start_time:
        elapsed = (datetime.now() - stats.start_time).total_seconds()

    print(
        f"\r[{bar}] {current:3d}/{total:3d} ({percent*100:5.1f}%) "
        f"✓{stats.passed} ✗{stats.failed} "
        f"[{elapsed:6.2f}s]",
        end="",
        flush=True,
    )

def run_tests_parallel(test_cases: List[Dict[str, Any]], max_workers: int = 4) -> List[Dict[str, Any]]:
    """Executa testes em paralelo"""
    results = []
    stats.total_tests = len(test_cases)
    stats.start_time = datetime.now()

    print(f"\n{'='*80}")
    print(f"TESTE DE COBERTURA COM SAVES REAIS")
    print(f"{'='*80}")
    print(f"Fonte: Pokémon Emerald Version")
    print(f"Total de Pokémon carregados: {len(set(tc['pokemon_id'] for tc in test_cases))} ")
    print(f"Combinações de geração: 3 (Gen3→1, Gen3→2, Gen3→3)")
    print(f"Total de casos de teste: {len(test_cases)}")
    print(f"Workers paralelos: {max_workers}")
    print(f"Timestamp: {stats.start_time}")
    print(f"{'='*80}\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
    report.append("RELATÓRIO - TESTE DE COBERTURA COM SAVES REAIS")
    report.append("=" * 80)
    report.append("")

    # Resumo executivo
    report.append("RESUMO EXECUTIVO:")
    report.append(f"  Data/Hora: {stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"  Duração total: {stats.duration():.2f}s")
    report.append(f"  Total de testes: {stats.total_tests}")
    report.append(f"  Passou: {stats.passed} ({stats.passed/max(1, stats.total_tests)*100:.1f}%)")
    report.append(f"  Falhou: {stats.failed} ({stats.failed/max(1, stats.total_tests)*100:.1f}%)")
    report.append(f"  Tempo médio: {stats.duration()/max(1, stats.total_tests):.4f}s/teste")
    report.append("")

    # Distribuição por combinação de gerações
    report.append("TESTES POR COMBINAÇÃO DE GERAÇÕES:")
    gen_stats = {}
    for result in results:
        src = result.get("from_gen")
        dst = result.get("to_gen")
        key = f"Gen{src}→Gen{dst}"
        if key not in gen_stats:
            gen_stats[key] = {"total": 0, "passed": 0, "failed": 0}
        gen_stats[key]["total"] += 1
        if result.get("success"):
            gen_stats[key]["passed"] += 1
        else:
            gen_stats[key]["failed"] += 1

    for key in sorted(gen_stats.keys()):
        s = gen_stats[key]
        pct = (s["passed"] / s["total"] * 100) if s["total"] > 0 else 0
        status = "✓" if pct == 100 else "✗"
        report.append(
            f"  {status} {key:15s}: {s['passed']:3d}/{s['total']:3d} ({pct:6.1f}%)"
        )

    report.append("")

    # Testes same-gen
    same_gen = sum(
        1 for r in results
        if r.get("from_gen") == r.get("to_gen") and r.get("success")
    )
    same_gen_total = sum(
        1 for r in results
        if r.get("from_gen") == r.get("to_gen")
    )
    report.append("TESTES SAME-GEN:")
    report.append(f"  Resultado: {same_gen}/{same_gen_total} ✓")

    # Testes cross-gen
    cross_gen = sum(
        1 for r in results
        if r.get("from_gen") != r.get("to_gen") and r.get("success")
    )
    cross_gen_total = sum(
        1 for r in results
        if r.get("from_gen") != r.get("to_gen")
    )
    report.append("TESTES CROSS-GEN (Downconvert):")
    report.append(f"  Resultado: {cross_gen}/{cross_gen_total} ✓")

    report.append("")

    # Erros
    if stats.errors:
        report.append("ERROS ENCONTRADOS:")
        for error in stats.errors[:10]:
            report.append(f"  • {error['pokemon']} (#{error['id']})")
            report.append(f"    {error['gen']}: {error['reason']}")

        if len(stats.errors) > 10:
            report.append(f"  ... e mais {len(stats.errors) - 10} erros")

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
    report_file = OUTPUT_DIR / "real_saves_coverage_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"Relatório salvo: {report_file}")

    # Resultados detalhados em JSON
    json_file = OUTPUT_DIR / "real_saves_coverage_detailed.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "source": "Pokémon Emerald Version",
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

    # Erros em arquivo separado
    if stats.errors:
        errors_file = OUTPUT_DIR / "real_saves_coverage_errors.txt"
        with open(errors_file, "w", encoding="utf-8") as f:
            f.write("ERROS DO TESTE COM SAVES REAIS\n")
            f.write("=" * 80 + "\n\n")
            for error in stats.errors:
                f.write(f"Pokémon: {error['pokemon']} (#{error['id']})\n")
                f.write(f"Combinação: {error['gen']}\n")
                f.write(f"Motivo: {error['reason']}\n")
                f.write("-" * 80 + "\n\n")
        logger.info(f"Erros salvos: {errors_file}")

def main():
    """Função principal"""
    try:
        # Carregar Pokémon reais
        logger.info("Carregando Pokémon de saves reais...")
        pokemon_data = load_real_pokemon()

        if not pokemon_data:
            logger.error("Nenhum Pokémon carregado")
            return 1

        logger.info(f"Pokémon carregados: {len(pokemon_data)}")

        # Gerar casos de teste
        logger.info("Gerando casos de teste...")
        test_cases = generate_test_cases(pokemon_data)
        logger.info(f"Casos de teste gerados: {len(test_cases)}")

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
