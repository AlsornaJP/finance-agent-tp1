import argparse
import asyncio
import sys

from agent.config import ConfigError, load_settings
from agent.runner import RateLimitAtingido, rodar_analise
from agent.schema import AnaliseFinanceira

CSV_PADRAO = {
    "parte3": ["samples/extrato_1_mes.csv"],
    "parte4": ["samples/extrato_1_mes.csv"],
    "parte5": ["samples/extrato_1_mes.csv", "samples/extrato_2_meses.csv"],
}


def _conferir(rotulo: str, obtido: float, esperado: float) -> None:
    divergente = abs(obtido - esperado) > 0.01
    marca = "DIVERGE" if divergente else "ok"
    print(f"  [{marca}] {rotulo}: {obtido:.2f} vs {esperado:.2f}")


def _validar(analise: AnaliseFinanceira) -> None:
    total = round(analise.total_gasto, 2)
    soma_categorias = round(sum(item.valor_total for item in analise.resumo_por_categoria), 2)
    soma_transacoes = round(sum(item.valor for item in analise.transacoes), 2)
    qtd_categorias = sum(item.quantidade_transacoes for item in analise.resumo_por_categoria)

    print(f"  final_output é {type(analise).__name__}: {isinstance(analise, AnaliseFinanceira)}")
    print(f"  transações enumeradas: {len(analise.transacoes)}")
    _conferir("soma de transacoes vs total_gasto", soma_transacoes, total)
    _conferir("soma de resumo_por_categoria vs total_gasto", soma_categorias, total)
    _conferir("contagem em resumo_por_categoria vs transacoes", qtd_categorias, len(analise.transacoes))
    print(f"  gastos_anomalos: {len(analise.gastos_anomalos)}")
    print(f"  comparacao_mes_anterior: {len(analise.comparacao_mes_anterior)}")


async def _main(etapa: str, arquivos: list[str]) -> None:
    settings = load_settings()
    for csv_path in arquivos:
        final_output = await rodar_analise(etapa, csv_path, settings)
        if isinstance(final_output, AnaliseFinanceira):
            _validar(final_output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agente de análise de finanças pessoais (TP1)")
    parser.add_argument("etapa", choices=sorted(CSV_PADRAO))
    parser.add_argument("--csv", nargs="+", help="Caminho(s) de CSV de extrato bancário")
    args = parser.parse_args()

    try:
        asyncio.run(_main(args.etapa, args.csv or CSV_PADRAO[args.etapa]))
    except (ConfigError, RateLimitAtingido, RuntimeError) as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
