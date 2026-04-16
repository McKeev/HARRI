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
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from jinja2 import Template
# Local Imports
import fin_db as fdb

# Agent Setup
provider = OllamaProvider(base_url="http://localhost:11434/v1")
model = OpenAIChatModel('qwen2.5:1.5b', provider=provider)

agent = Agent(
    model,
    model_settings=ModelSettings(
        max_tokens=100,
        temperature=0.0,
        top_p=1.0,
    )
)

# Test temperature and top_p settings by asking for a random number between 1
# and 10 multiple times. With temperature=0.0 and top_p=1.0, we should get the
# same result every time.
result = agent.run_sync('random number between 1 and 10')
print(result.output)
