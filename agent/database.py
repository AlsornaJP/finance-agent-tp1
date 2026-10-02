import csv
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from agent.schema import ClassificacaoTransacao, ResultadoImportacao, TransacaoParaClassificar

CAMINHO_BANCO_PADRAO = Path("data/financas.db")

ESQUEMA = """
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
