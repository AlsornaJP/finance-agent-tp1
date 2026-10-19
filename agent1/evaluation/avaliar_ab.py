import argparse
import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path

from agent import database
from agent.agents import construir_variante_sem_tools
from agent.config import Settings, load_settings
from agent.execution_log import Secao, salvar_registro
from agent.importacao import classificar_pendentes
from agent.runner import FalhaDeExecucao, RateLimitAtingido, executar
from agent.schema import AnaliseFinanceira
from evaluation.gabarito import carregar_gabarito
from evaluation.metricas import acuracia_classificacao, precisao_numerica, saidas_do_csv, totais_esperados

EXTRATOS = (Path("samples/extrato_1_mes.csv"), Path("samples/extrato_2_meses.csv"))
DIRETORIO_RESULTADOS = Path("evaluation/resultados")
DIRETORIO_LOGS_AVALIACAO = Path("evaluation/logs")
ERROS_DE_EXECUCAO = (FalhaDeExecucao, RateLimitAtingido)


def _medir(totais: dict[str, float], classificadas: list[tuple[str, float, str]], csv: Path) -> dict:
    gabarito = carregar_gabarito()
    saidas = saidas_do_csv(csv)
    esperados = totais_esperados(saidas, gabarito)
    total_obtido = round(sum(totais.values()), 2)
    return {
        "precisao_numerica": round(precisao_numerica(totais, esperados), 4),
        "erro_absoluto_total": round(abs(total_obtido - round(sum(esperados.values()), 2)), 2),
        "acuracia_classificacao": round(acuracia_classificacao(classificadas, saidas, gabarito), 4),
        "totais_obtidos": totais,
    }


async def _variante_a(csv: Path, settings: Settings) -> dict:
    execucao = await executar(construir_variante_sem_tools, csv.read_text(encoding="utf-8"), settings)
    analise: AnaliseFinanceira = execucao.resultado.final_output
    salvar_registro(
        f"ab_variante_a_{csv.stem}",
        "Avaliação A/B — variante A (sem tools)",
        {"CSV": str(csv), "Modelo": execucao.modelo},
        [Secao("Output", analise.model_dump_json(indent=2), "json")],
        diretorio=DIRETORIO_LOGS_AVALIACAO,
    )
    totais = {item.categoria: round(item.valor_total, 2) for item in analise.resumo_por_categoria}
    classificadas = [(t.descricao, t.valor, t.categoria) for t in analise.transacoes]
    return {"modelo": execucao.modelo, **_medir(totais, classificadas, csv)}


async def _variante_b(csv: Path, settings: Settings) -> dict:
    with tempfile.TemporaryDirectory() as diretorio:
        banco = Path(diretorio) / "avaliacao.db"
        database.importar_csv(banco, csv)
        relatorio = await classificar_pendentes(banco, settings)
        meses = database.meses_disponiveis(banco)
        totais: dict[str, float] = {}
        for mes in meses:
            for item in database.gastos_por_categoria(banco, mes):
                totais[item.categoria] = round(totais.get(item.categoria, 0.0) + item.valor_total, 2)
        classificadas = [
            (t.descricao, t.valor, t.categoria)
            for mes in meses
            for t in database.listar_transacoes(banco, mes)
            if t.tipo == "saida"
        ]
    modelo = relatorio.execucoes[-1].modelo if relatorio.execucoes else "-"
    classificacoes_json = json.dumps([c.model_dump() for c in relatorio.classificadas], ensure_ascii=False, indent=2)
    salvar_registro(
        f"ab_variante_b_{csv.stem}",
        "Avaliação A/B — variante B (classificador + tools)",
        {"CSV": str(csv), "Modelo": modelo},
        [Secao("Classificações", classificacoes_json, "json")],
        diretorio=DIRETORIO_LOGS_AVALIACAO,
    )
    return {"modelo": modelo, **_medir(totais, classificadas, csv)}


async def _main(execucoes: int) -> None:
    settings = load_settings()
    DIRETORIO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = DIRETORIO_RESULTADOS / f"ab_{datetime.now():%Y%m%d-%H%M%S}.json"
    resultados = []
    for csv in EXTRATOS:
        for numero in range(1, execucoes + 1):
            for nome, variante in (("A_sem_tools", _variante_a), ("B_com_tools", _variante_b)):
                print(f"[ab] {nome} {csv.name} execução {numero}")
                try:
                    medicao = await variante(csv, settings)
                except ERROS_DE_EXECUCAO as erro:
                    medicao = {"erro": f"{type(erro).__name__}: {str(erro)[:300]}"}
                resultados.append({"variante": nome, "csv": csv.name, "execucao": numero, **medicao})
                destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"     {({k: v for k, v in medicao.items() if k != 'totais_obtidos'})}")
    print(f"[ab] resultados em {destino}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avaliação A/B: sem tools × com tools")
    parser.add_argument("--execucoes", type=int, default=3)
    asyncio.run(_main(parser.parse_args().execucoes))
