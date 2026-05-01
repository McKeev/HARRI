import json
from pathlib import Path

import pytest

from harri.finance import ParseDeps, ParsedOutput, parser_agent

FILE_DIR = Path(__file__).parent
GREEN = "\033[92m"
RED = "\033[91m"
ORANGE = "\033[93m"
RESET = "\033[0m"


def _build_diff(actual: ParsedOutput, expected: ParsedOutput) -> str:
    """
    Reviews the parsed output and builds a custom colored diff string if there are
    mismatches.

    Parameters:
    ----------
    actual: ParsedOutput
        The actual output from the parser agent.
    expected: ParsedOutput
        The expected output defined in the test case.

    Returns:
    -------
    str
        A string representation of the diff, with matches in green and mismatches in
        red.
    """
    # Convert models to dictionaries for easy iteration
    actual_dict = actual.model_dump()
    expected_dict = expected.model_dump()
    diff = 0

    diff_elements = []

    for key, expected_val in expected_dict.items():
        actual_val = actual_dict.get(key)

        if actual_val == expected_val:
            # Match: Field and value in green
            diff_elements.append(f"{key}={GREEN}{repr(actual_val)}{RESET}")
        else:
            # Mismatch: `actual $expected$` in red
            diff_elements.append(
                f"{key}={RED}{repr(actual_val)}{RESET}"
                f"{ORANGE}!={RESET}"
                f"{RED}{repr(expected_val)}{RESET}"
            )
            diff += 1

    return "(" + ", ".join(diff_elements) + ")"


def _load_test_prompts() -> list[tuple[str, ParsedOutput]]:
    """Load `test_prompt: answer_key` pairs from test_prompts.json."""
    prompts_parsed: dict = json.loads((FILE_DIR / "test_prompts.json").read_text())
    return [(k, ParsedOutput(**v)) for k, v in prompts_parsed.items()]


@pytest.mark.parametrize("test_prompt, answer_key", _load_test_prompts())
def test_prompts(test_prompt: str, answer_key: ParsedOutput):
    # Important: test prompts should take into account these constraints:
    deps = ParseDeps(
        user="Cedric",
        possible_portfolios=["LOUIS.PF", "CEDRIC.PF", "JOHN.PF"],
        current_date="2026-04-08",
    )

    result = parser_agent.run_sync(deps=deps, user_prompt=test_prompt).output

    assert result == answer_key, _build_diff(result, answer_key)
