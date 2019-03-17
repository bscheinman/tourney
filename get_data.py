#!/usr/bin/python

from bs4 import BeautifulSoup
from math import sqrt
import re
import sys
import urllib2

RATINGS_URL = 'http://kenpom.com/'
BRACKET_URL = 'http://espn.go.com/ncb/bracketology'
GAMEPREDICT_URL = 'http://gamepredict.us/teams/matchup_table?team_a={0}&team_b={1}&neutral=true'
ODDS_URL = 'http://www.vegasinsider.com/college-basketball/odds/las-vegas/money/'
CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'

NAME_CONVERSIONS = {
    'Miami': 'Miami FL',
    'Southern Cal': 'USC',
    'St. Mary\'s (ca)': 'Saint Mary\'s',
    'Virginia Commonwealth': 'VCU',
    'Miami (fl)': 'Miami FL',
    'Middle Tennessee St.': 'Middle Tennessee',
    'Se Louisiana': 'Southeastern Louisiana',
    'Arkansas-pine Bluff': 'Arkansas Pine Bluff',
    'Louisiana': 'Louisiana Lafayette',
    'Charleston': 'College of Charleston',
    'Nc St.': 'North Carolina St.',
    'Texas A&m;': 'Texas A&M;',
    'Loyola-chicago': 'Loyola Chicago',
    'Cs Fullerton': 'Cal St. Fullerton',
    'Suny-buffalo': 'Buffalo',
    'Md-baltimore County': 'UMBC',
    'Texas Am': 'Texas A&M;',
    'Pennsylvania': 'Penn',
    'College Of Charleston': 'College of Charleston',
    'Texas Christian': 'TCU',
    'Ole Miss': 'Mississippi',
    'Gardner-webb': 'Gardner Webb',
}

WORD_ABBREVS = set([
    'Unc',
    'Ucla',
    'Smu',
    'Vcu',
    'Uc',
    'Tcu',
    'Liu',
    'Usc',
    'A&m',
    'A&m;',
    'Lsu',
    'Ucf',
])

WORD_CONVERSIONS = {
    'State': 'St.',
    'St': 'St.',
    'Marys': 'Mary\'s',
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
    cleaned = ' '.join(words)
    return NAME_CONVERSIONS.get(cleaned, cleaned)

def get_bracket(out_file):
    html = urllib2.urlopen(BRACKET_URL).read()
    soup = BeautifulSoup(html, 'html.parser')
    bracket = soup.find('div', { 'class': 'bracket' })
    for entry in bracket.find_all('div', {'class': 'team'}):
        team_names = [clean_name(link.string) for link in entry.find_all('a')]
        out_file.write('{0}\n'.format(','.join(team_names)))

def get_ratings(out_file):
    html = urllib2.urlopen(RATINGS_URL).read()
    soup = BeautifulSoup(html, 'html.parser')
    ratings = soup.find('table', { 'id': 'ratings-table' })
    ratings = ratings.tbody
    for row in ratings.find_all('tr'):
        columns = row.find_all('td')
        data_columns = row.find_all('td', {'class': 'td-left'})
        if not columns or not data_columns or len(data_columns) < 3:
            continue
        team_name = columns[1].a.string
        offense = data_columns[0].string
        defense = data_columns[1].string
        tempo = data_columns[2].string
        out_file.write('{0}\n'.format('|'.join((team_name, offense, defense, tempo))))

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

ODDS_REGEX = re.compile('[-+][1-9][0-9]{2,}')
def extract_odds(cell_str):
    return ODDS_REGEX.findall(cell_str)

def convert_american_odds(odds_str):
    num_comp = int(odds_str[1:])
    if odds_str[0] == '-':
        return num_comp / (100.0 + num_comp)
    elif odds_str[0] == '+':
        return 100.0 / (100.0 + num_comp)
    else:
        assert False

def get_overrides(overrides_file):
    req = urllib2.Request(ODDS_URL, headers={'User-Agent': CHROME_UA})
    html = urllib2.urlopen(req).read()
    #with open('odds.html', 'r') as html_file:
        #html = html_file.read()
    soup = BeautifulSoup(html, 'html.parser')
    odds_table = soup.find_all('table', {'class': 'frodds-data-tbl'})[0]
    rows = odds_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue

        matchup_cell = cells[0]
        odds_cell = cells[2]

        team_links = matchup_cell.find_all('a')
        if len(team_links) != 2:
            continue

        road_team = team_links[0].string
        home_team = team_links[1].string

        odds_links = odds_cell.find_all('a')
        if not odds_links:
            continue

        odds = extract_odds(odds_links[0].text)
        if len(odds) == 0:
            print road_team, home_team
        assert len(odds) == 2

        road_win = convert_american_odds(odds[0])
        home_win = convert_american_odds(odds[1])
        avg_win = sqrt(road_win * (1 - home_win))

        overrides_file.write('{0}\n'.format(','.join((clean_name(road_team),
            clean_name(home_team), str(round(avg_win, 3))))))

def read_team_names(bracket_file):
    names = []
    for line in bracket_file:
        if line.strip():
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
    elif sys.argv[1] == 'odds':
        with open('odds.txt', 'w') as overrides_file:
            get_overrides(overrides_file)
    else:
        print 'unrecognized data type {}'.format(sys.argv[1])
