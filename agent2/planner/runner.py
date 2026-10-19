from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents import Agent, Model, OpenAIChatCompletionsModel, RunResult, Runner

from planner.config import Settings, configure_sdk, google_client

ConstrutorAgente = Callable[[Model], Agent]


class FalhaDeExecucao(RuntimeError):
    pass


@dataclass(frozen=True)
class Execucao:
    resultado: RunResult
    modelo: str


async def executar(
    construir: ConstrutorAgente,
    entrada: str,
    settings: Settings,
    *,
    context: Any = None,
    max_turns: int = 10,
) -> Execucao:
    configure_sdk(settings)
    cliente = google_client(settings)
    erros: list[str] = []
    for modelo in settings.gemini_models:
        print(f"[planejador] modelo={modelo}")
        try:
            agente = construir(OpenAIChatCompletionsModel(model=modelo, openai_client=cliente))
            resultado = await Runner.run(agente, entrada, context=context, max_turns=max_turns)
        except Exception as erro:
            print(f"[planejador] falha: {type(erro).__name__}: {erro}")
            erros.append(f"[{modelo}] {type(erro).__name__}: {erro}")
            continue
        return Execucao(resultado, modelo)
    raise FalhaDeExecucao("Execução falhou em todos os modelos Gemini:\n\n" + "\n\n".join(erros))
