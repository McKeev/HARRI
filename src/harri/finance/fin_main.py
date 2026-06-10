# --------------------------------------------------------------------------------------
# IMPORTS AND SETUP
# --------------------------------------------------------------------------------------
# Standard Library Imports
from dataclasses import dataclass
from logging import getLogger

# Third-Party Imports
import fin_db as fdb
import numpy as np
import pandas as pd
from async_lru import alru_cache
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

# Local imports
from harri.finance.data import Asset
from harri.finance.parser import ParseDeps, ParsedOutput, parser_agent
from harri.memory import User

# Logger setup
logger = getLogger(__name__)

# --------------------------------------------------------------------------------------
# AGENT SETUP
# --------------------------------------------------------------------------------------


# Works with env var `OPENAI_API_KEY` by default
provider = OpenAIProvider()
model = OpenAIChatModel("gpt-5.4-nano", provider=provider)


@dataclass
class FinDeps:
    """
    Dependencies for the finance agent.

    Attributes:
    -----------
    start_date: str
        The start date for the financial data query in YYYY-MM-DD format.
    end_date: str
        The end date for the financial data query in YYYY-MM-DD format.
    assets: list[dict[str, Asset]]
        A list of dictionaries mapping the original user input (e.g., "AAPL") to the
        corresponding Asset data structure.
    portfolios: list[Asset]
        A list of portfolios represented as Asset data structures.
    """

    start_date: str
    end_date: str
    assets: list[dict[str, Asset]]
    portfolios: list[Asset]


finance_agent = Agent(
    model,
    deps_type=ParseDeps,
    output_type=ParsedOutput,
    model_settings=ModelSettings(
        temperature=0.3,
    ),
)


# --------------------------------------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------------------------------------


@alru_cache(ttl=3600)  # Cache 1hr
async def possible_portfolios() -> list[str]:
    """Fetches a list of possible portfolio tickers from the database."""
    pool = fdb.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                # sql
                """
                SELECT internal_ticker FROM instruments
                WHERE asset_class = 'portfolio';
                """
            )
            rows = await cur.fetchall()
            return [row[0] for row in rows]


# --------------------------------------------------------------------------------------
# MAIN LOGIC FLOW
# --------------------------------------------------------------------------------------


async def finance_query(query: str, user: User):
    """Main function to process a finance-related user query"""
    # Parse query
    result = await parser_agent.run(
        deps=ParseDeps(
            user=user.name,
            possible_portfolios=await possible_portfolios(),
        ),
        user_prompt=query,
    )
    parsed: ParsedOutput = result.output
    logger.debug(f"Parsed query: {parsed}")

    # Build translations
    if parsed.assets:
        translations = await fdb.resolve_instruments_async(parsed.assets)
        if translations is not None:
            translations = translations.set_index("raw_input")[
                ["internal_ticker", "name"]
            ].to_dict(orient="index")  # type: ignore
            unresolved = set(parsed.assets) - set(translations.keys())
        else:
            unresolved = set(parsed.assets)
    else:
        translations = {}
        unresolved = set()

    # Get data
    tickers = [t["internal_ticker"] for t in translations.values()] + parsed.portfolios
    if not tickers:
        logger.warning("No valid assets or portfolios found in the query.")
        return {
            "error": "No valid assets or portfolios found in the query.",
            "unresolved_assets": list(unresolved),
            "prose": (
                "Please check the asset names and portfolio names in your query "
                "and try again."
            ),
        }
    data = await fdb.get_hist_async(
        tickers=tickers,
        fields=["totret", "close"],
        sdate=parsed.start_date,
        edate=parsed.end_date,
    )

    # Wrap
    assets = []
    for raw_input, info in translations.items():
        ticker = info["internal_ticker"]
        asset_data = data[ticker].dropna()
        asset = Asset(
            name=info["name"],
            ticker=ticker,
            totrets=np.asarray(asset_data["totret"], dtype=np.float64),
            closes=np.asarray(asset_data["close"], dtype=np.float64),
            dates=pd.DatetimeIndex(asset_data.index),
        )
        assets.append({raw_input: asset})
    portfolios = []
    for ticker in parsed.portfolios:
        pf_data = data[ticker].dropna()
        portfolios.append(
            Asset(
                name=ticker,
                ticker=ticker,
                totrets=np.asarray(pf_data["totret"], dtype=np.float64),
                closes=np.asarray(pf_data["close"], dtype=np.float64),
                dates=pd.DatetimeIndex(pf_data.index),
            )
        )

    deps = FinDeps(
        start_date=parsed.start_date,
        end_date=parsed.end_date,
        assets=assets,
        portfolios=portfolios,
    )

    return deps
