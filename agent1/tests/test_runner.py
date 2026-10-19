import asyncio

import pytest
from agents import SQLiteSession

from agent.config import ConfigError, Settings
from agent.runner import montar_tentativas, restaurar_sessao


def _settings(google_api_key="chave-google", gemini_models=("gemini-3.5-flash-lite",)):
    return Settings(
        api_keys=("chave-openrouter",),
        key_names=("OPENAI_API_KEY",),
        base_url="https://openrouter.ai/api/v1",
        default_model="google/gemma-4-31b-it:free",
        fallback_model="google/gemma-4-31b-it:free",
        tracing_disabled=True,
        google_api_key=google_api_key,
        google_base_url="https://exemplo/",
        google_embedding_model="gemini-embedding-001",
        gemini_models=gemini_models,
    )


def test_restaurar_sessao_remove_itens_da_tentativa_falha():
    async def cenario():
        sessao = SQLiteSession("teste")
        await sessao.add_items([{"role": "user", "content": "pergunta antiga"}])
        quantidade_inicial = len(await sessao.get_items())
        await sessao.add_items([{"role": "user", "content": "pergunta nova"}, {"role": "assistant", "content": "x"}])
        await restaurar_sessao(sessao, quantidade_inicial)
        return await sessao.get_items()

    itens = asyncio.run(cenario())
    assert [item["content"] for item in itens] == ["pergunta antiga"]


def test_restaurar_sessao_sem_sessao_nao_faz_nada():
    asyncio.run(restaurar_sessao(None, 0))


def test_tentativas_sem_tools_comecam_pelo_gemini_e_caem_no_gemma():
    tentativas = montar_tentativas(_settings(), 0, com_tools=False)
    assert [(t.provedor, t.model) for t in tentativas] == [
        ("GoogleAIStudio/chave-pessoal", "gemini-3.5-flash-lite"),
        ("OpenRouter/OPENAI_API_KEY", "google/gemma-4-31b-it:free"),
        ("GoogleAIStudio/chave-pessoal", "gemma-4-31b-it"),
    ]


def test_tentativas_sem_chave_google_usam_so_openrouter():
    tentativas = montar_tentativas(_settings(google_api_key=""), 0, com_tools=False)
    assert [t.model for t in tentativas] == ["google/gemma-4-31b-it:free"]


def test_tentativas_com_tools_usam_apenas_gemini():
    tentativas = montar_tentativas(_settings(), 0, com_tools=True)
    assert [(t.provedor, t.model) for t in tentativas] == [("GoogleAIStudio/chave-pessoal", "gemini-3.5-flash-lite")]


def test_tentativas_com_tools_sem_configuracao_falham_com_mensagem():
    with pytest.raises(ConfigError, match="GEMINI_MODELS"):
        montar_tentativas(_settings(gemini_models=()), 0, com_tools=True)
    with pytest.raises(ConfigError, match="GOOGLE_API_KEY"):
        montar_tentativas(_settings(google_api_key=""), 0, com_tools=True)
