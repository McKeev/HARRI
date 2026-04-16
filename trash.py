def get_few_shot_examples() -> list:
    today = dt.date.today()
    year: int = today.year
    # To string
    today = today.strftime('%Y-%m-%d')

    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())
    return [
        # ----------------------------------------------------------------
        # Example 1: straightforward → get_history
        # ----------------------------------------------------------------

        ModelRequest(
            parts=[UserPromptPart(
                content=(
                    "Give me the close and totret for AAPL and SPY "
                    "2020-01-01 to 2020-12-31."
                )
        )], run_id=id1),
        ModelResponse(parts=[
            ToolCallPart(
                tool_name="get_history",
                args={
                    "tickers": ["AAPL", "SPY"],
                    "fields": ["close", "totret"],
                    "start_date": "2020-01-01",
                    "end_date": "2020-12-31"
                },
                tool_call_id="ex1-1"
            )
        ], run_id=id1),
        ModelRequest(parts=[
            ToolReturnPart(
                tool_name="get_history",
                content=(
                    "Retrieved 252 rows for ['AAPL', 'SPY'] | "
                    "fields=['close', 'totret'] | 2020-01-01 to 2020-12-31"
                ),
                tool_call_id="ex1-1"
            )
        ], run_id=id1),
        ModelResponse(parts=[
            TextPart(
                "Retrieved 252 rows for ['AAPL', 'SPY'] | "
                "fields=['close', 'totret'] | 2020-01-01 to 2020-12-31"
            )
        ], run_id=id1),

        # ----------------------------------------------------------------
        # Example 2: 'perform' + 'this year' → get_history only
        # ----------------------------------------------------------------

        ModelRequest(parts=[UserPromptPart(
            content=(
                "How is SAF.PA performing this year ?"
            )
        )], run_id=id2),
        ModelResponse(parts=[
            ToolCallPart(
                tool_name="get_history",
                # No fields specified -> default to totret,
                # which is what we want for "performing"
                args={
                    "tickers": ["SAF.PA"],
                    "start_date": f"{year}-01-01",
                    "end_date": today
                },
                tool_call_id="ex2-1"
            )
        ], run_id=id2),
        ModelRequest(parts=[
            ToolReturnPart(
                tool_name="get_history",
                content=(
                    "Retrieved 125 rows for ['SAF.PA'] | "
                    f"fields=['totret'] | {year}-01-01 to {today}"
                ),
                tool_call_id="ex2-1"
            )
        ], run_id=id2),
        ModelResponse(parts=[
            TextPart(
                "Retrieved 125 rows for ['SAF.PA'] | "
                f"fields=['totret'] | {year}-01-01 to {today}"
            )
        ], run_id=id2),

        # ----------------------------------------------------------------
        # Example 3: tool failure → clear response
        # ----------------------------------------------------------------
        ModelRequest(parts=[UserPromptPart(
            content="Get history for FAKE close from 2016-01-01 to 2016-06-31."
        )], run_id=id3),
        ModelResponse(parts=[
            ToolCallPart(
                tool_name="get_history",
                args={
                    "tickers": ["FAKE"],
                    "fields": ["close"],
                    "start_date": "2016-01-01",
                    "end_date": "2016-06-31"
                },
                tool_call_id="ex3-1"
            )
        ], run_id=id3),
        ModelRequest(parts=[
            ToolReturnPart(
                tool_name="get_history",
                content=(
                    "Error: Data for tickers {'FAKE'} not found in database."
                ),
                tool_call_id="ex3-1"
            )
        ], run_id=id3),
        ModelResponse(parts=[
            TextPart(
                "Error: Data for tickers {'FAKE'} not found in database."
            )
        ], run_id=id3),
    ]