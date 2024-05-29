from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarManager:
    def __init__(self, key_file:str, names:list):
        self.key_file = key_file
        self.names = names
        self.service = self.get_calendar_service()
    def get_schedule(self, start, end):
        now = start.isoformat() + 'Z' 
        endtime = end.isoformat() + 'Z'
        events_result = self.service.events().list(calendarId='settarov@gmail.com', timeMin=now, timeMax=endtime,
                                                   maxResults=1000, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])

        shed = dict()
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if event['summary'].strip() in self.names:
                if start in shed.keys():
                    shed[start] = shed[start] + ' ' + event['summary'].strip()
                else:
                    shed[start] = event['summary'].strip()
        return shed
    def get_calendar_service(self):
        creds = service_account.Credentials.from_service_account_file(self.key_file, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        return service