import asyncio

import pytest
from agents import SQLiteSession

from agent.config import ConfigError, Settings
from agent.runner import montar_tentativas, restaurar_sessao


def _settings(google_api_key="chave-google", google_tool_models=("gemini-3.5-flash-lite",)):
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
        google_tool_models=google_tool_models,
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


def test_tentativas_sem_tools_seguem_cadeia_gemma_com_gemini_por_ultimo():
    tentativas = montar_tentativas(_settings(), 0, com_tools=False)
    assert [(t.provedor, t.model) for t in tentativas] == [
        ("OpenRouter/OPENAI_API_KEY", "google/gemma-4-31b-it:free"),
        ("GoogleAIStudio/chave-pessoal", "gemma-4-31b-it"),
        ("GoogleAIStudio/chave-pessoal", "gemini-3.5-flash-lite"),
    ]


def test_tentativas_com_tools_usam_apenas_modelos_de_tools():
    tentativas = montar_tentativas(_settings(), 0, com_tools=True)
    assert [(t.provedor, t.model) for t in tentativas] == [("GoogleAIStudio/chave-pessoal", "gemini-3.5-flash-lite")]


def test_tentativas_com_tools_sem_configuracao_falham_com_mensagem():
    with pytest.raises(ConfigError, match="GOOGLE_TOOL_MODELS"):
        montar_tentativas(_settings(google_tool_models=()), 0, com_tools=True)
    with pytest.raises(ConfigError, match="GOOGLE_API_KEY"):
        montar_tentativas(_settings(google_api_key=""), 0, com_tools=True)
