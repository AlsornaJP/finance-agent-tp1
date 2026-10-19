import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from openai import APIError

from agent.config import ConfigError, load_settings
from agent.consulta import perguntar
from agent.database import CAMINHO_BANCO_PADRAO
from agent.diagnostico import diagnosticar
from agent.importacao import importar
from agent.runner import FalhaDeExecucao, RateLimitAtingido

ERROS_ESPERADOS = (ConfigError, RateLimitAtingido, FalhaDeExecucao, ValueError, OSError, APIError)


async def _importar(argumentos: argparse.Namespace) -> None:
    log = await importar(argumentos.banco, argumentos.csv, load_settings())
    print(f"[importar] log salvo em {log}")


async def _perguntar(argumentos: argparse.Namespace) -> None:
    resultado = await perguntar(argumentos.banco, argumentos.sessao, argumentos.pergunta, load_settings())
    print(f"\n{resultado.resposta.resposta}\n")
    for valor in resultado.resposta.valores_citados:
        print(f"  - {valor.descricao}: {valor.valor} (via {valor.ferramenta})")
    for fonte in resultado.resposta.fontes_conhecimento:
        print(f"  - fonte: {fonte}")
    print(f"\n[perguntar] log salvo em {resultado.log}")


async def _diagnosticar(argumentos: argparse.Namespace) -> None:
    diagnostico, log = await diagnosticar(argumentos.banco, argumentos.mes, load_settings())
    print(f"\n{diagnostico.resumo}\n")
    for avaliacao in diagnostico.avaliacoes:
        print(f"  [{avaliacao.situacao}] {avaliacao.assunto}: {avaliacao.explicacao}")
    print()
    for recomendacao in sorted(diagnostico.recomendacoes, key=lambda item: item.prioridade):
        print(f"  {recomendacao.prioridade}. {recomendacao.acao}")
    print(f"\n[diagnosticar] log salvo em {log}")


COMANDOS: dict[str, Callable[[argparse.Namespace], Awaitable[None]]] = {
    "importar": _importar,
    "perguntar": _perguntar,
    "diagnosticar": _diagnosticar,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agente de finanças pessoais (TP2)")
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    comando_importar = subcomandos.add_parser("importar", help="Importa um CSV e classifica as transações")
    comando_importar.add_argument("csv", type=Path)
    comando_importar.add_argument("--banco", type=Path, default=CAMINHO_BANCO_PADRAO)

    comando_perguntar = subcomandos.add_parser("perguntar", help="Faz uma pergunta ao assistente")
    comando_perguntar.add_argument("pergunta")
    comando_perguntar.add_argument("--sessao", required=True)
    comando_perguntar.add_argument("--banco", type=Path, default=CAMINHO_BANCO_PADRAO)

    comando_diagnosticar = subcomandos.add_parser("diagnosticar", help="Gera o diagnóstico de um mês em etapas")
    comando_diagnosticar.add_argument("--mes", required=True)
    comando_diagnosticar.add_argument("--banco", type=Path, default=CAMINHO_BANCO_PADRAO)

    return parser


def main() -> int:
    argumentos = _parser().parse_args()
    try:
        asyncio.run(COMANDOS[argumentos.comando](argumentos))
    except ERROS_ESPERADOS as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
