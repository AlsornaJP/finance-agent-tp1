from agent.consulta import texto_memoria


def test_texto_memoria_guarda_pergunta_e_resposta():
    assert texto_memoria("Minha meta de lazer é R$ 600", "Anotado.") == (
        "Pergunta do usuário: Minha meta de lazer é R$ 600\nResposta do assistente: Anotado."
    )


def test_falha_ao_gravar_memoria_preserva_resposta_e_log(banco_classificado, monkeypatch, tmp_path):
    import asyncio
    from types import SimpleNamespace

    from agent import consulta
    from agent.config import ConfigError
    from agent.schema import RespostaFinanceira

    async def nada(*_, **__):
        return False

    async def executar_falso(construir, entrada, settings, **_):
        resultado = SimpleNamespace(final_output=RespostaFinanceira(resposta="R$ 72,00"), new_items=[])
        return SimpleNamespace(resultado=resultado, provedor="p", modelo="m")

    async def memoria_quebrada(*_, **__):
        raise ConfigError("sem chave de embeddings")

    monkeypatch.setattr(consulta.rag, "indexar_guia", nada)
    monkeypatch.setattr(consulta, "executar", executar_falso)
    monkeypatch.setattr(consulta.rag, "gravar_memoria", memoria_quebrada)

    resultado = asyncio.run(
        consulta.perguntar(banco_classificado, "s", "Quanto gastei?", settings=None, diretorio_log=tmp_path)
    )
    assert resultado.resposta.resposta == "R$ 72,00"
    assert "sem chave de embeddings" in resultado.log.read_text(encoding="utf-8")
