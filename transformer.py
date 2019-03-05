from __future__ import print_function
import sys
import json
import argparse
import pprint 
import iso8601
import rfc3339
import logging
from pytimeparse.timeparse import timeparse

from datetime import timedelta
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

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

pp = pprint.PrettyPrinter(indent=4)

def parse_date(text):
    return iso8601.parse_date(text)

def print_date(date):
    return rfc3339.rfc3339(date)

def get_events_of_conference(calendar, config):
    """Get all events of the given conference (that's to say events of the given calendar in the good time period)"""
    global logger
    service = get_calendar_service()
    all_events = []
    for period in config['dates']:
        logger.info("getting events of %s between %s and %s" %(calendar['id'], period['start'], period['end']))
        page_token = None
        while True:
            events_list = service.events().list(calendarId=calendar['id'], 
                                            timeMin=period['start'],
                                            timeMax=period['end'],
                                            maxResults=10, singleEvents=True,
                                            orderBy='startTime').execute()
            logger.info("downloaded %d events" % len(all_events))
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
    logger.info("should remove %d events" % len(previous))
    for event in previous:
        service.events().delete(calendarId=calendar['id'], eventId=event['id']).execute()
        logger.info("removed %s" % previous)

def process_conference(conference, config):
    """Process conference file to generate the Google Agenda and the needed entries
    """
    conference_name = conference['name']
    calendar = get_or_create_calendar(conference_name, config)
    logger.info("Using calendar %s" % calendar )
    formats = conference['formats']
    # TODO maybe filter talks to remove rejected ones prior to sort them
    # First, clear all events at conference dates
    remove_previous_events(calendar, config)
    # And now, starting at start time, and until end time is elapsed, fill schedule with talks
    talks = sorted(conference['talks'], key=itemgetter('rating'), reverse=True)
    formats_map = improve_formats(conference['formats'])
    speakers_map = improve_speakers(conference['speakers'])

    period_list = config['dates']
    purgeable_talks = []
    purgeable_talks.extend(talks)
    for period in period_list:
        create_events_in_period(calendar, period, purgeable_talks, config, formats_map, speakers_map)

def create_events_in_period(calendar, period, purgeable_talks, config, formats_map, speakers_map):
    conference_end = parse_date(period['end'])
    # create a fake event to have start time correctly set
    previous_event = {
        'start': {'dateTime': period['start']}, 
        'end': {'dateTime': period['start']}, 
    }
    while purgeable_talks:
        t = purgeable_talks.pop(0)
        improve_talk(t, config, formats_map, speakers_map)
        next_event = create_event_for(t, calendar, config, previous_event)
        previous_event = next_event
        logger.info("added event %s"%next_event['summary'])
        talk_end = parse_date(previous_event['end']['dateTime'])
        if talk_end>conference_end:
            logger.info("conference period %s is full!" % period)
            return
    logger.info("All time slots are full, conference schedule is ready to be improved by hand at %s" % calendar)

def improve_talk(talk, config, formats, speakers):
    if talk['title'] in config['overrides']:
        override = config['overrides'][talk['title']]
        for key, value in override.items():
            talk[key] = value
    talk['timedelta'] = formats[talk['formats']]
    full_speakers = []
    for s in talk['speakers']:
        full_speakers.append(speakers[s])
    talk['speakers'] = full_speakers

def improve_speakers(speakers):
    returned = {}
    for s in speakers:
        returned[s['uid']]=s
    return returned

def improve_formats(formats):
    returned = {}
    for f in formats:
        returned[f['id']]=timedelta(seconds=timeparse(f["name"]))
    return returned

def create_event_for(talk, calendar, config, previous_event):
    """
    Creates an event for the given talk
    
    :param talk: the talk JSON fragment, as obtained from conference-hall export. 
    Notice it should an improved json object, with duration replaced with a timedelta, 
    and speakers ids replaced with speakers objects
    :param calendar: the calendar object, as obtained from Google Agenda
    :param config: the transform configuration
    :param previous_event: the immediatly previous event, after which the talk will be scheduled
    :return: the newly created event object, as returned from Google Calendar
    """
    logger.info("adding an event for %s" % talk['title'])
    service = get_calendar_service()

    start_time = parse_date(previous_event['end']['dateTime'])
    delta = talk['timedelta']
    end_time = start_time + delta
    event = {
        'summary': talk['title'],
        'location': config['location'],
        'description': talk['abstract'],
        'start': {
            'dateTime': print_date(start_time),
            'timeZone': config['timezone'],
        },
        'end': {
            'dateTime': print_date(end_time),
            'timeZone': config['timezone'],
        },
        }

    event = service.events().insert(calendarId=calendar['id'], body=event).execute()
    return event

def get_calendar_service():
    """
    Obtain the calendar service from Google
    """
    global SERVICE
    if SERVICE is None:
        logger.info("No Google calendar service existing. Creating")
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
        logger.info("Google calendar service created")
    return SERVICE

def get_or_create_calendar(conference, config):
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
                logger.info("calendar %s already exists! Retrieving it" % conference)
                return calendar_list_entry
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    # Calendar not found. Creating !
    calendar = {
        'summary': conference,
        'timeZone': config['timezone']
    }
    logger.info("calendar %s doesn't exist! Creating it" % conference)
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
