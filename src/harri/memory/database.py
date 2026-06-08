# --------------------------------------------------------------------------------------
# # IMPORTS, CONSTANTS AND SETUP
# --------------------------------------------------------------------------------------
from __future__ import annotations

# Standard Library Imports
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Third Party Imports
import aiosqlite
from pydantic import BaseModel, Field

# Local Imports
from harri.utils import PROD_DB, decrypt_blob, encrypt_blob

# Setup
_active_db_path: Path | None = None
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# EXCEPTIONS
# --------------------------------------------------------------------------------------


class UserConflictError(Exception):
    """Raised when a user registration conflict occurs."""


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
        # Enable foreign key support (required for ON DELETE CASCADE in SQLite)
        await conn.execute("PRAGMA foreign_keys = ON;")
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
        await cursor.executescript(
            # sql
            """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT,
            approval_status BOOLEAN DEFAULT 0,
            admin_status BOOLEAN DEFAULT 0,
            portfolio TEXT
        );
        CREATE TABLE IF NOT EXISTS oauth_credentials (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            encrypted_payload TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, provider)
        );
        """
        )
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
    portfolio: str | None
        Optional field for user's portfolio information (default: None).
    """

    id: int = Field(frozen=True)
    telegram_id: int = Field(frozen=True)
    name: str = "User"
    approval_status: bool = False
    admin_status: bool = False
    portfolio: str | None = None

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
        portfolio: str | None = None,
    ) -> User:
        """
        Registers a new user in the database. If a user with the same telegram_id
        already exists, raises a UserConflictError.

        Parameters:
        ----------
        telegram_id: int | str
            The user's Telegram ID (must be unique).
        name: str
            The user's display name (default: "User").
        approval_status: bool
            Whether the user is approved (default: False).
        admin_status: bool
            Whether the user has admin privileges (default: False).
        portfolio: str | None
            Optional field for user's portfolio information (default: None).

        Returns:
        -------
        User
            The newly registered User instance.

        Raises:
        ------
        UserConflictError
            If a user with the same telegram_id already exists in the database.
        ValueError
            If the provided telegram_id is not a valid integer or string representation
            of an integer.
        """
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
                INSERT INTO users (telegram_id, name, approval_status, admin_status, portfolio)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO NOTHING
                RETURNING *;
                """,
                (telegram_id, name, approval_status, admin_status, portfolio),
            )
            new_user_info = await cursor.fetchone()

            if new_user_info is None:
                # Unexpected behaviour: user already exists
                raise UserConflictError(
                    f"User with telegram_id {telegram_id} already exists."
                )
            logger.info(
                f"New user registered with telegram_id {telegram_id} and name '{name}'."
            )
            return cls(**dict(new_user_info))

    async def get_credentials(self, provider: str) -> dict | None:
        """
        Retrieves the encrypted credentials for a given provider.

        Parameters:
        ----------
        provider: str
            The name of the service provider (e.g., "google").

        Returns:
        -------
        dict | None
            The decrypted credentials as a dict if found, else None.
        """
        async with get_cursor() as cursor:
            await cursor.execute(
                # sql
                """
                SELECT encrypted_payload FROM oauth_credentials
                WHERE user_id = ? AND provider = ?;
                """,
                (self.id, provider),
            )
            result = await cursor.fetchone()

        if result is None:
            return None

        plaintext_credentials = decrypt_blob(result["encrypted_payload"])
        return json.loads(plaintext_credentials)

    async def store_credentials(self, provider: str, token: dict):
        """
        Encrypts and stores the credentials for a given provider.
        Conflict behaviour: overwrite existing credentials for the same provider.

        Parameters:
        ----------
        provider: str
            The name of the service provider (e.g., "google").
        token: dict
            The credentials to be encrypted and stored.
        """
        plaintext_credentials = json.dumps(token)
        encrypted = encrypt_blob(plaintext_credentials)
        async with get_cursor() as cursor:
            await cursor.execute(
                # sql
                """
                INSERT INTO oauth_credentials (user_id, provider, encrypted_payload)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    encrypted_payload = excluded.encrypted_payload,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (self.id, provider, encrypted),
            )

    async def info(self) -> str:
        """Returns a well formatted string of the user's information."""
        intro = "👤 User Info:\n"
        return intro + "\n".join(
            f"• {k.replace('_', ' ').title()}: {v}"
            for k, v in self.model_dump().items()
        )

    async def delete(self) -> None:
        """
        Deletes the user from the database.
        WARNING: This action is irreversible and will remove all associated data,
        including credentials.
        """
        async with get_cursor() as cursor:
            await cursor.execute(
                "DELETE FROM users WHERE id = ?;",
                (self.id,),
            )
            # Check if the user was actually deleted (should be 1)
            if cursor.rowcount == 0:
                logger.warning(
                    f"Attempted to delete user with id {self.id}, "
                    "but no rows were affected. "
                    "This may indicate the user was already deleted or never existed."
                )
            logger.info(f"User with id {self.id} deleted from database.")

    async def save(self) -> User | None:
        """
        Saves the current attributes of the User instance to the database.
        Use this after modifying the user's attributes.
        """
        async with get_cursor() as cursor:
            await cursor.execute(
                # sql
                """
                UPDATE users
                SET name = ?,
                    approval_status = ?,
                    admin_status = ?,
                    portfolio = ?
                WHERE id = ?;
                """,
                (
                    self.name,
                    self.approval_status,
                    self.admin_status,
                    self.portfolio,
                    self.id,
                ),
            )
            # check if the user was actually updated (should be 1)
            if cursor.rowcount == 0:
                logger.warning(
                    f"Attempted to update user with id {self.id}, "
                    "but no rows were affected. Check if user exists in the database."
                )
                return None
            logger.info(
                f"User with id {self.id} updated in database: {self.model_dump()}"
            )
            return self
