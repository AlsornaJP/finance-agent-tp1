import pytest

from agent import database


def test_validar_mes_rejeita_formato_invalido():
    for invalido in ("2024-4", "abril", "2024-13", "2024/04"):
        with pytest.raises(ValueError, match="AAAA-MM"):
            database.validar_mes(invalido)
    assert database.validar_mes("2024-04") == "2024-04"


def test_mes_anterior_vira_o_ano():
    assert database.mes_anterior("2024-04") == "2024-03"
    assert database.mes_anterior("2024-01") == "2023-12"


def test_meses_disponiveis(banco_classificado):
    assert database.meses_disponiveis(banco_classificado) == ["2024-03", "2024-04"]


def test_gasto_total_mes(banco_classificado):
    abril = database.gasto_total_mes(banco_classificado, "2024-04")
    assert abril.total_gasto == 5573.35
    assert abril.quantidade_transacoes == 16
    assert abril.renda == 4500.0
    assert abril.percentual_renda_gasto == 123.85
    marco = database.gasto_total_mes(banco_classificado, "2024-03")
    assert (marco.total_gasto, marco.quantidade_transacoes) == (2752.3, 14)


def test_gasto_total_mes_sem_renda_tem_percentual_nulo(banco, tmp_path):
    csv = tmp_path / "sem_renda.csv"
    csv.write_text("data,descrição,valor,tipo\n2024-05-02,PADARIA,-10.00,saida\n", encoding="utf-8")
    database.importar_csv(banco, csv)
    assert database.gasto_total_mes(banco, "2024-05").percentual_renda_gasto is None


def test_gastos_por_categoria(banco_classificado):
    categorias = database.gastos_por_categoria(banco_classificado, "2024-04")
    assert categorias[0].categoria == "Alimentação"
    assert categorias[0].valor_total == 2853.25
    assert categorias[0].quantidade_transacoes == 3
    assert categorias[0].percentual_da_renda == 63.41
    assert round(sum(c.valor_total for c in categorias), 2) == 5573.35
    assert sum(c.quantidade_transacoes for c in categorias) == 16


def test_comparar_meses(banco_classificado):
    comparacao = {c.categoria: c for c in database.comparar_meses(banco_classificado, "2024-04", "2024-03")}
    transporte = comparacao["Transporte"]
    assert (transporte.valor_atual, transporte.valor_anterior) == (330.3, 234.3)
    assert transporte.diferenca == 96.0 and transporte.variacao_percentual == 40.97
    assert comparacao["Não identificado"].valor_anterior == 0.0
    assert comparacao["Não identificado"].variacao_percentual is None


def test_transacoes_atipicas(banco_classificado):
    atipicas = database.transacoes_atipicas(banco_classificado, "2024-04")
    assert [(a.descricao, a.valor, a.media_categoria, a.razao) for a in atipicas] == [
        ("RESTAURANTE OUTBACK", 2450.0, 157.21, 15.6)
    ]
    assert database.transacoes_atipicas(banco_classificado, "2024-03") == []


def test_listar_transacoes_filtra_por_categoria(banco_classificado):
    transporte = database.listar_transacoes(banco_classificado, "2024-04", "Transporte")
    assert [t.valor for t in transporte] == [28.7, 210.0, 41.6, 50.0]
    assert len(database.listar_transacoes(banco_classificado, "2024-04")) == 17


def test_listar_transacoes_rejeita_categoria_desconhecida(banco_classificado):
    with pytest.raises(ValueError, match="Categorias válidas"):
        database.listar_transacoes(banco_classificado, "2024-04", "Habitação")


def test_gasto_total_mes_informa_saldo_do_mes(banco_classificado):
    assert database.gasto_total_mes(banco_classificado, "2024-04").saldo == -1073.35
    assert database.gasto_total_mes(banco_classificado, "2024-03").saldo == 1747.7
