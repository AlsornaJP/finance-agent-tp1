import json
from datetime import datetime
from pathlib import Path

DIRETORIO_LOGS = Path("prompts/outputs")
ALUNO = "João Pedro Jacob"
DISCIPLINA = "26E3_5"


def _cabecalho(etapa: str, model: str, key_name: str, csv_path: str, instructions: str, csv_text: str) -> str:
    return (
        f"# Execução — {etapa}\n\n"
        f"**Aluno:** {ALUNO} · **Disciplina:** {DISCIPLINA}\n\n"
        f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Modelo: {model}\n"
        f"- Chave de API: {key_name}\n"
        f"- CSV de entrada: {csv_path}\n\n"
        "## Instructions enviadas ao agente\n\n"
        f"```text\n{instructions}\n```\n\n"
        "## Input (CSV bruto)\n\n"
        f"```csv\n{csv_text.strip()}\n```\n\n"
    )


def salvar_log(
    etapa: str,
    model: str,
    key_name: str,
    csv_path: str,
    instructions: str,
    csv_text: str,
    resultado: str | None = None,
    erro: str | None = None,
) -> Path:
    DIRETORIO_LOGS.mkdir(parents=True, exist_ok=True)
    sufixo = "erro" if erro else Path(csv_path).stem
    destino = DIRETORIO_LOGS / f"{etapa}_{sufixo}_{datetime.now():%Y%m%d-%H%M%S}.md"

    corpo = _cabecalho(etapa, model, key_name, csv_path, instructions, csv_text)
    if erro:
        corpo += f"## Erro\n\n```text\n{erro}\n```\n"
    else:
        corpo += f"## Output\n\n```{'json' if etapa == 'parte5' else 'text'}\n{resultado}\n```\n"

    destino.write_text(corpo, encoding="utf-8")
    return destino


def salvar_json(etapa: str, csv_path: str, dados: dict) -> Path:
    DIRETORIO_LOGS.mkdir(parents=True, exist_ok=True)
    destino = DIRETORIO_LOGS / f"{etapa}_{Path(csv_path).stem}_{datetime.now():%Y%m%d-%H%M%S}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino
