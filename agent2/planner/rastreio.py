from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChamadaTool:
    nome: str
    argumentos: str
    retorno: str


def _argumentos(item: Any) -> str:
    bruto = item.raw_item
    argumentos = bruto.get("arguments") if isinstance(bruto, dict) else getattr(bruto, "arguments", None)
    return argumentos or "{}"


def chamadas_de_tool(itens: list[Any]) -> list[ChamadaTool]:
    pedidos: dict[str, Any] = {}
    chamadas = []
    for item in itens:
        if item.type == "tool_call_item":
            pedidos[item.call_id] = item
        elif item.type == "tool_call_output_item" and item.call_id in pedidos:
            pedido = pedidos.pop(item.call_id)
            chamadas.append(ChamadaTool(pedido.tool_name or "desconhecida", _argumentos(pedido), str(item.output)))
    return chamadas


def formatar_chamadas(chamadas: list[ChamadaTool]) -> str:
    if not chamadas:
        return "Nenhuma tool foi chamada."
    return "\n\n".join(
        f"[{indice}] {chamada.nome}({chamada.argumentos})\n-> {chamada.retorno}"
        for indice, chamada in enumerate(chamadas, start=1)
    )
