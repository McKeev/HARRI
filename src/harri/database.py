# --------------------------------------------------------------------------------------
# # IMPORTS, CONSTANTS AND SETUP
# --------------------------------------------------------------------------------------
from __future__ import annotations

import logging

# Standard Library Imports
from contextlib import asynccontextmanager
from pathlib import Path

# Third Party Imports
import aiosqlite
from pydantic import BaseModel

# Constants
from harri.utils import PROD_DB

# Setup
_active_db_path: Path | None = None
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# DATABASE
# --------------------------------------------------------------------------------------


@asynccontextmanager
async def get_conn():
    """
    Centralized connection manager. ALL database interactions should be wrapped in this
    context manager to ensure proper connection handling and transaction management.
    """
    if _active_db_path is None:
        raise RuntimeError("Database path not set. Ensure `load_db` is called.")
    async with aiosqlite.connect(_active_db_path) as conn:
        # Allows rows to be accessed like dicts
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            raise e


@asynccontextmanager
async def get_cursor():
    """Chains off get_conn() to yield just a cursor."""
    async with get_conn() as conn:
        async with conn.cursor() as cursor:
            yield cursor


async def load_db(db_path: Path | str | None = None):
    """
    Initializes the database and creates necessary tables. If no path is provided,
    defaults to PROD_DB.
    """
    global _active_db_path
    if db_path is None:
        db_path = PROD_DB
    # Update global active database path
    _active_db_path = Path(db_path)
    # Establish connection and create table
    async with get_cursor() as cursor:
        # language=sql
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT,
            approval_status BOOLEAN DEFAULT 0,
            admin_status BOOLEAN DEFAULT 0
        );
        """)
        await cursor.execute("PRAGMA journal_mode=WAL;")
        logger.info(f"Database loaded from: {str(_active_db_path)}")


# --------------------------------------------------------------------------------------
# USER MODEL
# --------------------------------------------------------------------------------------


class User(BaseModel):
    """
    Represents a user in the system, with methods for database interactions.
    Should only be instantiated via class methods to ensure proper database handling.

    Attributes:
    ----------
    id: int
        Unique identifier for the user (auto-incremented).
    telegram_id: str
        Unique Telegram ID for the user.
    name: str
        Display name for the user (default: "User").
    approval_status: bool
        Indicates if the user is approved (default: False).
    admin_status: bool
        Indicates if the user has admin privileges (default: False).
    """

    id: int
    telegram_id: int
    name: str = "User"
    approval_status: bool = False
    admin_status: bool = False

    @classmethod
    async def from_tele_id(cls, telegram_id: int | str) -> User | None:
        """
        User factory from telegram id.

        Parameters:
        ----------
        telegram_id: int
            The user's Telegram ID.

        Returns:
        -------
        User | None
            A User instance if found, else None.
        """
        if isinstance(telegram_id, str):
            try:
                telegram_id = int(telegram_id)
            except Exception:
                raise ValueError(
                    f"Invalid telegram_id: {telegram_id}. "
                    "Must be an integer or string representing an integer."
                )

        async with get_cursor() as cursor:
            await cursor.execute(
                # sql
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            )
            user_info = await cursor.fetchone()

            if user_info:
                return cls(**dict(user_info))

            return None

    @classmethod
    async def register(
        cls,
        telegram_id: int | str,
        name: str = "User",
        approval_status: bool = False,
        admin_status: bool = False,
    ):
        if isinstance(telegram_id, str):
            try:
                telegram_id = int(telegram_id)
            except Exception:
                raise ValueError(
                    f"Invalid telegram_id: {telegram_id}. "
                    "Must be an integer or string representing an integer."
                )

        # Registers the user
        async with get_cursor() as cursor:
            await cursor.execute(
                # sql
                """
                INSERT INTO users (telegram_id, name, approval_status, admin_status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO NOTHING
                RETURNING *;
                """,
                (telegram_id, name, approval_status, admin_status),
            )
            new_user_info = await cursor.fetchone()

            if new_user_info is None:
                # Unexpected behaviour: user already exists
                raise ValueError(f"User with telegram_id {telegram_id} already exists.")

            return cls(**dict(new_user_info))
