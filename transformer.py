from __future__ import print_function
import sys
import json
import argparse
import pprint 

from operator import itemgetter

import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/calendar' # Full calendar access is required to create the calendar from conference name
    ]
APPLICATION_NAME = 'Conference-Hall Google Agenda exporter'

SERVICE = None


pp = pprint.PrettyPrinter(indent=4)

def get_events_of_conference(calendar, config):
    """Get all events of the given conference (that's to say events of the given calendar in the good time period)"""
    service = get_calendar_service()
    page_token = None
    all_events = []
    print("getting events of %s between %s and %s" %(calendar['id'], config['dates']['start'], config['dates']['end']))
    while True:
        events_list = service.events().list(calendarId=calendar['id'], 
                                        timeMin=config['dates']['start'],
                                        timeMax=config['dates']['end'],
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
        for event in events_list['items']:
            all_events.append(event)
        page_token = events_list.get('nextPageToken')
        if not page_token:
            break
    return all_events

def remove_previous_events(calendar, config):
    """Remove all event from given calendar at conference dates"""
    service = get_calendar_service()
    previous = get_events_of_conference(calendar, config)
    print("should remove %d events" % len(previous))
    for event in previous:
        service.events().delete(calendarId=calendar['id'], eventId=event['id']).execute()
        print("removed %s" % previous)

def process_conference(conference, config):
    """Process conference file to generate the Google Agenda and the needed entries
    """
    conference_name = conference['name']
    calendar = get_or_create_calendar(conference_name)
    print("Using calendar %s" % calendar )
    formats = conference['formats']
    # TODO maybe filter talks to remove rejected ones prior to sort them
    # First, clear all events at conference dates
    remove_previous_events(calendar, config)
    talks = sorted(conference['talks'], key=itemgetter('rating'), reverse=True)
#        pp.pprint(talks)

def get_calendar_service():
    """
    Obtain the calendar service from Google
    """
    global SERVICE
    if SERVICE is None:
        print("No Google calendar service existing. Creating")
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                flow.user_agent = APPLICATION_NAME
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        SERVICE = build('calendar', 'v3', credentials=creds)
        print("Google calendar service created")
    return SERVICE

def get_or_create_calendar(conference):
    """Create secondary calendar having as summary the given text
    """
    service = get_calendar_service()

    # This code is to fetch the calendar ids shared with me
    # Src: https://developers.google.com/google-apps/calendar/v3/reference/calendarList/list
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary']==conference:
                print("calendar %s already exists! Retrieving it" % conference)
                return calendar_list_entry
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    # Calendar not found. Creating !
    calendar = {
        'summary': conference,
        'timeZone': 'America/Los_Angeles'
    }
    print("calendar %s doesn't exist! Creating it" % conference)
    return service.calendars().insert(body=calendar).execute()

def parse_json(path):
    with open(path, encoding='UTF-8') as file:
        return json.loads(file.read())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="A simple Python tool that fill a Google Calendar from a conference-hall export file"
    )
    parser.add_argument('--input',
        required = False,
        default = 'export.json',
        help = 'Export file generated by https://conference-hall.io for this conference')

    parser.add_argument('--configuration',
        required = False,
        default = 'config.json',
        help = 'Additional configuration elements that are missing from conference-hall export')

    args = parser.parse_args()
    process_conference(parse_json(args.input), parse_json(args.configuration))
