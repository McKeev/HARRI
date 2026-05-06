# --------------------------------------------------------------------------------------
# IMPORTS
# --------------------------------------------------------------------------------------

# First Party Imports
import json
from typing import List, cast

# Third Party Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Local Imports
from harri.memory import User
from harri.utils import GOOGLE_CREDS

# --------------------------------------------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------------------------------------------


async def authenticate(user: User, scopes: List[str]) -> Credentials:
    """Authenticates the user and returns the Credentials object."""
    creds = None
    token = await user.get_credentials("google")

    if token:
        creds = Credentials.from_authorized_user_info(token, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(GOOGLE_CREDS, scopes)
            creds = flow.run_local_server(port=0)

        await user.store_credentials("google", json.loads(creds.to_json()))

    return cast(Credentials, creds)
