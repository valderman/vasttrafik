#!/usr/bin/python3
'''Library for looking up Västtrafik departures.
'''
from datetime import datetime, timedelta
from os import stat, path
from tempfile import gettempdir
import json
import requests
import re

__stops_url = 'https://www.vasttrafik.se/api/geography/stopareas'
__departures_url = 'https://www.vasttrafik.se/api/departure-board/'
__stop_file = path.join(gettempdir(), 'vasttrafik-stops.json')
__stops = None

class departure:
    def __init__(self, line, direction, minsLeft, minsNext = None):
        self.line = str(line)
        self.direction = str(direction)
        self.minsLeft = int(minsLeft) if minsLeft != 'now' else 0
        self.minsNext = int(minsNext) if minsNext else None

    def __str__(self):
        out = self.line.rjust(3) + ' → ' + self.direction
        out += ' in ' + str(self.minsLeft) + 'm'
        if self.minsNext:
            out += ' (then ' + str(self.minsNext) + 'm)'
        return out

def __load_stops():
    with open(__stop_file, 'r') as f:
        return json.loads(f.read())

def __refresh_stop_cache():
    global __stops
    if __stops:
        return
    if path.exists(__stop_file):
        mtime = datetime.fromtimestamp(stat(__stop_file).st_mtime)
        if datetime.utcnow() - mtime > timedelta(weeks = 1):
            __fetch_stop_file()
    else:
        __fetch_stop_file()
    __stops = __load_stops()

def __fetch_stop_file():
    stops = requests.get(__stops_url)
    with open(__stop_file, 'w') as f:
        f.write(stops.content.decode('utf-8-sig'))

def find_stops(name):
    '''
    Returns the Västtrafik stop ID and full names all Västtrafik stops
    matching the given regular expression.
    '''
    __refresh_stop_cache()
    for stop in __stops:
        if re.search(name, stop['name'], re.IGNORECASE):
            yield int(stop['gid']), stop['name']

def departures(stop):
    '''
    Returns the next few (as defined by Västtrafik's whims) departures from
    the given stop. Stops are given as Västtrafik stop IDs, obtained by calling
    find_stops.
    '''
    if type(stop) == int:
        result = requests.get(__departures_url + str(stop))
        deps = json.loads(result.content.decode('utf-8-sig'))
        return [departure(d['name'], d['direction'], d['rtMinutesLeft1'], d['rtMinutesLeft2']) for d in deps]
    else:
        raise TypeError

if __name__ == "__main__":
    from sys import argv, exit
    from pathlib import Path
    def read_defaults():
        default_file = path.join(str(Path.home()), '.vasttrafik')
        if path.exists(default_file):
            with open(default_file, "r") as f:
                for ln in f:
                    yield ln.rstrip()

    regexes = list(read_defaults())
    if len(argv) < 2:
        if not regexes:
            print("Prints the next few Västtrafik departures from the stops matching "
                  "the given regular expressions.")
            print("Usage: " + argv[0] + " <stop> [<stop2> ...]")
            exit(0)
    else:
        regexes = argv[1:]

    stops = [stop for stops in map(find_stops, regexes)
             for stop in stops if stop]
    if not stops:
        print("No matching stops found.")
        exit(1)

    for stop in stops:
        print(stop[1] + ':')
        for dep in departures(stop[0]):
            print('  ' + str(dep))
