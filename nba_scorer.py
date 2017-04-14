#!/usr/bin/python

from bs4 import BeautifulSoup
from decimal import Decimal
import urllib2
import sys

ROUND_SCORES = [1, 1, 2, 2]
URL = 'https://projects.fivethirtyeight.com/2017-nba-predictions'

#html = urllib2.urlopen(URL).read()

with open(sys.argv[1], 'r') as html_file:
    html = html_file.read()

soup = BeautifulSoup(html, 'html.parser')
standings = soup.find('table', { 'id' : 'standings-table' })
teams = standings.find_all('tr')
for team in teams[4:]:
    cells = team.find_all('td')
    if len(cells) < 10:
        continue
    name = cells[4]['data-str']
    round_probs = cells[6:10]
    score = Decimal(0)
    for i in xrange(len(ROUND_SCORES)):
        prob_string = round_probs[i].string[:-1]
        if not prob_string:
            break
        elif prob_string[0] == '<':
            prob = 0
        else:
            prob = Decimal(prob_string) / 100
        score += prob * ROUND_SCORES[i]
    if score:
        print name, score
