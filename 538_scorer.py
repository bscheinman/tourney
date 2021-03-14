#!/usr/bin/python

from datetime import datetime
from decimal import Decimal
from gzip import GzipFile
import json
import pycurl
from StringIO import StringIO
import urllib2

ROUND_SCORES = [0, 1, 1, 2, 2, 2, 3]
ENDPOINT = 'https://projects.fivethirtyeight.com/march-madness-api/{0}/latest.json'.format(datetime.now().year)
ENDPOINT = 'https://projects.fivethirtyeight.com/march-madness-api/{0}/madness.json'.format(datetime.now().year)

def score(data):
    scores = {}
    teams = data['forecasts']['mens']['current_run']['teams']
    for team in teams:
        name = team['team_name']
        score = Decimal(0)
        for i in range(len(ROUND_SCORES)):
            p = Decimal(team['rd{0}_win'.format(i + 1)])
            #print(' '.join(map(str, (name, i, p))))
            score += p * ROUND_SCORES[i]
        scores[name] = score
    return scores

compressed_data = urllib2.urlopen(ENDPOINT).read()
compressed_file = StringIO()
compressed_file.write(compressed_data)
compressed_file.seek(0)
raw_file = GzipFile(fileobj=compressed_file, mode='rb')
raw_data = raw_file.read()
data = json.loads(raw_data)
scores = score(data)
scores = sorted(scores.iteritems(), key=lambda x: x[0])

for team, score in scores:
    if score:
        print('{0},{1}'.format(team, round(score, 3)))
