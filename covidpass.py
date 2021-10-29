#!/usr/bin/env python3
import sys
import time
from datetime import datetime, timedelta

from covidpass_api import *

# Show a warning if requirement expires in at most this many hours
warning_hours = {
    "medical": 24,
    "attestation": 6,
}

def get_now():
    return datetime.now().astimezone().replace(microsecond=0)

def format_datetime(dt):
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M')
    else:
        return ''

def format_date(dt):
    if dt:
        return dt.strftime('%Y-%m-%d')
    else:
        return ''

# === Interactive commands

def print_locations(session, days=4):
    locations = get_locations(session, days)
    print(f'| {"day":^6} | {"id":^3} | {"title":^20} | {"open":^8} | {"close":^8} | {"self-test":^9} |')
    print(f'|-{"-"*6}-|-{"-"*3}:|:{"-"*20}:|:{"-"*8}:|:{"-"*8}:|:{"-"*9}:|')
    for l in locations:
        if l.is_open:
            print(f'| {l.day_title:6} | {l.location_id:>3} | {l.name:^20} | {l.open_time:^8} | {l.close_time:^8} | '
                    f'{[["no", "pick-up"], ["drop-off", "yes"]][l.unobserved_drop_off][l.unobserved_pick_up]:^9} |')

def print_test_results(session, count=5):
    results = get_test_results(session)
    print(f'| {"date":^10} | {"":^1} | {"company":^10} |')
    print(f'|:{"-"*10}:|:{"-"*1}:|:{"-"*10}:|')
    for r in results[:count]:
        print(f'| {format_date(r.test_date):^10} | {r.result or "?":^1} | {r.test_company or "":^10} | {r.test_guid}')
    if len(results) > count:
        print(f'(and {len(results) - count} more)')

def print_status(session):
    requirements = get_requirements(session)

    # Yes, it's wider than 80 characters. I don't care.
    print(f'| {"id":^11} | {"title":^20} | {"status":^13} | {"last completion":^16} | {"next completion":^16} |')
    print(f'|-{"-"*11}-|-{"-"*20}-|:{"-"*13}:|:{"-"*16}:|:{"-"*16}:|')
    for r in requirements.values():
        print(f'| {r.id:11} | {r.title_web:20} | {r.status:^13} | '
                f'{format_datetime(r.last_completion):^16} | '
                f'{format_datetime(r.next_completion):^16} |')
    print()

    now = get_now()
    for r in requirements.values():
        if r.next_completion:
            warn_hours = warning_hours[r.id]
            if r.next_completion < now:
                print(f'{r.title_web} has expired on {r.next_completion}!')
            elif warn_hours and r.next_completion - now < timedelta(hours=warn_hours):
                print(f'{r.title_web} expires on {r.next_completion:%Y-%m-%d %H:%M} (in {r.next_completion - now})!')
        elif r.status == 'incomplete':
            print(f'{r.title_web} is incomplete!')

    print()
    test_results = get_test_results(session)
    if test_results:
        if test_results[0].result == None:
            print(f'Your latest COVID test ({format_date(test_results[0].test_date)}) is still pending.')
        elif test_results[0].result == 'P':
            print(f'Your latest COVID test ({format_date(test_results[0].test_date)}) was positive.')
            print('Please use the official web app (https://covidpass.mit.edu/) instead of this CLI until you are out of isolation.')
        elif test_results[0].result == 'N':
            #print(f'Your latest COVID test ({format_date(test_results[0].test_date)}) was negative.')
            pass
        elif test_results[0].result == 'I':
            print(f'Your latest COVID test ({format_date(test_results[0].test_date)}) was invalid.')
            print('This might mean you didn\'t take the sample correctly. You should probably redo the test.')
        else:
            print(f'Your latest COVID test ({format_date(test_results[0].test_date)}) result was `{test_results[0].result}`.')
            print('Please submit an issue or a pull request if you figure out what this means.')

def submit_medical_interactive(session):
    code1 = input('Enter your 10-digit code: D-')
    if len(code1) != 10:
        if input('Your code is not 10 digits long. Continue anyways? (y/N)').lower() != 'y':
            return
    print('  1. Wash hands for 20 seconds')
    print('  2. Unscrew and discard the cap')
    print('  3. Take the swap')
    print('  4. Rotate 3 times in first nostril')
    print('  5. Slide up and down 3 times')
    print('  6. Hold for 10 seconds')
    print('  7. Repeat 4-6 in the other nostril')
    print('  8. Put the swab in the collection device')
    print('  9. Put the collection device into the biohazard bag')

    code2 = input('Re-enter your code: D-')
    if code1 != code2:
        print('Codes don\'t match!')
        return

    response = submit_medical(session, code1)
    if response.ok:
        print('Medical submitted. Bring your the biohazard bag to one test collection points (see `covidpass.py locations`).')
    else:
        print('Failed to submit medical test.')
        print(f'{response.status-code} {response.reason}')
        print(response.text)

def submit_attestation_interactive(session):
    # TODO: check if there have been any positive tests in the last 10 days

    response = submit_attestation(session)
    if response.ok:
        print('Daily attestation submitted successfully!')
    else:
        print('Failed to submit attestation.')
        print(f'{response.status-code} {response.reason}')
        print(response.text)




def main():
    args = sys.argv[1:]
    if args == ['help'] or args == ['?'] or args == ['-h']:
        print('`covidpass.py help` to read this message again.')
        print('`covidpass.py` or `covidpass.py status` to check your covid status.')
        print('`covidpass.py map` to get a link to the map pdf.')
        print('`covidpass.py locations <n>` to see the list of testing locations for the next `n` days. Default is 4.')
        print('`covidpass.py results <n>` to see `n` of your test results. Default is 5.')
        print('`covidpass.py attest` to submit daily attestation.')
        print('`covidpass.py medical` to submit a medical at-home test.')
        return

    try:
        credentials = read_credentials()
    except Exception as e:
        print('Could not open `credentials.json` file.')
        print('Make sure it is in your currect working directory.')
        raise e

    try:
        with Session(credentials) as session:
            if args == [] or args == ['status']:
                print_status(session)
            elif args == ['map']:
                print('https://covidapps.mit.edu/sites/default/files/documents/MITCampusAccessMap.pdf')
            elif args == ['locations']:
                print_locations(session)
            elif len(args) == 2 and args[0] == 'locations':
                try:
                    print_locations(session, int(args[1]))
                except ValueError as e:
                    print('Invalid argument. Number of days should be an integer')
            elif args == ['results']:
                print_test_results(session)
            elif len(args) == 2 and args[0] == 'results':
                try:
                    print_test_results(session, int(args[1]))
                except ValueError as e:
                    print('Invalid argument. Number of test results should be an integer')
            elif args == ['attest']:
                submit_attestation_interactive(session)
            elif args == ['medical']:
                submit_medical_interactive(session)
            else:
                print('Unknown command :(')
                print('Try `covidpass.py help`.')
    except ConnectionError as e:
        print('Failed to connect to ATLAS/CovidPass servers. Check your internet connection.')
        print(e)
    #try:
    #except Exception as e:
    #    print(e)
    #    alert('Unhandled Exception!', e)

if __name__ == '__main__':
    main()