import asyncio

import pytest
import pytest_asyncio

from harri.memory import User, UserConflictError, load_db

# --------------------------------------------------------------------------------------
# FIXTURES
# --------------------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(tmp_path):
    """
    Runs automatically before EVERY test.
    Creates a unique temporary database file so xdist workers don't collide.
    """
    test_db_path = tmp_path / "test_harri.db"

    # Run load_db with the temporary path
    await load_db(db_path=test_db_path)

    yield


# --------------------------------------------------------------------------------------
# TESTS
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_new_user():
    """Test that a new user can be registered and returned with an ID."""
    user = await User.register(telegram_id=12345, name="TestUser")

    assert user.id is not None
    assert user.telegram_id == 12345
    assert user.name == "TestUser"
    assert user.approval_status is False


@pytest.mark.asyncio
async def test_register_duplicate_user_raises_error():
    """Test that registering the same telegram_id twice raises a UserConflictError."""
    await User.register(telegram_id=11111, name="Original")

    with pytest.raises(UserConflictError, match="already exists"):
        await User.register(telegram_id=11111, name="Imposter")


@pytest.mark.asyncio
async def test_from_tele_id_fetches_existing_user():
    """Test retrieving an existing user."""
    await User.register(telegram_id=99999, name="FetchMe")

    fetched_user = await User.from_tele_id(telegram_id=99999)
    assert fetched_user is not None
    assert fetched_user.name == "FetchMe"


@pytest.mark.asyncio
async def test_from_tele_id_returns_none_if_missing():
    """Test fetching a non-existent user returns None."""
    fetched_user = await User.from_tele_id(telegram_id=777)
    assert fetched_user is None


@pytest.mark.asyncio
async def test_string_integer_parsing():
    """Test that string integers are correctly parsed into ints."""
    # Register with a string
    user = await User.register(telegram_id="555", name="StringUser")
    assert user.telegram_id == 555

    # Fetch with a string
    fetched = await User.from_tele_id(telegram_id="555")
    assert fetched is not None
    assert fetched.id == user.id


@pytest.mark.asyncio
async def test_invalid_telegram_id_raises_error():
    """Test that passing non-numeric strings crashes the factories safely."""
    with pytest.raises(ValueError, match="Invalid telegram_id"):
        await User.register(telegram_id="not_a_number")

    with pytest.raises(ValueError, match="Invalid telegram_id"):
        await User.from_tele_id(telegram_id="not_a_number")


@pytest.mark.asyncio
async def test_concurrent_reads_and_writes():
    """
    Test that WAL mode allows dozens of users to read the database
    at the exact same time a new user is being registered.
    """
    # Initial user to read
    await User.register(telegram_id=1, name="FirstUser")

    tasks = []
    # Read
    for _ in range(50):
        tasks.append(User.from_tele_id(telegram_id=1))
    # Write
    for i in range(10, 20):
        tasks.append(User.register(telegram_id=i, name=f"User{i}"))

    results = await asyncio.gather(*tasks)
    assert len(results) == 60  # 50 reads + 10 writes

    # Check that one of the writes succeeded
    check_user = await User.from_tele_id(telegram_id=15)
    if isinstance(check_user, User):
        assert check_user.name == "User15"
    else:
        raise AssertionError(
            "Expected to find User15 in the database, but it was not found."
        )
