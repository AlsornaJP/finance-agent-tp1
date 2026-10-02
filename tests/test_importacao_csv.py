import sqlite3
from pathlib import Path

import pytest

from agent import database
from agent.schema import ClassificacaoTransacao

EXTRATO_2_MESES = Path("samples/extrato_2_meses.csv")


def _linhas(banco: Path) -> list[sqlite3.Row]:
    with database.conectar(banco) as conexao:
        return conexao.execute("SELECT * FROM transacoes ORDER BY id").fetchall()


def test_importa_todas_as_linhas_com_valor_positivo(banco):
    resultado = database.importar_csv(banco, EXTRATO_2_MESES)
    linhas = _linhas(banco)
    assert resultado.inseridas == 32 and resultado.ignoradas == 0
    assert all(linha["valor"] > 0 for linha in linhas)
    assert linhas[1]["descricao"] == "ALUGUEL APTO 302" and linhas[1]["tipo"] == "saida"
    assert linhas[1]["valor"] == 1450.0 and linhas[1]["arquivo_origem"] == "extrato_2_meses.csv"


def test_reimportar_nao_duplica(banco):
    database.importar_csv(banco, EXTRATO_2_MESES)
    resultado = database.importar_csv(banco, EXTRATO_2_MESES)
    assert resultado.inseridas == 0 and resultado.ignoradas == 32
    assert len(_linhas(banco)) == 32


def test_linhas_identicas_no_mesmo_arquivo_sao_mantidas(banco, tmp_path):
    csv = tmp_path / "repetidas.csv"
    csv.write_text(
        "data,descrição,valor,tipo\n2024-05-02,UBER *TRIP,-20.00,saida\n2024-05-02,UBER *TRIP,-20.00,saida\n",
        encoding="utf-8",
    )
    assert database.importar_csv(banco, csv).inseridas == 2
    assert database.importar_csv(banco, csv).inseridas == 0


def test_aceita_bom_cabecalho_sem_acento_e_tipo_ausente(banco, tmp_path):
    csv = tmp_path / "variante.csv"
    csv.write_text("﻿data,descricao,valor\n2024-05-01,SALARIO,3000.00\n2024-05-03,PADARIA,-12.50\n", encoding="utf-8")
    database.importar_csv(banco, csv)
    tipos = [(linha["descricao"], linha["tipo"], linha["valor"]) for linha in _linhas(banco)]
    assert tipos == [("SALARIO", "entrada", 3000.0), ("PADARIA", "saida", 12.5)]


def test_valor_invalido_cita_a_linha_e_nao_grava_nada(banco, tmp_path):
    csv = tmp_path / "invalido.csv"
    csv.write_text("data,descrição,valor,tipo\n2024-05-01,A,-1.00,saida\n2024-05-02,B,abc,saida\n", encoding="utf-8")
    with pytest.raises(database.ErroDeImportacao, match="linha 3"):
        database.importar_csv(banco, csv)
    assert _linhas(banco) == []


def test_coluna_obrigatoria_ausente(banco, tmp_path):
    csv = tmp_path / "sem_valor.csv"
    csv.write_text("data,descrição\n2024-05-01,A\n", encoding="utf-8")
    with pytest.raises(database.ErroDeImportacao, match="valor"):
        database.importar_csv(banco, csv)


def test_sem_categoria_lista_apenas_saidas_pendentes_e_gravar_atualiza(banco):
    database.importar_csv(banco, EXTRATO_2_MESES)
    pendentes = database.transacoes_sem_categoria(banco)
    assert len(pendentes) == 30
    primeira = pendentes[0]
    database.gravar_categorias(
        banco, [ClassificacaoTransacao(id=primeira.id, justificativa="aluguel", categoria="Moradia")]
    )
    assert len(database.transacoes_sem_categoria(banco)) == 29


def test_banco_gabarito_classifica_todas_as_saidas(banco_classificado):
    assert database.transacoes_sem_categoria(banco_classificado) == []
