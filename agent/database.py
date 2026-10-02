import csv
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

from agent.schema import (
    CATEGORIAS,
    ClassificacaoTransacao,
    ComparacaoMensal,
    GastoCategoria,
    ResultadoImportacao,
    TotalMes,
    Transacao,
    TransacaoAtipica,
    TransacaoParaClassificar,
)

CAMINHO_BANCO_PADRAO = Path("data/financas.db")
FATOR_ATIPICO = 10.0
MINIMO_COMPARACOES_ATIPICO = 2
SEM_CATEGORIA = "Pendente de classificação"
PADRAO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

ESQUEMA = """
BEGIN;
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    categoria TEXT,
    justificativa TEXT,
    arquivo_origem TEXT NOT NULL,
    ocorrencia INTEGER NOT NULL,
    UNIQUE (data, descricao, valor, tipo, ocorrencia)
);
CREATE TABLE IF NOT EXISTS trechos_guia (
    id INTEGER PRIMARY KEY,
    secao TEXT NOT NULL,
    texto TEXT NOT NULL,
    embedding TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memorias (
    id INTEGER PRIMARY KEY,
    sessao TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    texto TEXT NOT NULL,
    embedding TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metadados (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
COMMIT;
"""

COLUNAS_DESCRICAO = ("descrição", "descricao")


class ErroDeImportacao(ValueError):
    pass


def conectar(banco: Path) -> sqlite3.Connection:
    banco.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(banco)
    conexao.row_factory = sqlite3.Row
    conexao.executescript(ESQUEMA)
    return conexao


def _ler_registros(caminho_csv: Path) -> list[tuple]:
    with caminho_csv.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        colunas = set(leitor.fieldnames or ())
        coluna_descricao = next((nome for nome in COLUNAS_DESCRICAO if nome in colunas), None)
        faltando = [nome for nome in ("data", "valor") if nome not in colunas]
        if coluna_descricao is None:
            faltando.append("descrição")
        if faltando:
            raise ErroDeImportacao(f"{caminho_csv.name}: colunas obrigatórias ausentes: {', '.join(faltando)}")

        ocorrencias: Counter[tuple] = Counter()
        registros = []
        for numero_linha, linha in enumerate(leitor, start=2):
            try:
                valor = float(linha["valor"])
            except (TypeError, ValueError):
                raise ErroDeImportacao(
                    f"{caminho_csv.name}, linha {numero_linha}: valor inválido {linha['valor']!r}"
                ) from None
            tipo = (linha.get("tipo") or "").strip() or ("entrada" if valor > 0 else "saida")
            chave = (linha["data"].strip(), linha[coluna_descricao].strip(), round(abs(valor), 2), tipo)
            ocorrencias[chave] += 1
            registros.append((*chave, caminho_csv.name, ocorrencias[chave]))
        return registros


def importar_csv(banco: Path, caminho_csv: Path) -> ResultadoImportacao:
    registros = _ler_registros(caminho_csv)
    with closing(conectar(banco)) as conexao:
        antes = conexao.total_changes
        conexao.executemany(
            "INSERT OR IGNORE INTO transacoes (data, descricao, valor, tipo, arquivo_origem, ocorrencia) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            registros,
        )
        inseridas = conexao.total_changes - antes
        conexao.commit()
    return ResultadoImportacao(inseridas=inseridas, ignoradas=len(registros) - inseridas)


def transacoes_sem_categoria(banco: Path) -> list[TransacaoParaClassificar]:
    with closing(conectar(banco)) as conexao:
        linhas = conexao.execute(
            "SELECT id, descricao, valor FROM transacoes "
            "WHERE tipo = 'saida' AND categoria IS NULL ORDER BY data, id"
        ).fetchall()
    return [TransacaoParaClassificar(**dict(linha)) for linha in linhas]


def gravar_categorias(banco: Path, classificacoes: list[ClassificacaoTransacao]) -> None:
    with closing(conectar(banco)) as conexao:
        conexao.executemany(
            "UPDATE transacoes SET categoria = ?, justificativa = ? WHERE id = ?",
            [(item.categoria, item.justificativa, item.id) for item in classificacoes],
        )
        conexao.commit()


def validar_mes(mes: str) -> str:
    if not PADRAO_MES.match(mes):
        raise ValueError(f"Mês inválido: {mes!r}. Use o formato AAAA-MM, por exemplo 2024-04.")
    return mes


def mes_anterior(mes: str) -> str:
    ano, numero = map(int, validar_mes(mes).split("-"))
    return f"{ano - 1}-12" if numero == 1 else f"{ano}-{numero - 1:02d}"


def _percentual(parte: float, todo: float) -> float | None:
    return round(parte / todo * 100, 2) if todo else None


def _soma(conexao: sqlite3.Connection, tipo: str, mes: str) -> tuple[float, int]:
    total, quantidade = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0), COUNT(*) FROM transacoes WHERE tipo = ? AND substr(data, 1, 7) = ?",
        (tipo, mes),
    ).fetchone()
    return round(total, 2), quantidade


