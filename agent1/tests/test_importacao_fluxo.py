from agent.importacao import incorporar_classificacoes
from agent.schema import ClassificacaoTransacao, TransacaoParaClassificar


def _pendente(id_):
    return TransacaoParaClassificar(id=id_, descricao=f"T{id_}", valor=10.0)


def _classificada(id_, categoria="Lazer"):
    return ClassificacaoTransacao(id=id_, justificativa="x", categoria=categoria)


def test_incorpora_ignorando_ids_inventados_e_duplicados():
    pendentes = [_pendente(1), _pendente(2), _pendente(3)]
    recebidas = [_classificada(1), _classificada(99), _classificada(1, "Compras"), _classificada(3)]
    aceitas, restantes = incorporar_classificacoes(pendentes, recebidas)
    assert [(c.id, c.categoria) for c in aceitas] == [(1, "Lazer"), (3, "Lazer")]
    assert [t.id for t in restantes] == [2]


def test_falha_na_segunda_tentativa_preserva_a_primeira(banco_classificado, monkeypatch, tmp_path):
    import asyncio
    from pathlib import Path
    from types import SimpleNamespace

    from agent import database, importacao
    from agent.runner import FalhaDeExecucao
    from agent.schema import ClassificacaoLote

    csv = tmp_path / "novas.csv"
    csv.write_text("data,descrição,valor,tipo\n2024-05-01,LOJA A,-10.00,saida\n2024-05-02,LOJA B,-20.00,saida\n", encoding="utf-8")
    database.importar_csv(banco_classificado, csv)
    primeira, _ = database.transacoes_sem_categoria(banco_classificado)
    chamadas = []

    async def executar_falso(construir, entrada, settings, **_):
        chamadas.append(entrada)
        if len(chamadas) == 2:
            raise FalhaDeExecucao("cota esgotada")
        lote = ClassificacaoLote(classificacoes=[_classificada(primeira.id, "Compras")])
        return SimpleNamespace(resultado=SimpleNamespace(final_output=lote), provedor="p", modelo="m")

    monkeypatch.setattr(importacao, "executar", executar_falso)
    relatorio = asyncio.run(importacao.classificar_pendentes(Path(banco_classificado), settings=None))

    assert [c.id for c in relatorio.classificadas] == [primeira.id]
    assert len(relatorio.nao_retornadas) == 1
    assert database.transacoes_sem_categoria(banco_classificado) == []
