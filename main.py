import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from agent.config import ConfigError, load_settings
from agent.database import CAMINHO_BANCO_PADRAO
from agent.importacao import importar
from agent.runner import FalhaDeExecucao, RateLimitAtingido

ERROS_ESPERADOS = (ConfigError, RateLimitAtingido, FalhaDeExecucao, ValueError)


async def _importar(argumentos: argparse.Namespace) -> None:
    log = await importar(argumentos.banco, argumentos.csv, load_settings())
    print(f"[importar] log salvo em {log}")


COMANDOS: dict[str, Callable[[argparse.Namespace], Awaitable[None]]] = {
    "importar": _importar,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agente de finanças pessoais (TP2)")
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    comando_importar = subcomandos.add_parser("importar", help="Importa um CSV e classifica as transações")
    comando_importar.add_argument("csv", type=Path)
    comando_importar.add_argument("--banco", type=Path, default=CAMINHO_BANCO_PADRAO)

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
