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
