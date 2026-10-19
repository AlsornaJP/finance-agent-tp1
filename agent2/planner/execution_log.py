from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DIRETORIO_LOGS = Path("prompts/outputs")
ALUNO = "João Pedro Jacob"
DISCIPLINA = "26E3_5"


@dataclass(frozen=True)
class Secao:
    titulo: str
    conteudo: str
    linguagem: str = "text"


def _destino_livre(diretorio: Path, prefixo: str) -> Path:
    base = f"{prefixo}_{datetime.now():%Y%m%d-%H%M%S}"
    destino = diretorio / f"{base}.md"
    sufixo = 2
    while destino.exists():
        destino = diretorio / f"{base}-{sufixo}.md"
        sufixo += 1
    return destino


def salvar_registro(
    prefixo: str,
    titulo: str,
    metadados: dict[str, str],
    secoes: list[Secao],
    diretorio: Path = DIRETORIO_LOGS,
) -> Path:
    diretorio.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"# {titulo}",
        "",
        f"**Aluno:** {ALUNO} · **Disciplina:** {DISCIPLINA}",
        "",
        f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}",
        *(f"- {chave}: {valor}" for chave, valor in metadados.items()),
        "",
    ]
    for secao in secoes:
        linhas += [f"## {secao.titulo}", "", f"```{secao.linguagem}", secao.conteudo.strip(), "```", ""]
    destino = _destino_livre(diretorio, prefixo)
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino
