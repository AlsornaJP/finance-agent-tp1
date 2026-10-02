from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents import Agent, Model, OpenAIChatCompletionsModel, RunResult, Runner, Session
from openai import APIStatusError, AsyncOpenAI, RateLimitError

from agent.config import ConfigError, Settings, configure_sdk, google_client, modelo_no_google, openrouter_client
from agent.execution_log import Secao, salvar_registro

MARCADORES_LIMITE_UPSTREAM = ("upstream_provider_shared_pool", "rate-limited upstream")
PROVEDOR_GOOGLE = "GoogleAIStudio/chave-pessoal"

ConstrutorAgente = Callable[[Model], Agent]


class RateLimitAtingido(RuntimeError):
    pass


class FalhaDeExecucao(RuntimeError):
    pass


@dataclass(frozen=True)
class Tentativa:
    provedor: str
    client: AsyncOpenAI
    model: str


@dataclass(frozen=True)
class Execucao:
    resultado: RunResult
    provedor: str
    modelo: str


def _e_rate_limit(erro: Exception) -> bool:
    if isinstance(erro, RateLimitError):
        return True
    if isinstance(erro, APIStatusError) and erro.status_code == 429:
        return True
    return "429" in str(erro)


def _e_limite_do_provedor(erro: Exception) -> bool:
    texto = str(erro).lower()
    return any(marcador in texto for marcador in MARCADORES_LIMITE_UPSTREAM)


def _e_limite_da_chave(erro: Exception) -> bool:
    return _e_rate_limit(erro) and not _e_limite_do_provedor(erro)


def _tentativas_com_tools(settings: Settings) -> list[Tentativa]:
    if not settings.google_api_key:
        raise ConfigError("Agentes com tools exigem GOOGLE_API_KEY (modelos Gemini do Google AI Studio).")
    if not settings.google_tool_models:
        raise ConfigError("Agentes com tools exigem GOOGLE_TOOL_MODELS no .env, ex.: gemini-3.5-flash-lite.")
    cliente = google_client(settings)
    return [Tentativa(PROVEDOR_GOOGLE, cliente, model) for model in settings.google_tool_models]


def montar_tentativas(settings: Settings, key_index: int, com_tools: bool) -> list[Tentativa]:
    if com_tools:
        return _tentativas_com_tools(settings)
    key_name, client = openrouter_client(settings, key_index)
    tentativas = [Tentativa(f"OpenRouter/{key_name}", client, model) for model in settings.modelos]
    if settings.google_api_key:
        pessoal = google_client(settings)
        modelos_google = [modelo_no_google(model) for model in settings.modelos] + list(settings.google_tool_models)
        tentativas += [Tentativa(PROVEDOR_GOOGLE, pessoal, model) for model in modelos_google]
    return tentativas


def _confirmar_proxima_chave(settings: Settings, proximo_indice: int) -> bool:
    if proximo_indice >= len(settings.api_keys):
        print("\n[rate limit] Todas as chaves do OpenRouter configuradas no .env já foram usadas.")
        return False
    resposta = input(
        f"\n[rate limit] O limite diário da chave atual foi atingido. "
        f"Seguir com {settings.key_names[proximo_indice]}? [s/N] "
    )
    return resposta.strip().lower() in {"s", "sim", "y", "yes"}


async def restaurar_sessao(session: Session | None, quantidade_itens: int) -> None:
    if session is None:
        return
    while len(await session.get_items()) > quantidade_itens:
        await session.pop_item()


async def executar(
    construir: ConstrutorAgente,
    entrada: str,
    settings: Settings,
    *,
    com_tools: bool = False,
    session: Session | None = None,
    context: Any = None,
    max_turns: int = 10,
) -> Execucao:
    configure_sdk(settings)
    itens_iniciais = len(await session.get_items()) if session else 0

    key_index = 0
    while True:
        erros: list[tuple[Tentativa, Exception]] = []
        for tentativa in montar_tentativas(settings, key_index, com_tools):
            print(f"[agente] provedor={tentativa.provedor} modelo={tentativa.model}")
            try:
                agente = construir(OpenAIChatCompletionsModel(model=tentativa.model, openai_client=tentativa.client))
                resultado = await Runner.run(agente, entrada, session=session, context=context, max_turns=max_turns)
            except Exception as erro:
                await restaurar_sessao(session, itens_iniciais)
                erros.append((tentativa, erro))
                print(f"[agente] falha: {type(erro).__name__}: {erro}")
                continue
            return Execucao(resultado, tentativa.provedor, tentativa.model)

        limite_de_chave = any(
            _e_limite_da_chave(erro) for tentativa, erro in erros if tentativa.provedor.startswith("OpenRouter")
        )
        if limite_de_chave and _confirmar_proxima_chave(settings, key_index + 1):
            key_index += 1
            continue

        relatorio = "\n\n".join(
            f"[{tentativa.provedor} | {tentativa.model}] {type(erro).__name__}: {erro}" for tentativa, erro in erros
        )
        salvar_registro(
            "erro",
            "Execução — falha em todas as tentativas",
            {},
            [Secao("Entrada", entrada), Secao("Erros", relatorio)],
        )

        if all(_e_limite_do_provedor(erro) for _, erro in erros):
            raise RateLimitAtingido(
                "Todos os provedores e modelos configurados estão sob rate limit upstream. "
                "Tente novamente em alguns minutos."
            )
        if limite_de_chave:
            raise RateLimitAtingido("Limite de requisições da chave atingido e nenhuma chave alternativa foi autorizada.")
        raise FalhaDeExecucao(f"Execução falhou em todas as tentativas:\n\n{relatorio}")
