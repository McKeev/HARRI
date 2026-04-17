# -----------------------------------------------------------------------------
# ========================== IMPORTS AND CONSTANTS ============================
# -----------------------------------------------------------------------------
# First Party Imports
import datetime as dt
from pathlib import Path
import logging
# Third Party Imports
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from jinja2 import Template
# Local Imports
import fin_db as fdb
# Constants
FILE_DIR = Path(__file__).parent
# Setup logger
logger = fdb.setup_logger('parser_agent')


# -----------------------------------------------------------------------------
# =============================== AGENT SETUP =================================
# -----------------------------------------------------------------------------
provider = OllamaProvider(base_url="http://localhost:11434/v1")
model = OpenAIChatModel('qwen2.5:1.5b', provider=provider)


class ParsedOutput(BaseModel):
    assets: list[str] = Field(
        description="List unmodified asset name(s) mentioned in the user query"
    )
    start_date: str = Field(
        description="Start date for the requested time range"
    )
    end_date: str = Field(
        description="End date for the requested time range"
    )


parser_agent = Agent(
    model,
    model_settings=ModelSettings(
        max_tokens=100,
        temperature=0.0,
        top_p=1.0,
    ),
    output_type=ParsedOutput
)


# System prompt
@parser_agent.system_prompt
def build_prompt() -> str:
    prompt_text = (FILE_DIR / 'prompts' / 'parser.md').read_text()
    today = dt.date.today()

    context = {
        'today': today.strftime('%Y-%m-%d'),
        'year': today.year,
        'yesterday': (today - dt.timedelta(days=1)).strftime('%Y-%m-%d'),
    }

    return Template(prompt_text).render(**context)


if __name__ == '__main__':
    print(build_prompt())
    user_query = "How is louis's portfolio doing YTD?"
    result = parser_agent.run_sync(user_prompt=user_query)
    print(result.output)
