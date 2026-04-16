import fin_db as fdb
from .first_attempt import agent, State


def run():
    logger = fdb.setup_logger('main')
    fdb.open_session('fin_db_read')
    state = State()
    result = agent.run_sync(
        user_prompt='What were the returns for AAPL in 2025?',
        deps=state,
    )
    logger.info('Agent run complete')
    print(result.output)
    print(state.data)


if __name__ == '__main__':
    run()
