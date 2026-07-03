import sys
import os.path
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, time

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


TZ_MSK = ZoneInfo('Europe/Moscow')
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TIME_STR = '22:21'
EVENT_DESCRIPTION = ''


def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        creds = Credentials.from_authorized_user_file('token.pickle', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'w') as f:
            f.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def parse_dates(date_intervals):
    result = []
    for interval in date_intervals:
        parts = interval.split(' - ')
        start_date = datetime.strptime(f'{parts[0]}', '%d.%m.%y')
        end_date =  datetime.strptime(f'{parts[1].strip()}', '%d.%m.%y')
        while start_date <= end_date:
            result.append(start_date)
            start_date = start_date + timedelta(days=1)
    return result


def remove_reminder(service, reminder_date, time_str, summary):
    hour, minute = map(int, time_str.split(':'))
    start_dt = datetime.combine(reminder_date, time(hour, minute)).replace(tzinfo=TZ_MSK)
    time_min = (start_dt - timedelta(minutes=1)).isoformat()
    time_max = (start_dt + timedelta(minutes=1)).isoformat()

    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            q=summary,
            singleEvents=True,
            orderBy='startTime',
        ).execute()
        events = events_result.get('items', [])

        for event in events:
            service.events().delete(
                calendarId='primary',
                eventId=event['id'],
            ).execute()
    except Exception as e:
        print(f'Error in remove reminder: {repr(e)}')


def reminder_exists(service, start_date, summary):
    start_iso = start_date.isoformat()
    time_min = (start_date - timedelta(minutes=1)).isoformat()
    time_max = (start_date + timedelta(minutes=1)).isoformat()

    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            q=summary,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return True if events_result.get('items', []) else False
    except Exception as e:
        print(e)
        return False


def add_reminder(service, reminder_date, time_str, summary, reminder_minutes=0):
    hour, minute = map(int, time_str.split(':'))
    start_date = datetime.combine(reminder_date, time(hour, minute)).replace(tzinfo=TZ_MSK)
    end_date = start_date + timedelta(minutes=15)
    event_body = {
        'summary': summary,
        'start': {
            'dateTime': start_date.isoformat(),
            'timeZone': TZ_MSK.key,
        },
        'end': {
            'dateTime': end_date.isoformat(),
            'timeZone': TZ_MSK.key,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {
                    'method': 'popup',
                    'minutes': reminder_minutes,
                }
            ],
        },
    }

    if not reminder_exists(service, start_date, summary):
        service.events().insert(
            calendarId='primary',
            body=event_body
        ).execute()


def main():
    service = get_calendar_service()
    raw_date_intervals = sys.stdin.readlines()
    parsed_dates = parse_dates(raw_date_intervals)
    for day in parsed_dates:
        add_reminder(
            service=service,
            reminder_date=day,
            time_str=TIME_STR,
            summary=EVENT_DESCRIPTION,
        )
    print(f'Reminders were added for dates {parsed_dates[0]} - {parsed_dates[-1]}')


if __name__ == '__main__':
    main()
