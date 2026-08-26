from agents import Agent, AgentOutputSchema, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from agent.prompts import INSTRUCTIONS_PARTE_3, INSTRUCTIONS_PARTE_4, INSTRUCTIONS_PARTE_5
from agent.schema import AnaliseFinanceira

INSTRUCTIONS_POR_ETAPA = {
    "parte3": INSTRUCTIONS_PARTE_3,
    "parte4": INSTRUCTIONS_PARTE_4,
    "parte5": INSTRUCTIONS_PARTE_5,
}


def build_agent(etapa: str, model: str, client: AsyncOpenAI | None = None) -> Agent:
    return Agent(
        name="Analista de Finanças Pessoais",
        instructions=INSTRUCTIONS_POR_ETAPA[etapa],
        model=OpenAIChatCompletionsModel(model=model, openai_client=client) if client else model,
        output_type=AgentOutputSchema(AnaliseFinanceira, strict_json_schema=False)
        if etapa == "parte5"
        else None,
    )
