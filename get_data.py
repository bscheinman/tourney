#!/usr/bin/python

import sys

from bs4 import BeautifulSoup
import urllib2

RATINGS_URL = 'http://kenpom.com/'
BRACKET_URL = 'http://espn.go.com/ncb/bracketology'
GAMEPREDICT_URL = 'http://gamepredict.us/teams/matchup_table?team_a={0}&team_b={1}&neutral=true'

NAME_CONVERSIONS = {
    'Miami': 'Miami FL'
}

WORD_ABBREVS = set([
    'Unc',
    'Ucla',
    'Smu',
    'Vcu',
    'Uc',
])

WORD_CONVERSIONS = {
    'St': 'St.',
}

def clean_name(s):
    words = s.split()
    for i in xrange(len(words)):
        word = words[i].lower()
        word = word[0].upper() + word[1:].lower()
        if word in WORD_ABBREVS:
            word = word.upper()
        word = WORD_CONVERSIONS.get(word, word)
        words[i] = word
    return ' '.join(words)

def get_bracket(out_file):
    html = urllib2.urlopen(BRACKET_URL).read()
    soup = BeautifulSoup(html, 'html.parser')
    bracket = soup.find('div', { 'class': 'bracket' })
    for entry in bracket.find_all('div', {'class': 'team'}):
        team_names = [clean_name(link.string) for link in entry.find_all('a')]
        team_names = [NAME_CONVERSIONS.get(name, name) for name in team_names]
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

def get_pairwise_prob(a, b):
    html = urllib2.urlopen(GAMEPREDICT_URL.format(urllib2.quote(a), urllib2.quote(b))).read()
    soup = BeautifulSoup(html, 'html.parser')
    cols = soup.find_all('div', {'class': 'col-xs-6'})
    perc_str = cols[2].find_all('p')[0].string.strip()
    return int(perc_str[:-1]) / 100.0

# Start with the lazy approach of scraping all probs from gamepredict
def get_pairwise_probs(teams, out_file):
    for i in xrange(len(teams)):
        for j in xrange(i + 1, len(teams)):
            try:
                prob = get_pairwise_prob(teams[i], teams[j])
                out_file.write('{0}\n'.format(','.join((teams[i], teams[j], str(prob)))))
            except:
                sys.stderr.write('prob failed for teams {0}, {1}\n'.format(teams[i], teams[j]))
                raise

def read_team_names(bracket_file):
    names = []
    for line in bracket_file:
        names += line.strip().split(',')
    return names

if __name__ == '__main__':
    if sys.argv[1] == 'bracket':
        with open('bracket.txt', 'w') as bracket_file:
            get_bracket(bracket_file)
    elif sys.argv[1] == 'ratings':
        with open('ratings.txt', 'w') as ratings_file:
            get_ratings(ratings_file)
    elif sys.argv[1] == 'probs':
        with open('bracket.txt', 'r') as bracket_file:
            all_teams = read_team_names(bracket_file)
        with open('probs.txt', 'w') as probs_file:
            get_pairwise_probs(all_teams, probs_file)
