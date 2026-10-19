import argparse
import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from agent import rag
from agent.config import load_settings
from agent.consulta import perguntar
from agent.rastreio import numeros_nos_retornos
from evaluation.gabarito import criar_banco_gabarito
from evaluation.metricas import acertou, numeros_no_texto, rastreabilidade

DIRETORIO_PRRR = Path("evaluation/prrr")
EXTRATO = Path("samples/extrato_2_meses.csv")


async def _main(versao: str) -> None:
    settings = load_settings()
    instructions = (DIRETORIO_PRRR / f"assistente_{versao}.md").read_text(encoding="utf-8")
    perguntas = json.loads((DIRETORIO_PRRR / "perguntas.json").read_text(encoding="utf-8"))
    resultados = []
    with tempfile.TemporaryDirectory() as diretorio:
        base = criar_banco_gabarito(Path(diretorio) / "base.db", EXTRATO)
        await rag.indexar_guia(base, settings)
        for numero, item in enumerate(perguntas, start=1):
            banco = Path(diretorio) / f"pergunta_{numero}.db"
            shutil.copy(base, banco)
            resultado = await perguntar(
                banco,
                f"prrr-{versao}-{numero}",
                item["pergunta"],
                settings,
                instructions=instructions,
                diretorio_log=DIRETORIO_PRRR / "logs" / versao,
            )
            citados = [valor.valor for valor in resultado.resposta.valores_citados]
            numeros_das_tools = numeros_nos_retornos(resultado.chamadas)
            rastreabilidade_texto = rastreabilidade(numeros_no_texto(resultado.resposta.resposta), numeros_das_tools)
            esperado = item["esperado"]
            medicao = {
                "pergunta": item["pergunta"],
                "esperado": esperado,
                "resposta": resultado.resposta.resposta,
                "valores_citados": citados,
                "tools_chamadas": [chamada.nome for chamada in resultado.chamadas],
                "rastreabilidade": round(rastreabilidade(citados, numeros_das_tools), 4),
                "rastreabilidade_texto": round(rastreabilidade_texto, 4),
                "acertou": acertou(citados, esperado) if esperado is not None else rastreabilidade_texto == 1.0,
                "modelo": resultado.execucao.modelo,
            }
            resultados.append(medicao)
            print(
                f"[prrr {versao}] {numero}: acertou={medicao['acertou']} rastreabilidade={medicao['rastreabilidade']} "
                f"rastreabilidade_texto={medicao['rastreabilidade_texto']}"
            )

    total = len(resultados)
    resumo = {
        "versao": versao,
        "acertos": sum(r["acertou"] for r in resultados),
        "total": total,
        "rastreabilidade_media": round(sum(r["rastreabilidade"] for r in resultados) / total, 4),
        "rastreabilidade_texto_media": round(sum(r["rastreabilidade_texto"] for r in resultados) / total, 4),
        "resultados": resultados,
    }
    destino = DIRETORIO_PRRR / f"resultado_{versao}.json"
    destino.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[prrr {versao}] {resumo['acertos']}/{total} acertos, rastreabilidade média {resumo['rastreabilidade_media']}, "
        f"no texto {resumo['rastreabilidade_texto_media']}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ciclo Prompt-Response-Reflect-Revise do assistente")
    parser.add_argument("versao")
    asyncio.run(_main(parser.parse_args().versao))
