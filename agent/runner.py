from dataclasses import dataclass
from pathlib import Path

from agents import Runner
from openai import APIStatusError, AsyncOpenAI, RateLimitError

from agent.config import (
    Settings,
    configure_sdk,
    google_client,
    modelo_no_google,
    openrouter_client,
)
from agent.execution_log import salvar_json, salvar_log
from agent.finance_agent import build_agent
from agent.schema import AnaliseFinanceira

MARCADORES_LIMITE_UPSTREAM = ("upstream_provider_shared_pool", "rate-limited upstream")


class RateLimitAtingido(RuntimeError):
    pass


@dataclass(frozen=True)
class Tentativa:
    provedor: str
    client: AsyncOpenAI
    model: str


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


def _montar_tentativas(settings: Settings, key_index: int) -> tuple[str, list[Tentativa]]:
    key_name, client = openrouter_client(settings, key_index)
    tentativas = [Tentativa(f"OpenRouter/{key_name}", client, model) for model in settings.modelos]

    if settings.google_api_key:
        pessoal = google_client(settings)
        tentativas += [
            Tentativa("GoogleAIStudio/chave-pessoal", pessoal, modelo_no_google(model))
            for model in settings.modelos
        ]
    return key_name, tentativas


def _confirmar_proxima_chave(settings: Settings, proximo_indice: int) -> bool:
    if proximo_indice >= len(settings.api_keys):
        print("\n[rate limit] Todas as chaves do OpenRouter configuradas no .env já foram usadas.")
        return False
    resposta = input(
        f"\n[rate limit] O limite diário da chave atual foi atingido. "
        f"Seguir com {settings.key_names[proximo_indice]}? [s/N] "
    )
    return resposta.strip().lower() in {"s", "sim", "y", "yes"}


def _registrar_sucesso(
    etapa: str,
    tentativa: Tentativa,
    csv_path: str,
    instructions: str,
    csv_text: str,
    final_output: object,
) -> None:
    estruturado = isinstance(final_output, AnaliseFinanceira)
    log = salvar_log(
        etapa=etapa,
        model=tentativa.model,
        key_name=tentativa.provedor,
        csv_path=csv_path,
        instructions=instructions,
        csv_text=csv_text,
        resultado=final_output.model_dump_json(indent=2) if estruturado else str(final_output),
    )
    print(f"[{etapa}] log salvo em {log}")
    if estruturado:
        print(f"[{etapa}] JSON salvo em {salvar_json(etapa, csv_path, final_output.model_dump())}")


async def rodar_analise(etapa: str, csv_path: str, settings: Settings) -> object:
    csv_text = Path(csv_path).read_text(encoding="utf-8")
    instructions = build_agent(etapa, settings.default_model).instructions
    configure_sdk(settings)

    key_index = 0
    while True:
        key_name, tentativas = _montar_tentativas(settings, key_index)
        erros: list[tuple[Tentativa, Exception]] = []

        for tentativa in tentativas:
            print(f"[{etapa}] provedor={tentativa.provedor} modelo={tentativa.model} csv={csv_path}")
            try:
                agent = build_agent(etapa, tentativa.model, tentativa.client)
                final_output = (await Runner.run(agent, csv_text)).final_output
            except Exception as erro:
                erros.append((tentativa, erro))
                print(f"[{etapa}] falha: {type(erro).__name__}: {erro}")
                continue
            _registrar_sucesso(etapa, tentativa, csv_path, instructions, csv_text, final_output)
            return final_output

        limite_de_chave = any(
            _e_limite_da_chave(erro) for tentativa, erro in erros if tentativa.provedor.startswith("OpenRouter")
        )
        if limite_de_chave and _confirmar_proxima_chave(settings, key_index + 1):
            key_index += 1
            continue

        relatorio = "\n\n".join(
            f"[{tentativa.provedor} | {tentativa.model}] {type(erro).__name__}: {erro}" for tentativa, erro in erros
        )
        salvar_log(
            etapa=etapa,
            model=", ".join(sorted({t.model for t, _ in erros})),
            key_name=key_name,
            csv_path=csv_path,
            instructions=instructions,
            csv_text=csv_text,
            erro=relatorio,
        )

        if all(_e_limite_do_provedor(erro) for _, erro in erros):
            raise RateLimitAtingido(
                "Todos os provedores e modelos configurados estão sob rate limit upstream. "
                "Se o fallback do Google AI Studio estiver configurado e também falhar, "
                "tente novamente em alguns minutos ou troque OPENAI_DEFAULT_MODEL."
            )
        if limite_de_chave:
            raise RateLimitAtingido(
                "Limite de requisições da chave atingido e nenhuma chave alternativa foi autorizada."
            )
        raise RuntimeError(f"Execução falhou em todas as tentativas:\n\n{relatorio}")
