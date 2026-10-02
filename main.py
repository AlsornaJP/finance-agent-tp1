import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

from agent.config import ConfigError
from agent.runner import FalhaDeExecucao, RateLimitAtingido

ERROS_ESPERADOS = (ConfigError, RateLimitAtingido, FalhaDeExecucao, ValueError)

COMANDOS: dict[str, Callable[[argparse.Namespace], Awaitable[None]]] = {}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agente de finanças pessoais (TP2)")
    parser.add_subparsers(dest="comando", required=True)
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
