"""Monta o ZIP de arquivamento: tudo que está versionado, mais o vídeo da apresentação."""

import subprocess
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PREFIXO = "TP1_26E3_5_Joao_Pedro_Jacob"
DESTINO = RAIZ / "entrega" / f"{PREFIXO}.zip"
EXTRAS = ("entrega/TP1_26E3_5_Joao_Pedro_Jacob_video.mp4",)


def arquivos_versionados() -> list[str]:
    saida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True)
    return [linha for linha in saida.stdout.splitlines() if linha]


def main() -> None:
    DESTINO.unlink(missing_ok=True)
    caminhos = arquivos_versionados()
    faltando = [e for e in EXTRAS if not (RAIZ / e).exists()]
    if faltando:
        raise SystemExit(f"Arquivo esperado não encontrado: {', '.join(faltando)}")

    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as zip_saida:
        for relativo in caminhos + list(EXTRAS):
            zip_saida.write(RAIZ / relativo, f"{PREFIXO}/{relativo}")

    total = len(caminhos) + len(EXTRAS)
    print(f"{DESTINO.relative_to(RAIZ)}: {total} arquivos, {DESTINO.stat().st_size // 1024 // 1024} MB")


if __name__ == "__main__":
    main()
