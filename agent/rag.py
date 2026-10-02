import hashlib
import json
import math
from contextlib import closing
from datetime import datetime
from pathlib import Path

from agent.config import ConfigError, Settings, google_client
from agent.database import conectar
from agent.schema import TrechoRecuperado

CAMINHO_GUIA = Path("knowledge/guia_orcamento.md")
QUANTIDADE_RESULTADOS = 4
CHAVE_ASSINATURA_GUIA = "assinatura_guia"


def dividir_em_trechos(markdown: str) -> list[tuple[str, str]]:
    trechos: list[tuple[str, str]] = []
    secao: str | None = None
    linhas: list[str] = []

    def fechar_secao() -> None:
        texto = "\n".join(linhas).strip()
        if secao and texto:
            trechos.append((secao, texto))

    for linha in markdown.splitlines():
        if linha.startswith("## "):
            fechar_secao()
            secao, linhas = linha[3:].strip(), []
        elif secao is not None:
            linhas.append(linha)
    fechar_secao()
    return trechos


def similaridade_cosseno(a: list[float], b: list[float]) -> float:
    norma = math.hypot(*a) * math.hypot(*b)
    return sum(x * y for x, y in zip(a, b)) / norma if norma else 0.0


def ranquear(
    consulta: list[float], candidatos: list[tuple[str, str, list[float]]], limite: int
) -> list[TrechoRecuperado]:
    pontuados = [
        TrechoRecuperado(origem=origem, texto=texto, similaridade=round(similaridade_cosseno(consulta, vetor), 4))
        for origem, texto, vetor in candidatos
    ]
    return sorted(pontuados, key=lambda trecho: trecho.similaridade, reverse=True)[:limite]


def assinatura_indexada(banco: Path) -> str | None:
    with closing(conectar(banco)) as conexao:
        linha = conexao.execute("SELECT valor FROM metadados WHERE chave = ?", (CHAVE_ASSINATURA_GUIA,)).fetchone()
    return linha[0] if linha else None


def salvar_trechos_guia(
    banco: Path, trechos: list[tuple[str, str]], vetores: list[list[float]], assinatura: str
) -> None:
    with closing(conectar(banco)) as conexao:
        conexao.execute("DELETE FROM trechos_guia")
        conexao.executemany(
            "INSERT INTO trechos_guia (secao, texto, embedding) VALUES (?, ?, ?)",
            [(secao, texto, json.dumps(vetor)) for (secao, texto), vetor in zip(trechos, vetores)],
        )
        conexao.execute(
            "INSERT OR REPLACE INTO metadados (chave, valor) VALUES (?, ?)", (CHAVE_ASSINATURA_GUIA, assinatura)
        )
        conexao.commit()


def salvar_memoria(banco: Path, sessao: str, texto: str, vetor: list[float]) -> None:
    with closing(conectar(banco)) as conexao:
        conexao.execute(
            "INSERT INTO memorias (sessao, criado_em, texto, embedding) VALUES (?, ?, ?, ?)",
            (sessao, datetime.now().isoformat(timespec="seconds"), texto, json.dumps(vetor)),
        )
        conexao.commit()


def carregar_candidatos(banco: Path, incluir_memorias: bool = True) -> list[tuple[str, str, list[float]]]:
    with closing(conectar(banco)) as conexao:
        candidatos = [
            (f"guia: {linha['secao']}", linha["texto"], json.loads(linha["embedding"]))
            for linha in conexao.execute("SELECT secao, texto, embedding FROM trechos_guia ORDER BY id")
        ]
        if incluir_memorias:
            candidatos += [
                (
                    f"memória da sessão {linha['sessao']} ({linha['criado_em']})",
                    linha["texto"],
                    json.loads(linha["embedding"]),
                )
                for linha in conexao.execute("SELECT sessao, criado_em, texto, embedding FROM memorias ORDER BY id")
            ]
    return candidatos


async def gerar_embeddings(textos: list[str], settings: Settings) -> list[list[float]]:
    if not settings.google_api_key:
        raise ConfigError("GOOGLE_API_KEY é necessária para gerar os embeddings do RAG.")
    resposta = await google_client(settings).embeddings.create(model=settings.google_embedding_model, input=textos)
    return [item.embedding for item in resposta.data]


async def indexar_guia(banco: Path, settings: Settings, caminho: Path = CAMINHO_GUIA) -> bool:
    markdown = caminho.read_text(encoding="utf-8")
    assinatura = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if assinatura_indexada(banco) == assinatura:
        return False
    trechos = dividir_em_trechos(markdown)
    vetores = await gerar_embeddings([f"{secao}\n{texto}" for secao, texto in trechos], settings)
    salvar_trechos_guia(banco, trechos, vetores, assinatura)
    return True


async def gravar_memoria(banco: Path, sessao: str, texto: str, settings: Settings) -> None:
    vetor = (await gerar_embeddings([texto], settings))[0]
    salvar_memoria(banco, sessao, texto, vetor)


async def buscar(
    banco: Path,
    consulta: str,
    settings: Settings,
    incluir_memorias: bool = True,
    limite: int = QUANTIDADE_RESULTADOS,
) -> list[TrechoRecuperado]:
    vetor = (await gerar_embeddings([consulta], settings))[0]
    return ranquear(vetor, carregar_candidatos(banco, incluir_memorias), limite)
