from agents import Agent, AgentOutputSchema, Model

from planner.prompts import INSTRUCTIONS_PLANEJADOR
from planner.schema import PropostaDePlano
from planner.tools import FERRAMENTAS, ContextoPlanejamento


def construir_planejador(modelo: Model | str) -> Agent[ContextoPlanejamento]:
    return Agent[ContextoPlanejamento](
        name="Planejador de Metas",
        instructions=INSTRUCTIONS_PLANEJADOR,
        model=modelo,
        tools=FERRAMENTAS,
        output_type=AgentOutputSchema(PropostaDePlano, strict_json_schema=False),
    )
