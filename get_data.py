#!/usr/bin/python

import sys

from bs4 import BeautifulSoup
import urllib2

RATINGS_URL = 'http://kenpom.com/'
BRACKET_URL = 'http://espn.go.com/ncb/bracketology'

def get_bracket(out_file):
    html = urllib2.urlopen(BRACKET_URL).read()
    soup = BeautifulSoup(html)
    bracket = soup.find('div', { 'class': 'bracket' })
    for link in bracket.find_all('a'):
        team_name = link.string
        replacement = NAME_CONVERSIONS.get(team_name.lower(), None)
        if replacement:
            team_name = replacement
        out_file.write('{0}\n'.format(team_name))

def get_ratings(out_file):
    html = urllib2.urlopen(RATINGS_URL).read()
    soup = BeautifulSoup(html)
    ratings = soup.find('table', { 'id': 'ratings-table' })
    ratings = ratings.tbody
    for row in ratings.find_all('tr'):
        columns = row.find_all('td')
        if not columns:
            continue
        team_name = columns[1].a.string
        team_rating = columns[4].string
        out_file.write('{0}|{1}\n'.format(team_name, team_rating))

if __name__ == '__main__':
    with open('ratings.txt', 'w') as ratings_file:
        get_ratings(ratings_file)
