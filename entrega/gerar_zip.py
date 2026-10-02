"""Monta o ZIP de arquivamento com todos os arquivos versionados."""

import argparse
import subprocess
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def arquivos_versionados() -> list[str]:
    saida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True)
    return [linha for linha in saida.stdout.splitlines() if linha]


def gerar_zip(prefixo: str, extras: list[str]) -> Path:
    destino = RAIZ / "entrega" / f"{prefixo}.zip"
    destino.unlink(missing_ok=True)
    faltando = [extra for extra in extras if not (RAIZ / extra).exists()]
    if faltando:
        raise SystemExit(f"Arquivo esperado não encontrado: {', '.join(faltando)}")
    caminhos = arquivos_versionados() + extras
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zip_saida:
        for relativo in caminhos:
            zip_saida.write(RAIZ / relativo, f"{prefixo}/{relativo}")
    print(f"{destino.relative_to(RAIZ)}: {len(caminhos)} arquivos, {destino.stat().st_size // 1024} KB")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o ZIP de entrega")
    parser.add_argument("prefixo", help="ex.: joao_jacob_PB_TP2")
    parser.add_argument("--extra", action="append", default=[], help="arquivo não versionado a incluir")
    argumentos = parser.parse_args()
    gerar_zip(argumentos.prefixo, argumentos.extra)
