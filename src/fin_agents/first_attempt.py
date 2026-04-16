"""
File Name: helloworld.py
Author: Cedric McKeever
Date: 2026-04-15
Description:
This script served as experimentation for developing agents. This was my
first experience with pydantic_ai and agent development, so I used this script
to figure out the basics and figure out how to approach my project.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
import datetime as dt
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import logging
# Third Party Imports
import pandas as pd
from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from jinja2 import Template
# Local Imports
import fin_db as fdb


# ----------------------------------------------------------------------------
# ================================== SCRIPT ==================================
# ----------------------------------------------------------------------------


# Logging
logger = logging.getLogger(__name__)

# Agent Setup
provider = OllamaProvider(base_url="http://localhost:11434/v1")
model = OpenAIChatModel('librarian-dbagent:latest', provider=provider)


@dataclass
class State:
    data: list[pd.DataFrame] = field(default_factory=list)
    metadata: list[dict[str, Any]] = field(default_factory=list)


agent = Agent(
    model,
    deps_type=State,
    model_settings=ModelSettings(max_tokens=100)
)
logger.info('Agent initialized with model librarian-dbagent')


@agent.system_prompt
def build_prompt() -> str:
    """
    Build the prompt for the agent.
    """
    prompt_text = Path('prompt.md').read_text()
    today = dt.date.today()

    context = {
        'today': today.strftime('%Y-%m-%d'),
        'year': today.year,
    }

    return Template(prompt_text).render(**context)


@agent.tool
def names_to_tickers(
    ctx: RunContext[State],
    names: list[str]
) -> str:
    """
    Convert names into ticker symbols. Always use this tool when tickers
    are not provided by the user.

    # Parameters
    - names: A list of company names (e.g., ['Safran', 'Microsoft). Ensure you
        pass the names as provided by the user. Do not attempt to pre-clean.
    """
    logger.info('Tool called: names_to_tickers | names=%s', names)
    return {
        'Safran': 'SAF.PA',
        'Microsoft': 'MSFT',
    }


@agent.tool
def get_history(
    ctx: RunContext[State],
    tickers: str | list[str],
    fields: str | list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None
) -> str:
    """
    Get historical data for list of tickers and fields between 2 dates
    (inclusive). If user does not specify optional parameters, defaults used.
    If user does not specify fields, default is `totret`.

    # Parameters
    - tickers: A string or list of strings representing ticker symbols
        (e.g., 'AAPL', 'SAF.PA', ['AAPL', 'SAF.PA']).
    - fields: A string or list of strings. Possible values are 'close',
        'totret'. Defaults to 'totret'.
    """
    logger.info(
        'Tool called: get_history | tickers=%s fields=%s start=%s end=%s',
        tickers,
        fields,
        start_date,
        end_date,
    )

    # Normalize inputs
    if isinstance(tickers, str):
        tickers = [tickers]
    if isinstance(fields, str):
        fields = [fields]
    if not fields:
        fields = ['totret']
    if start_date is None:
        start_date = '1900-01-01'
    if end_date is None:
        end_date = dt.datetime.now().strftime('%Y-%m-%d')

    try:
        df = fdb.get_hist(
            tickers=tickers,
            fields=fields,
            sdate=start_date,
            edate=end_date
        )
        ctx.deps.data.append(df)

        ctx.deps.metadata.append({
            'tickers': tickers,
            'fields': fields,
            'start_date': df.index.min().strftime('%Y-%m-%d'),
            'end_date': df.index.max().strftime('%Y-%m-%d'),
            'row_count': len(df),
            'columns': df.columns.tolist()
        })
        logger.info(
            'Historical data retrieved and stored in state | rows=%d', len(df)
        )
        return (
            f"Retrieved {len(df)} rows for {tickers} | fields={fields} | "
            f"{df.index.min().strftime('%Y-%m-%d')} to "
            f"{df.index.max().strftime('%Y-%m-%d')}"
        )

    except Exception as e:
        logger.error('Error retrieving historical data: %s', str(e))
        return f"Error: {str(e)}"


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # Quick tests
    state = State()
    result = agent.run_sync(
        user_prompt='What were the returns for TSM in 2025?',
        deps=state,
    )
    logger.info('Agent run complete')

    print(result.output)
    print(state.data)
    print(state.metadata)
