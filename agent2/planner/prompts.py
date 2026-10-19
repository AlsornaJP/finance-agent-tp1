from pathlib import Path

CAMINHO_INSTRUCTIONS_PLANEJADOR = Path(__file__).resolve().parent.parent / "prompts" / "planejador_v1.md"
INSTRUCTIONS_PLANEJADOR = CAMINHO_INSTRUCTIONS_PLANEJADOR.read_text(encoding="utf-8")
