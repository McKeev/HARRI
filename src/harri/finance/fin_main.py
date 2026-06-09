# --------------------------------------------------------------------------------------
# IMPORTS AND CONSTANTS
# --------------------------------------------------------------------------------------
# Third-Party Imports
import fin_db as fdb

# --------------------------------------------------------------------------------------
# LOGIC FLOW
# --------------------------------------------------------------------------------------


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
