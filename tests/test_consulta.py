from agent.consulta import texto_memoria


def test_texto_memoria_guarda_pergunta_e_resposta():
    assert texto_memoria("Minha meta de lazer é R$ 600", "Anotado.") == (
        "Pergunta do usuário: Minha meta de lazer é R$ 600\nResposta do assistente: Anotado."
    )