def _totais_por_categoria(conexao: sqlite3.Connection, mes: str) -> dict[str, tuple[float, int]]:
    linhas = conexao.execute(
        "SELECT COALESCE(categoria, ?) AS categoria, SUM(valor) AS total, COUNT(*) AS quantidade "
        "FROM transacoes WHERE tipo = 'saida' AND substr(data, 1, 7) = ? GROUP BY 1",
        (SEM_CATEGORIA, mes),
    ).fetchall()
    return {linha["categoria"]: (round(linha["total"], 2), linha["quantidade"]) for linha in linhas}


def meses_disponiveis(banco: Path) -> list[str]:
    with closing(conectar(banco)) as conexao:
        linhas = conexao.execute("SELECT DISTINCT substr(data, 1, 7) FROM transacoes ORDER BY 1").fetchall()
    return [linha[0] for linha in linhas]


def gasto_total_mes(banco: Path, mes: str) -> TotalMes:
    validar_mes(mes)
    with closing(conectar(banco)) as conexao:
        gasto, quantidade = _soma(conexao, "saida", mes)
        renda, _ = _soma(conexao, "entrada", mes)
    return TotalMes(
        mes=mes,
        total_gasto=gasto,
        quantidade_transacoes=quantidade,
        renda=renda,
        percentual_renda_gasto=_percentual(gasto, renda),
    )


def gastos_por_categoria(banco: Path, mes: str) -> list[GastoCategoria]:
    validar_mes(mes)
    with closing(conectar(banco)) as conexao:
        totais = _totais_por_categoria(conexao, mes)
        gasto, _ = _soma(conexao, "saida", mes)
        renda, _ = _soma(conexao, "entrada", mes)
    categorias = [
        GastoCategoria(
            categoria=categoria,
            valor_total=valor,
            quantidade_transacoes=quantidade,
            percentual_do_total=_percentual(valor, gasto),
            percentual_da_renda=_percentual(valor, renda),
        )
        for categoria, (valor, quantidade) in totais.items()
    ]
    return sorted(categorias, key=lambda item: item.valor_total, reverse=True)


def comparar_meses(banco: Path, mes_atual: str, mes_anterior: str) -> list[ComparacaoMensal]:
    validar_mes(mes_atual)
    validar_mes(mes_anterior)
    with closing(conectar(banco)) as conexao:
        atual = _totais_por_categoria(conexao, mes_atual)
        anterior = _totais_por_categoria(conexao, mes_anterior)
    comparacao = []
    for categoria in sorted(atual.keys() | anterior.keys()):
        valor_atual = atual.get(categoria, (0.0, 0))[0]
        valor_anterior = anterior.get(categoria, (0.0, 0))[0]
        diferenca = round(valor_atual - valor_anterior, 2)
        comparacao.append(
            ComparacaoMensal(
                categoria=categoria,
                valor_atual=valor_atual,
                valor_anterior=valor_anterior,
                diferenca=diferenca,
                variacao_percentual=_percentual(diferenca, valor_anterior),
            )
        )
    return comparacao


def transacoes_atipicas(banco: Path, mes: str) -> list[TransacaoAtipica]:
    validar_mes(mes)
    with closing(conectar(banco)) as conexao:
        saidas = conexao.execute(
            "SELECT id, data, descricao, valor, COALESCE(categoria, ?) AS categoria "
            "FROM transacoes WHERE tipo = 'saida' ORDER BY data, id",
            (SEM_CATEGORIA,),
        ).fetchall()
    valores_por_categoria: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for saida in saidas:
        valores_por_categoria[saida["categoria"]].append((saida["id"], saida["valor"]))

    atipicas = []
    for saida in saidas:
        if not saida["data"].startswith(mes):
            continue
        demais = [valor for id_, valor in valores_por_categoria[saida["categoria"]] if id_ != saida["id"]]
        if len(demais) < MINIMO_COMPARACOES_ATIPICO:
            continue
        media = statistics.mean(demais)
        razao = saida["valor"] / media
        if razao > FATOR_ATIPICO:
            atipicas.append(
                TransacaoAtipica(
                    data=saida["data"],
                    descricao=saida["descricao"],
                    valor=saida["valor"],
                    categoria=saida["categoria"],
                    media_categoria=round(media, 2),
                    razao=round(razao, 1),
                )
            )
    return atipicas


def listar_transacoes(banco: Path, mes: str, categoria: str | None = None) -> list[Transacao]:
    validar_mes(mes)
    if categoria is not None and categoria not in CATEGORIAS:
        raise ValueError(f"Categoria desconhecida: {categoria!r}. Categorias válidas: {', '.join(CATEGORIAS)}.")
    consulta = "SELECT id, data, descricao, valor, tipo, categoria FROM transacoes WHERE substr(data, 1, 7) = ?"
    parametros: list[str] = [mes]
    if categoria is not None:
        consulta += " AND categoria = ?"
        parametros.append(categoria)
    with closing(conectar(banco)) as conexao:
        linhas = conexao.execute(consulta + " ORDER BY data, id", parametros).fetchall()
    return [Transacao(**dict(linha)) for linha in linhas]
