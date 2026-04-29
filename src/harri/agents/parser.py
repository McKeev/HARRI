# -----------------------------------------------------------------------------
# ========================== IMPORTS AND CONSTANTS ============================
# -----------------------------------------------------------------------------
# First Party Imports
from dataclasses import dataclass
import datetime as dt
from pathlib import Path
import logging
# Third Party Imports
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.settings import ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from jinja2 import Template
# Constants
FILE_DIR = Path(__file__).parent
# Setup logger
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# =============================== AGENT SETUP =================================
# -----------------------------------------------------------------------------
# Works with env var `OPENAI_API_KEY` by default
provider = OpenAIProvider()
model = OpenAIChatModel('gpt-5.4-nano', provider=provider)


@dataclass
class ParseDeps:
    user: str
    possible_portfolios: list[str]
    current_date: str = dt.date.today().strftime('%Y-%m-%d')


class ParsedOutput(BaseModel):
    assets: list[str] = Field(
        description="List unmodified asset name(s) mentioned in user query."
    )
    portfolios: list[str] = Field(
        description=(
            "List portfolios mentioned in user query."
        )
    )
    start_date: str = Field(
        description="Start date for the requested time range."
    )
    end_date: str = Field(
        description="End date for the requested time range."
    )


parser_agent = Agent(
    model,
    deps_type=ParseDeps,
    output_type=ParsedOutput,
    model_settings=ModelSettings(
        max_tokens=100,
        temperature=0.0,
        top_p=1.0,
    ),
)


# System prompt
@parser_agent.system_prompt
def build_prompt(ctx: RunContext[ParseDeps]) -> str:
    prompt_text = (FILE_DIR / 'parser.md').read_text()
    today = dt.datetime.strptime(ctx.deps.current_date, '%Y-%m-%d').date()

    vars = {
        'today': today.strftime('%Y-%m-%d'),
        'year': today.year,
        'yesterday': (today - dt.timedelta(days=1)).strftime('%Y-%m-%d'),
        'user': ctx.deps.user.upper(),
        'possible_portfolios': ctx.deps.possible_portfolios,
    }

    prompt = Template(prompt_text).render(**vars)
    logger.debug('System prompt built: %s', prompt)

    return prompt


# Ouptut validation can catch errors and trigger a retry with a helpful message
@parser_agent.output_validator
def validate_output(
    ctx: RunContext[ParseDeps],
    output: ParsedOutput
) -> ParsedOutput:
    errors = []

    # Uppercase all assets and portfolios
    output.assets = [asset.upper() for asset in (output.assets or [])]
    output.portfolios = [pf.upper() for pf in (output.portfolios or [])]

    # Validate that portfolios mentioned in output are in possible_portfolios
    for pf in (output.portfolios or []):
        if pf not in ctx.deps.possible_portfolios:
            errors.append(
                f"- Invalid portfolio mentioned: {pf}. Must be one of "
                f"{ctx.deps.possible_portfolios}"
            )

    # Check that start_date is not after end_date
    if output.start_date > output.end_date:
        errors.append(
            f"- Invalid date range: start_date {output.start_date} is after "
            f"end_date {output.end_date}"
        )

    # Move any assets that are actually portfolio names
    # (common model error we can fix ourselves)
    for asset in (output.assets or []):
        if asset in ctx.deps.possible_portfolios:
            output.assets.remove(asset)
            if asset not in (output.portfolios or []):
                output.portfolios.append(asset)
            logger.warning(
                f"Asset '{asset}' is a portfolio name. "
                "Moved it to portfolios list."
            )

    if errors:
        rerun_msg = (
            "Output validation failed:\n" +
            "\n".join(errors) +
            "\nPlease correct the errors and try again."
        )
        logger.warning(rerun_msg)
        raise ModelRetry(rerun_msg)

    return output


if __name__ == '__main__':
    # Example usage for testing
    deps = ParseDeps(
        user="Cedric",
        possible_portfolios=["CEDRIC.PF", "JOHN.PF", "LOUIS.PF"]
    )
    user_query = "What is my portofolio performance ffrom Jan 1 to Mar 31?"
    result = parser_agent.run_sync(
        deps=deps,
        user_prompt=user_query,
        output_type=ParsedOutput
    )
    print(result.output)
