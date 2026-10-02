import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

Gasto = tuple[str, float]
TOLERANCIA = 0.01
PADRAO_NUMERO_BR = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")
FAIXA_DE_ANOS = range(1900, 2101)


def saidas_do_csv(caminho: Path) -> list[Gasto]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [
        (linha["descrição"].strip(), round(abs(float(linha["valor"])), 2))
        for linha in linhas
        if float(linha["valor"]) < 0
    ]


def totais_esperados(saidas: list[Gasto], gabarito: dict[str, str]) -> dict[str, float]:
    totais: dict[str, float] = defaultdict(float)
    for descricao, valor in saidas:
        totais[gabarito[descricao]] += valor
    return {categoria: round(total, 2) for categoria, total in totais.items()}


def precisao_numerica(obtidos: dict[str, float], esperados: dict[str, float]) -> float:
    categorias = obtidos.keys() | esperados.keys()
    exatas = sum(
        1
        for categoria in categorias
        if categoria in obtidos
        and categoria in esperados
        and abs(obtidos[categoria] - esperados[categoria]) <= TOLERANCIA
    )
    return exatas / len(categorias) if categorias else 1.0


def acuracia_classificacao(
    obtidas: list[tuple[str, float, str]], saidas: list[Gasto], gabarito: dict[str, str]
) -> float:
    disponiveis = Counter((descricao, round(valor, 2), categoria) for descricao, valor, categoria in obtidas)
    acertos = 0
    for descricao, valor in saidas:
        chave = (descricao, round(valor, 2), gabarito[descricao])
        if disponiveis[chave] > 0:
            disponiveis[chave] -= 1
            acertos += 1
    return acertos / len(saidas) if saidas else 1.0


def _contem(numeros: list[float], alvo: float) -> bool:
    return any(abs(numero - alvo) <= TOLERANCIA for numero in numeros)


def rastreabilidade(citados: list[float], numeros_das_tools: list[float]) -> float:
    if not citados:
        return 1.0
    return sum(_contem(numeros_das_tools, valor) for valor in citados) / len(citados)


def acertou(citados: list[float], esperado: float) -> bool:
    return _contem(citados, esperado)


def numeros_no_texto(texto: str) -> list[float]:
    numeros = [float(bruto.replace(".", "").replace(",", ".")) for bruto in PADRAO_NUMERO_BR.findall(texto)]
    return [numero for numero in numeros if not (numero.is_integer() and int(numero) in FAIXA_DE_ANOS)]
