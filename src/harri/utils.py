# --------------------------------------------------------------------------------------
# IMPORTS, LOGGING AND CONSTANTS
# --------------------------------------------------------------------------------------

# Standard Library Imports
import json
import logging
import os
from pathlib import Path

# Third Party Imports
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

# Logger
logger = logging.getLogger(__name__)

# Code-level Constants
SRC_HARRI = Path(__file__).parent.resolve()
REPO_ROOT = SRC_HARRI.parent.parent
_ENV_FILE = REPO_ROOT / ".env"

# --------------------------------------------------------------------------------------
# .ENV LOADING AND VALIDATION
# --------------------------------------------------------------------------------------
if not _ENV_FILE.exists():
    raise RuntimeError(
        f"Missing .env file at {_ENV_FILE}. "
        "Please create one with the required variables."
    )
load_dotenv(dotenv_path=(REPO_ROOT / ".env"))

# PROD_DB
_db_path_str = os.getenv("PROD_DB_PATH")
if not _db_path_str:
    raise RuntimeError(
        "Missing 'PROD_DB_PATH' in environment variables. "
        "Please set it in your .env file."
    )
PROD_DB = Path(_db_path_str).resolve()
logger.info(f"Using database at: {PROD_DB}")

# Google creds
_creds_str = os.getenv("GOOGLE_CLIENT_CREDENTIALS")
if not _creds_str:
    raise RuntimeError("Missing GOOGLE_CLIENT_CREDENTIALS in .env file.")
GOOGLE_CREDS = json.loads(_creds_str)

# Encryption Key and Cypher
_ENCRYPTION_KEY = os.getenv("HARRI_ENCRYPTION_KEY")
if not _ENCRYPTION_KEY:
    raise RuntimeError(
        "Missing 'HARRI_ENCRYPTION_KEY' in environment variables. "
        "Generate one with `Fernet.generate_key()`."
    )
try:
    _CYPHER = Fernet(_ENCRYPTION_KEY.encode("utf-8"))
except ValueError as e:
    raise RuntimeError(
        "Invalid Fernet key in 'HARRI_ENCRYPTION_KEY'. Please check your .env file."
    ) from e


# --------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------------------


def encrypt_blob(plaintext: str) -> str:
    """Encrypts a string into a secure, URL-safe base64 string."""
    # Convert plaintext string to bytes
    bytes_data = plaintext.encode("utf-8")
    # Encrypt
    encrypted_bytes = _CYPHER.encrypt(bytes_data)
    # Decode back to a regular string so it's easy to store in SQLite TEXT column
    return encrypted_bytes.decode("utf-8")


def decrypt_blob(ciphertext: str) -> str:
    """Decrypts the ciphertext string back into the original plaintext."""
    try:
        # Convert string to bytes
        bytes_data = ciphertext.encode("utf-8")
        # Decrypt
        decrypted_bytes = _CYPHER.decrypt(bytes_data)
        # Decode back to string
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt the token. The encryption key might have changed "
            "or the data is corrupted."
        )


__all__ = [
    "encrypt_blob",
    "decrypt_blob",
    "REPO_ROOT",
    "SRC_HARRI",
    "GOOGLE_CREDS",
    "PROD_DB",
]
