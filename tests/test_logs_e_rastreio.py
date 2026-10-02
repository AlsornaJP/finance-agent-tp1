from types import SimpleNamespace

from agent import execution_log, rastreio


def test_salvar_registro_monta_markdown(tmp_path):
    destino = execution_log.salvar_registro(
        "perguntar_joao",
        "Execução — perguntar",
        {"Sessão": "joao"},
        [execution_log.Secao("Pergunta", "Quanto gastei?"), execution_log.Secao("Saída", '{"a": 1}', "json")],
        diretorio=tmp_path,
    )
    texto = destino.read_text(encoding="utf-8")
    assert destino.name.startswith("perguntar_joao_")
    assert "# Execução — perguntar" in texto and "- Sessão: joao" in texto
    assert "## Saída\n\n```json\n{\"a\": 1}\n```" in texto


def test_salvar_registro_nao_sobrescreve_no_mesmo_segundo(tmp_path):
    primeiro = execution_log.salvar_registro("x", "t", {}, [], diretorio=tmp_path)
    segundo = execution_log.salvar_registro("x", "t", {}, [], diretorio=tmp_path)
    assert primeiro != segundo and primeiro.exists() and segundo.exists()


def _chamada(call_id, nome, argumentos):
    return SimpleNamespace(type="tool_call_item", call_id=call_id, tool_name=nome, raw_item=SimpleNamespace(arguments=argumentos))


def _saida(call_id, output):
    return SimpleNamespace(type="tool_call_output_item", call_id=call_id, output=output)


def test_chamadas_de_tool_pareia_pedido_e_retorno():
    itens = [
        _chamada("c1", "gasto_total_mes", '{"mes": "2024-04"}'),
        SimpleNamespace(type="message_output_item"),
        _saida("c1", '{"total_gasto": 5573.35}'),
    ]
    assert rastreio.chamadas_de_tool(itens) == [
        rastreio.ChamadaTool("gasto_total_mes", '{"mes": "2024-04"}', '{"total_gasto": 5573.35}')
    ]


def test_numeros_nos_retornos_percorre_json_aninhado():
    chamadas = [
        rastreio.ChamadaTool("a", "{}", '[{"valor_total": 2853.25, "quantidade": 3, "categoria": "Alimentação"}]'),
        rastreio.ChamadaTool("b", "{}", "texto sem json"),
        rastreio.ChamadaTool("c", "{}", '{"percentual": null, "ok": true}'),
    ]
    assert sorted(rastreio.numeros_nos_retornos(chamadas)) == [3.0, 2853.25]


def test_formatar_chamadas_sem_chamadas():
    assert rastreio.formatar_chamadas([]) == "Nenhuma tool foi chamada."
