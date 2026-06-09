"""
Main entry point for the Harri application, providing both CLI and
Telegram bot interfaces.
"""

# -----------------------------------------------------------------------------
# ========================== IMPORTS AND CONSTANTS ============================
# -----------------------------------------------------------------------------

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Import colorlog if available, otherwise set to None
try:
    import colorlog
except ImportError:
    colorlog = None

from .bot import start_telebot
from .finance import ParseDeps, parser_agent

FILE_DIR = Path(__file__).parent  # harri/src/harri


# -----------------------------------------------------------------------------
# ================================= LOGGING ===================================
# -----------------------------------------------------------------------------


logger = logging.getLogger("harri")
logger.setLevel("INFO")
logger.propagate = False

if colorlog is not None:
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(blue)s%(name)s%(reset)s: %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )
else:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
logger.addHandler(console_handler)


# -----------------------------------------------------------------------------
# =============================== ENTRY POINTS ================================
# -----------------------------------------------------------------------------


def run_cli():
    """
    Runs the parser agent with a user prompt taken from command line arguments.
    """

    async def inner():
        user_prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
        deps = ParseDeps(
            user="Cedric",
            possible_portfolios=["LOUIS.PF", "CEDRIC.PF", "JOHN.PF"],
        )

        result = await parser_agent.run(deps=deps, user_prompt=user_prompt)

        return result.output

    try:
        return asyncio.run(inner())
    except Exception as e:
        logger.error(f"An error occurred while running the CLI: {e}")
        sys.exit(1)


def run_telebot():
    token = sys.argv[1] if len(sys.argv) > 1 else None
    if not token:
        env_path = FILE_DIR.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        token = os.getenv("HARRI_BOT_TOKEN")
    if not token or not isinstance(token, str):
        logger.error("Telegram bot token not provided.")
        sys.exit(1)

    try:
        start_telebot(token)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


# -----------------------------------------------------------------------------
# =================================== MAIN ====================================
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    # Default to CLI
    run_cli()
