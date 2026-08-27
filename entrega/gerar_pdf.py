"""Consolida spec, prompts, análise e logs em um único PDF de entrega."""

import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = Path(__file__).resolve().parent
BASE = "TP1_26E3_5_Joao_Pedro_Jacob"

ROTULOS_LOG = {
    "parte3_erro": "Parte 3 — tentativa interrompida por rate limit do OpenRouter",
    "parte3_extrato_1_mes": "Parte 3 — extrato de 1 mês (texto livre)",
    "parte4_extrato_1_mes": "Parte 4 — extrato de 1 mês (prompt refinado)",
    "parte5_extrato_1_mes_20260826-1723": "Parte 5 — extrato de 1 mês (schema do enunciado)",
    "parte5_extrato_2_meses_20260826-1723": "Parte 5 — extrato de 2 meses (schema do enunciado)",
    "parte5_extrato_1_mes_20260826-1847": "Parte 5 — extrato de 1 mês (com campo de enumeração)",
    "parte5_extrato_2_meses_20260826-1849": "Parte 5 — extrato de 2 meses (com campo de enumeração)",
}


def rotular(nome: str) -> str:
    for chave, rotulo in sorted(ROTULOS_LOG.items(), key=lambda kv: -len(kv[0])):
        if nome.startswith(chave):
            return rotulo
    return nome


def corpo(caminho: Path, remover_titulo: bool = True) -> str:
    texto = caminho.read_text(encoding="utf-8")
    texto = re.sub(r"^\*\*Aluno:\*\*.*?\n\n", "", texto, flags=re.M)
    if remover_titulo:
        texto = re.sub(r"\A# .*?\n", "", texto)
    return texto.strip()


def montar_markdown() -> Path:
    partes = ["""---
title: "TP1 — Agente de Análise de Finanças Pessoais"
subtitle: "Especificação, implementação e evidências de execução"
author: "João Pedro Jacob — Disciplina 26E3_5"
date: "Agosto de 2026"
---

# Sumário do documento

Este documento reúne, em ordem: a especificação do problema e a arquitetura inicial (Partes 1 e 2),
uma explicação do funcionamento do agente passo a passo, os prompts documentados com a anatomia de
quatro componentes (Partes 3 a 5 do trabalho), a análise dos resultados com as justificativas
técnicas, e as evidências de execução registradas em log.

O código-fonte completo está no repositório público do projeto:

<https://github.com/AlsornaJP/finance-agent-tp1>
"""]

    partes.append("# Parte I — Especificação do problema e arquitetura inicial\n\n"
                  + corpo(RAIZ / "spec/TP1_spec_partes_1_2.md"))

    partes.append("# Parte II — Como o agente funciona, passo a passo\n\n"
                  + corpo(RAIZ / "spec/fluxo_de_execucao.md"))

    partes.append("# Parte III — Prompts documentados\n")
    for arq in ("parte3_instructions.md", "parte4_instructions.md", "parte5_instructions.md"):
        caminho = RAIZ / "prompts" / arq
        titulo = caminho.read_text(encoding="utf-8").split("\n")[0].lstrip("# ")
        partes.append(f"## {titulo}\n\n" + corpo(caminho))

    partes.append("# Parte IV — Análise dos resultados e justificativas técnicas\n\n"
                  + corpo(RAIZ / "prompts/analise_resultados.md"))

    partes.append("# Parte V — Evidências de execução\n\n"
                  "Os logs abaixo reproduzem o cabeçalho de cada execução e a resposta do modelo. "
                  "As *instructions* enviadas foram omitidas por já constarem da Parte III, e os CSVs "
                  "de entrada constam do apêndice.")

    for log in sorted((RAIZ / "prompts/outputs").glob("*.md")):
        texto = re.sub(r"^\*\*Aluno:\*\*.*?\n\n", "", log.read_text(encoding="utf-8"), flags=re.M)
        cabecalho = re.sub(r"\A# Execução — \w+\n", "", texto.split("## Instructions")[0]).strip()
        saida = ""
        for marcador in ("## Output", "## Erro"):
            if marcador in texto:
                saida = marcador.replace("## ", "### ") + texto.split(marcador, 1)[1]
                break
        partes.append(f"## {rotular(log.name)}\n\n{cabecalho}\n\n*Arquivo: `{log.name}`*\n\n{saida.strip()}")

    partes.append("# Apêndice A — CSVs de teste\n")
    for csv in ("samples/extrato_1_mes.csv", "samples/extrato_2_meses.csv"):
        conteudo = (RAIZ / csv).read_text(encoding="utf-8").strip()
        partes.append(f"## `{csv}`\n\n```csv\n{conteudo}\n```")

    partes.append("# Apêndice B — Saídas validadas pelo schema Pydantic\n")
    for arquivo in sorted((RAIZ / "prompts/outputs").glob("*.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        corpo_json = json.dumps(dados, ensure_ascii=False, indent=2)
        partes.append(f"## {rotular(arquivo.name)}\n\n*Arquivo: `{arquivo.name}`*\n\n"
                      f"```json\n{corpo_json}\n```")

    destino = DESTINO / f"{BASE}.md"
    destino.write_text("\n\n".join(partes) + "\n", encoding="utf-8")
    return destino


def gerar_pdf(markdown: Path) -> Path:
    pdf = DESTINO / f"{BASE}.pdf"
    subprocess.run(
        ["pandoc", str(markdown), "--pdf-engine=weasyprint", f"--css={DESTINO / 'estilo.css'}",
         "--toc", "--toc-depth=2", "--standalone", "-o", str(pdf)],
        check=True, capture_output=True,
    )
    return pdf


if __name__ == "__main__":
    md = montar_markdown()
    pdf = gerar_pdf(md)
    print(f"markdown: {md.relative_to(RAIZ)} ({md.stat().st_size // 1024} KB)")
    print(f"pdf     : {pdf.relative_to(RAIZ)} ({pdf.stat().st_size // 1024} KB)")
