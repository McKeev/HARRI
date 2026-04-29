import sys
from .agents import ParseDeps, parser_agent


def run():
    """
    Runs the parser agent with a user prompt taken from command line arguments.
    """
    user_prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    deps = ParseDeps(
        user='Cedric',
        possible_portfolios=['LOUIS.PF', 'CEDRIC.PF', 'JOHN.PF'],
    )

    result = parser_agent.run_sync(
        deps=deps,
        user_prompt=user_prompt
    )

    return result.output


if __name__ == '__main__':
    run()
