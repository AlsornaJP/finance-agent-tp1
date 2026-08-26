import os
from dataclasses import dataclass

from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

API_KEY_VARS = ("OPENAI_API_KEY", "OPENAI_SECOND_API_KEY", "OPENAI_THIRD_API_KEY")
GOOGLE_BASE_URL_PADRAO = "https://generativelanguage.googleapis.com/v1beta/openai/"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    api_keys: tuple[str, ...]
    key_names: tuple[str, ...]
    base_url: str
    default_model: str
    fallback_model: str
    tracing_disabled: bool
    google_api_key: str
    google_base_url: str

    @property
    def modelos(self) -> tuple[str, ...]:
        if self.fallback_model == self.default_model:
            return (self.default_model,)
        return (self.default_model, self.fallback_model)


def load_settings() -> Settings:
    load_dotenv()

    keys, names = [], []
    for var in API_KEY_VARS:
        value = os.getenv(var, "").strip()
        if value:
            keys.append(value)
            names.append(var)
    if not keys:
        raise ConfigError(f"Nenhuma chave encontrada no .env (esperado ao menos {API_KEY_VARS[0]}).")

    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    default_model = os.getenv("OPENAI_DEFAULT_MODEL", "").strip()
    fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "").strip() or default_model
    for var, value in (("OPENAI_BASE_URL", base_url), ("OPENAI_DEFAULT_MODEL", default_model)):
        if not value:
            raise ConfigError(f"Variável de ambiente obrigatória ausente ou vazia: {var}")

    return Settings(
        api_keys=tuple(keys),
        key_names=tuple(names),
        base_url=base_url,
        default_model=default_model,
        fallback_model=fallback_model,
        tracing_disabled=os.getenv("OPENAI_AGENTS_DISABLE_TRACING", "0").strip() == "1",
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        google_base_url=os.getenv("GOOGLE_BASE_URL", "").strip() or GOOGLE_BASE_URL_PADRAO,
    )


def configure_sdk(settings: Settings) -> None:
    set_default_openai_api("chat_completions")
    set_tracing_disabled(settings.tracing_disabled)


def openrouter_client(settings: Settings, key_index: int) -> tuple[str, AsyncOpenAI]:
    if key_index >= len(settings.api_keys):
        raise ConfigError("Não há mais chaves de API do OpenRouter disponíveis no .env.")
    client = AsyncOpenAI(api_key=settings.api_keys[key_index], base_url=settings.base_url)
    set_default_openai_client(client, use_for_tracing=False)
    return settings.key_names[key_index], client


def google_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.google_api_key, base_url=settings.google_base_url)


def modelo_no_google(modelo_openrouter: str) -> str:
    return modelo_openrouter.removeprefix("google/").removesuffix(":free")
