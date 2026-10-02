import pytest

from agent.diagnostico import levantar_mes


def test_levantamento_de_abril_compara_com_marco(banco_classificado):
    levantamento = levantar_mes(banco_classificado, "2024-04")
    assert levantamento.total.total_gasto == 5573.35
    assert levantamento.mes_anterior == "2024-03"
    assert any(c.categoria == "Transporte" and c.diferenca == 96.0 for c in levantamento.comparacao)
    assert [a.descricao for a in levantamento.atipicas] == ["RESTAURANTE OUTBACK"]


def test_levantamento_do_primeiro_mes_nao_tem_comparacao(banco_classificado):
    levantamento = levantar_mes(banco_classificado, "2024-03")
    assert levantamento.mes_anterior is None and levantamento.comparacao == []


def test_levantamento_de_mes_sem_dados_falha(banco_classificado):
    with pytest.raises(ValueError, match="2024-03, 2024-04"):
        levantar_mes(banco_classificado, "2024-09")


def test_trechos_mantem_um_item_por_ponto_mesmo_com_assunto_repetido():
    import asyncio

    from agent.diagnostico import recuperar_trechos
    from agent.schema import PontoDeAtencao, TrechoRecuperado

    pontos = [
        PontoDeAtencao(assunto="Alimentação", dados="63% da renda", motivo="peso na renda"),
        PontoDeAtencao(assunto="Alimentação", dados="+645%", motivo="crescimento"),
    ]

    async def buscar_falso(consulta: str) -> list[TrechoRecuperado]:
        return [TrechoRecuperado(origem="guia: X", texto=consulta, similaridade=1.0)]

    trechos = asyncio.run(recuperar_trechos(pontos, buscar_falso))
    assert [item["assunto"] for item in trechos] == ["Alimentação", "Alimentação"]
    assert [item["trechos"][0]["texto"] for item in trechos] == [
        "Alimentação: peso na renda",
        "Alimentação: crescimento",
    ]
