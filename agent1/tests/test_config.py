from agent.config import TIMEOUT_REQUISICAO_SEGUNDOS, google_client, openrouter_client
from tests.test_runner import _settings


def test_clientes_tem_timeout_curto_para_cair_no_fallback():
    _, cliente_openrouter = openrouter_client(_settings(), 0)
    cliente_google = google_client(_settings())
    for cliente in (cliente_openrouter, cliente_google):
        assert cliente.timeout == TIMEOUT_REQUISICAO_SEGUNDOS
        assert cliente.max_retries == 1
