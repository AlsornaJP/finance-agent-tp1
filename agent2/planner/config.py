import os
from dataclasses import dataclass

from agents import set_default_openai_api, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

GOOGLE_BASE_URL_PADRAO = "https://generativelanguage.googleapis.com/v1beta/openai/"
TIMEOUT_REQUISICAO_SEGUNDOS = 180.0
RETENTATIVAS_POR_REQUISICAO = 1


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    google_base_url: str
    gemini_models: tuple[str, ...]
    tracing_disabled: bool


def load_settings() -> Settings:
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not google_api_key:
        raise ConfigError("Variável de ambiente obrigatória ausente ou vazia: GOOGLE_API_KEY")
    gemini_models = tuple(modelo.strip() for modelo in os.getenv("GEMINI_MODELS", "").split(",") if modelo.strip())
    if not gemini_models:
        raise ConfigError("Informe ao menos um modelo em GEMINI_MODELS, ex.: gemini-3.5-flash-lite.")
    return Settings(
        google_api_key=google_api_key,
        google_base_url=os.getenv("GOOGLE_BASE_URL", "").strip() or GOOGLE_BASE_URL_PADRAO,
        gemini_models=gemini_models,
        tracing_disabled=os.getenv("OPENAI_AGENTS_DISABLE_TRACING", "0").strip() == "1",
    )


def configure_sdk(settings: Settings) -> None:
    set_default_openai_api("chat_completions")
    set_tracing_disabled(settings.tracing_disabled)


def google_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.google_api_key,
        base_url=settings.google_base_url,
        timeout=TIMEOUT_REQUISICAO_SEGUNDOS,
        max_retries=RETENTATIVAS_POR_REQUISICAO,
    )
