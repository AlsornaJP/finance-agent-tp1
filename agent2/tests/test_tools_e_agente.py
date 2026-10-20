import pytest

from planner.agente import construir_planejador
from planner.config import ConfigError, load_settings
from planner.prompts import INSTRUCTIONS_PLANEJADOR


def test_planejador_tem_as_duas_tools_e_saida_tipada():
    agente = construir_planejador("modelo-falso")
    assert {tool.name for tool in agente.tools} == {"calcular_necessidade_da_meta", "simular_cortes"}
    assert agente.output_type is not None
    assert agente.instructions == INSTRUCTIONS_PLANEJADOR


def test_instructions_seguem_a_anatomia_de_quatro_componentes():
    for secao in ("# INSTRUÇÃO", "# CONTEXTO", "# EXEMPLOS", "# FORMATO DE SAÍDA"):
        assert secao in INSTRUCTIONS_PLANEJADOR


def test_load_settings_exige_chave_google(monkeypatch):
    monkeypatch.setattr("planner.config.load_dotenv", lambda: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODELS", "gemini-x")
    with pytest.raises(ConfigError, match="GOOGLE_API_KEY"):
        load_settings()


def test_load_settings_exige_ao_menos_um_modelo(monkeypatch):
    monkeypatch.setattr("planner.config.load_dotenv", lambda: None)
    monkeypatch.setenv("GOOGLE_API_KEY", "chave")
    monkeypatch.setenv("GEMINI_MODELS", " , ")
    with pytest.raises(ConfigError, match="GEMINI_MODELS"):
        load_settings()


def test_load_settings_le_modelos_em_ordem(monkeypatch):
    monkeypatch.setattr("planner.config.load_dotenv", lambda: None)
    monkeypatch.setenv("GOOGLE_API_KEY", "chave")
    monkeypatch.setenv("GEMINI_MODELS", "gemini-a, gemini-b")
    assert load_settings().gemini_models == ("gemini-a", "gemini-b")


def test_instructions_em_uso_sao_a_v2_com_valores_em_reais():
    from planner.prompts import CAMINHO_INSTRUCTIONS_PLANEJADOR

    assert CAMINHO_INSTRUCTIONS_PLANEJADOR.name == "planejador_v2.md"
    assert "R$ 1.223,35" in INSTRUCTIONS_PLANEJADOR
