import fin_db as fdb
from .parser import ParseDeps, parser_agent


def run():
    logger = fdb.setup_logger('main')
    deps = ParseDeps(
        user='Cedric',
        possible_portfolios=['LOUIS.PF', 'CEDRIC.PF', 'JOHN.PF'],
    )

    result = parser_agent.run_sync(
        deps=deps,
        user_prompt="hows tsmc been doing since last year?"
    )
    logger.info('Parsed output: %s', result.output)


if __name__ == '__main__':
    run()
