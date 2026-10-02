from pathlib import Path

import pytest

from evaluation.gabarito import criar_banco_gabarito

EXTRATO_2_MESES = Path("samples/extrato_2_meses.csv")


@pytest.fixture
def banco(tmp_path: Path) -> Path:
    return tmp_path / "teste.db"


@pytest.fixture
def banco_classificado(banco: Path) -> Path:
    return criar_banco_gabarito(banco, EXTRATO_2_MESES)
