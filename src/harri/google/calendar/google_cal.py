import datetime as dt
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

# We request read-only access to the calendar list, and read/write access to events.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def authenticate() -> Resource:
    """Authenticates the user and returns the Google Calendar service object."""
    creds = None
    # Note: If you previously ran the script with different scopes,
    # you MUST delete 'token.json' so it prompts you to authorize the new scopes.
    if os.path.exists("secrets/token.json"):
        creds = Credentials.from_authorized_user_file("secrets/token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "secrets/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("secrets/token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def list_calendars(service):
    """Lists all calendars the user has access to."""
    print("\n--- Available Calendars ---")
    try:
        # Note: This requires the calendar.readonly scope
        page_token = None
        while True:
            calendar_list = service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry in calendar_list["items"]:
                print(f"- {calendar_list_entry['summary']}")
                print(f"  ID: {calendar_list_entry['id']}\n")
            page_token = calendar_list.get("nextPageToken")
            if not page_token:
                break
    except HttpError as error:
        print(f"An error occurred: {error}")


def list_upcoming_events(service):
    """Prints the upcoming events for a specified calendar."""
    calendar_id = input(
        "\nEnter Calendar ID to read (leave blank for 'primary'): "
    ).strip()
    if not calendar_id:
        calendar_id = "primary"

    try:
        now = dt.datetime.now(tz=dt.timezone.utc)
        one_month_from_now = now + dt.timedelta(days=30)
        print(f"\n--- Fetching upcoming events for '{calendar_id}' ---")

        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),
                timeMax=one_month_from_now.isoformat(),
                maxResults=10,
                singleEvents=True,  # Expand recurring events into individual instances
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"[{start}] {event.get('summary', 'No Title')}")

    except HttpError as error:
        print(f"An error occurred reading events: {error}")


def add_event(service):
    """Creates a new event on a specifically requested calendar."""
    print("\n--- Add a New Event ---")
    calendar_id = input("Enter the EXACT Calendar ID to write to (required): ").strip()

    if not calendar_id:
        print("❌ Write operation cancelled. You must specify a target calendar ID.")
        return

    summary = input("Event Title: ")
    print("Scheduling this event for tomorrow. What hour? (0-23)")

    try:
        hour = int(input("Hour: "))
    except ValueError:
        print("❌ Invalid hour. Operation cancelled.")
        return

    tomorrow = dt.datetime.now() + dt.timedelta(days=1)
    start_time = tomorrow.replace(
        hour=hour, minute=0, second=0, microsecond=0
    ).astimezone()
    end_time = (
        start_time + dt.timedelta(hours=1)
    )  # Fixed from datetime.timedelta to just timedelta reference via import or explicit

    event_body = {
        "summary": summary,
        "description": "Created via Python script.",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC",
        },
    }

    try:
        event = (
            service.events().insert(calendarId=calendar_id, body=event_body).execute()
        )
        print(f"\n✅ Event created successfully on calendar '{calendar_id}'")
        print(f"Link: {event.get('htmlLink')}")
    except HttpError as error:
        print(f"\n❌ An error occurred creating the event: {error}")
        print("Make sure you have write permissions for this specific calendar ID.")


def main():
    print("Authenticating with Google...")
    service: Resource = authenticate()

    if isinstance(service, Resource):
        print("✅ Authentication successful!")
        print(type(service))
    else:
        print("❌ Authentication failed. Exiting.")

    while True:
        print("\n==============================")
        print("    Google Calendar Menu")
        print("==============================")
        print("1. List my calendars (to find IDs)")
        print("2. View upcoming events (Read-only)")
        print("3. Add an event to a specific calendar (Write)")
        print("4. Exit")

        choice = input("Enter your choice (1/2/3/4): ")

        if choice == "1":
            list_calendars(service)
        elif choice == "2":
            list_upcoming_events(service)
        elif choice == "3":
            add_event(service)
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
