import csv
from pathlib import Path

from agent import database
from agent.schema import ClassificacaoTransacao

CAMINHO_GABARITO = Path(__file__).parent / "gabarito_categorias.csv"


def carregar_gabarito() -> dict[str, str]:
    with CAMINHO_GABARITO.open(encoding="utf-8", newline="") as arquivo:
        return {linha["descricao"]: linha["categoria"] for linha in csv.DictReader(arquivo)}


def criar_banco_gabarito(banco: Path, caminho_csv: Path) -> Path:
    gabarito = carregar_gabarito()
    database.importar_csv(banco, caminho_csv)
    pendentes = database.transacoes_sem_categoria(banco)
    sem_gabarito = sorted({t.descricao for t in pendentes if t.descricao not in gabarito})
    if sem_gabarito:
        raise ValueError(f"Descrições sem categoria no gabarito: {', '.join(sem_gabarito)}")
    database.gravar_categorias(
        banco,
        [ClassificacaoTransacao(id=t.id, justificativa="gabarito", categoria=gabarito[t.descricao]) for t in pendentes],
    )
    return banco
