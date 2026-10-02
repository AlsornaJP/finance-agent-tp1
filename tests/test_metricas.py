from pathlib import Path

import pytest

from evaluation import metricas
from evaluation.gabarito import carregar_gabarito


def test_saidas_do_csv_ignora_entradas():
    saidas = metricas.saidas_do_csv(Path("samples/extrato_2_meses.csv"))
    assert len(saidas) == 30 and ("ALUGUEL APTO 302", 1450.0) in saidas


def test_totais_esperados_do_extrato_2_meses():
    totais = metricas.totais_esperados(metricas.saidas_do_csv(Path("samples/extrato_2_meses.csv")), carregar_gabarito())
    assert totais["Alimentação"] == pytest.approx(3236.05)
    assert round(sum(totais.values()), 2) == 8325.65


def test_precisao_numerica_conta_categorias_exatas_e_ausentes():
    esperados = {"Lazer": 72.0, "Moradia": 1654.1, "Compras": 10.0}
    obtidos = {"Lazer": 72.0, "Moradia": 1650.0, "Saúde": 5.0}
    assert metricas.precisao_numerica(obtidos, esperados) == pytest.approx(1 / 4)


def test_acuracia_classificacao_pareia_por_descricao_e_valor():
    saidas = [("UBER *TRIP", 20.0), ("UBER *TRIP", 30.0), ("NETFLIX.COM", 39.9)]
    gabarito = {"UBER *TRIP": "Transporte", "NETFLIX.COM": "Serviços/Assinaturas"}
    obtidas = [("UBER *TRIP", 20.0, "Transporte"), ("NETFLIX.COM", 39.9, "Lazer"), ("INVENTADA", 1.0, "Lazer")]
    assert metricas.acuracia_classificacao(obtidas, saidas, gabarito) == pytest.approx(1 / 3)


def test_rastreabilidade_conta_valores_presentes_nas_tools():
    assert metricas.rastreabilidade([2853.25, 63.41, 999.0], [2853.25, 3.0, 63.41]) == pytest.approx(2 / 3)
    assert metricas.rastreabilidade([], [1.0]) == 1.0


def test_acertou_com_tolerancia():
    assert metricas.acertou([10.0, 2853.25], 2853.25)
    assert not metricas.acertou([2853.0], 2853.25)


def test_numeros_no_texto_le_formato_brasileiro_e_ignora_anos():
    texto = "Em abril de 2024 você gastou R$ 2.853,25 (63,41% da renda), em 3 transações, totalizando R$ 3183,55."
    assert metricas.numeros_no_texto(texto) == [2853.25, 63.41, 3.0, 3183.55]
