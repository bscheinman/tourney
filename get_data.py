#!/usr/bin/python

import sys

from bs4 import BeautifulSoup
import urllib2

RATINGS_URL = 'http://kenpom.com/'
BRACKET_URL = 'http://espn.go.com/ncb/bracketology'

NAME_CONVERSIONS = {}

def get_bracket(out_file):
    html = urllib2.urlopen(BRACKET_URL).read()
    soup = BeautifulSoup(html, 'html.parser')
    bracket = soup.find('div', { 'class': 'bracket' })
    for entry in bracket.find_all('div', {'class': 'team'}):
        team_names = [link.string for link in entry.find_all('a')]
        team_names = [NAME_CONVERSIONS.get(name.lower(), name) for name in team_names]
        out_file.write('{0}\n'.format(','.join(team_names)))

def get_ratings(out_file):
    html = urllib2.urlopen(RATINGS_URL).read()
    soup = BeautifulSoup(html, 'html.parser')
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
    with open('bracket.txt', 'w') as bracket_file:
        get_bracket(bracket_file)
