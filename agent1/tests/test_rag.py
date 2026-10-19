import pytest

from agent import rag


def test_dividir_em_trechos_por_secao_ignorando_introducao():
    markdown = "# Título\n\nIntrodução.\n\n## Moradia\n\nAté 30%.\n\n## Lazer\n\nEntre 5% e 10%.\n\n## Vazia\n\n"
    assert rag.dividir_em_trechos(markdown) == [("Moradia", "Até 30%."), ("Lazer", "Entre 5% e 10%.")]


def test_guia_real_tem_secoes():
    secoes = [secao for secao, _ in rag.dividir_em_trechos(rag.CAMINHO_GUIA.read_text(encoding="utf-8"))]
    assert "Regra 50/30/20" in secoes and "Metas pessoais" in secoes


def test_similaridade_cosseno():
    assert rag.similaridade_cosseno([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert rag.similaridade_cosseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert rag.similaridade_cosseno([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_ranquear_ordena_e_limita():
    candidatos = [("a", "texto a", [1.0, 0.0]), ("b", "texto b", [0.0, 1.0]), ("c", "texto c", [0.7, 0.7])]
    resultado = rag.ranquear([1.0, 0.1], candidatos, limite=2)
    assert [trecho.origem for trecho in resultado] == ["a", "c"]


def test_salvar_e_carregar_candidatos(banco):
    rag.salvar_trechos_guia(banco, [("Moradia", "Até 30%.")], [[0.1, 0.2]], "hash1")
    rag.salvar_memoria(banco, "joao-1", "Pergunta: meta de lazer\nResposta: anotado", [0.3, 0.4])
    assert rag.assinatura_indexada(banco) == "hash1"
    candidatos = rag.carregar_candidatos(banco)
    assert candidatos[0] == ("guia: Moradia", "Até 30%.", [0.1, 0.2])
    assert candidatos[1][0].startswith("memória da sessão joao-1")
    assert len(rag.carregar_candidatos(banco, incluir_memorias=False)) == 1


def test_reindexar_substitui_trechos(banco):
    rag.salvar_trechos_guia(banco, [("A", "a"), ("B", "b")], [[1.0], [2.0]], "hash1")
    rag.salvar_trechos_guia(banco, [("C", "c")], [[3.0]], "hash2")
    assert [c[0] for c in rag.carregar_candidatos(banco)] == ["guia: C"]
    assert rag.assinatura_indexada(banco) == "hash2"
