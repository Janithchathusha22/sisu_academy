"""Calendar payload contract: no media URLs, grades, payments or attendee list."""
from hashlib import sha256
from datetime import datetime
from zoneinfo import ZoneInfo

def event_id(site, member, session):
    return sha256(f'{site}:{member}:{session}'.encode()).hexdigest()

def event_payload(session, room_title, timezone, campus_url):
    zone=ZoneInfo(timezone)
    start=datetime.fromisoformat(str(session['starts_at']))
    end=datetime.fromisoformat(str(session['ends_at']))
    start=start.astimezone(zone) if start.tzinfo else start.replace(tzinfo=zone)
    end=end.astimezone(zone) if end.tzinfo else end.replace(tzinfo=zone)
    if end<=start: raise ValueError('Invalid session dates')
    return {'summary':str(session['title'])[:120], 'description':f'{str(room_title)[:160]}\nOpen your LMS for class access: {campus_url}',
            'location':str(session.get('location') or '')[:200], 'visibility':'private', 'status':'confirmed',
            'start':{'dateTime':start.isoformat(),'timeZone':timezone},'end':{'dateTime':end.isoformat(),'timeZone':timezone},
            'reminders':{'useDefault':False,'overrides':[{'method':'popup','minutes':15}]}}
