import json
import sys
import time
from datetime import datetime
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from marshmallow import fields
from touchstone_auth import TouchstoneSession
from typing import Optional, List

def mk_optional_datetime_field():
    return field(
        default=None,
        metadata=config(
            #encoder=lambda d: datetime.isoformat(d) if d else None,
            decoder=lambda s: datetime.fromisoformat(s).astimezone() if s else None,
            #mm_field=fields.DateTime(format='iso')
        )
    )

@dataclass_json
@dataclass(frozen=True)
class Credentials:
    certfile: str = './cert.p12'
    password: str = ''

def read_credentials():
    with open('credentials.json') as cred_file:
        return Credentials.from_dict(json.load(cred_file))

def Session(credentials):
    return TouchstoneSession(
        base_url=r'https://atlas-auth.mit.edu/oauth2/authorize?identity_provider=Touchstone&redirect_uri=https://covidpass.mit.edu&response_type=TOKEN&client_id=2ao42ccnajj7jpqd7h059n7eoc&scope=covid19/user%20openid',
        pkcs12_filename=credentials.certfile,
        pkcs12_pass=credentials.password,
        cookiejar_filename='cookies.pickle')


# TODO: add all fields
@dataclass_json
@dataclass(frozen=True)
class Requirement:
    id: str
    title_web: str
    title_mobile: str
    required: bool
    visible: bool
    medical_awaiting_test_outcome: bool
    status: str # 'complete', 'due_soon', 'incomplete', 'pending'
    last_completion: Optional[datetime] = mk_optional_datetime_field()
    next_completion: Optional[datetime] = mk_optional_datetime_field()
    prerequisites: Optional[List[str]] = None

def get_requirements(session):
    response = session.get('https://api.mit.edu/pass-v1/pass/access_status')
    response.raise_for_status()
    requirements = [Requirement.from_dict(r) for r in json.loads(response.text)['requirements']]
    return {r.id : r for r in requirements}

@dataclass_json
@dataclass(frozen=True)
class Location:
    wait_time: str
    wait_time_text: str
    location_id: int
    name: str
    day_title: str
    open_time: str
    close_time: str
    medical_queue_indicator: bool
    is_open: bool
    is_open_24_hours: bool
    unobserved_pick_up: bool
    unobserved_drop_off: bool
    latitude: Optional[str]
    longitude: Optional[str]

def get_locations(session, days=7, include_self_test=True):
    response = session.get('https://api.mit.edu/pass-v1/pass/medical/queue_times', params={
        'number_of_days': days,
        'medical_test_type': 2 if include_self_test else 1
    })
    response.raise_for_status()
    return [Location.from_dict(l) for l in json.loads(response.text)]

@dataclass_json
@dataclass(frozen=True)
class TestResult:
    test_guid: str
    result: Optional[str] # 'N' (negative), 'P' (positive), 'I' (invalid), None (pending)
    can_download: bool
    test_company: Optional[str]
    test_date: Optional[datetime] = mk_optional_datetime_field()

def get_test_results(session):
    response = session.get('https://api.mit.edu/medical-v1/tests/results?optional=medical') # ,flu_shots,vaccine
    response.raise_for_status()
    return [TestResult.from_dict(r) for r in json.loads(response.text)]

# Individual result as pdf: https://api.mit.edu/medical-v1/tests/result/pdf?test_guid=...

def submit_medical(session, code):
    return session.post('https://api.mit.edu/medical-v1/unobserved/complete', json={
        "barcode": "D-" + code,
    })

def submit_attestation(session, symptoms=False, positive=False, follow_rules=True):
    # Questions: https://api.mit.edu/pass-v1/pass/questions?new=1
    # Hopefully the questions won't change too often
    return session.post('https://api.mit.edu/pass-v1/pass/attestations', json={
        "answers": [
            {"id" : "14", "checked" : symptoms},
            {"id" : "18", "checked" : positive},
            {"id" : "16", "checked" : follow_rules},
        ],
    })