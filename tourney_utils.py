from collections import defaultdict
import csv
from decimal import Decimal
import random
from scipy.stats import norm

DEBUG_PRINT = False
#DEBUG_PRINT = True

AVG_SCORING = Decimal('104.6')
AVG_TEMPO = Decimal('67.7')
SCORING_STDDEV = Decimal('11.0')

total_overrides = 0
overrides_used = 0

class Team:
    def __init__(self, name, ratings=None):
        self.name = name
        if ratings is None:
            self.offense = None
            self.defense = None
            self.tempo = None
        else:
            self.offense, self.defense, self.tempo = tuple(map(Decimal, ratings))
            self.offense = (self.offense / AVG_SCORING) - 1
            self.defense = (self.defense / AVG_SCORING) - 1
            if DEBUG_PRINT:
                print '\t\t'.join(map(str, (self.name, self.offense, self.defense, self.tempo)))

class OverridesMap:
    _overrides = {}

    def read_from_file(self, filepath):
        global total_overrides
        with open(filepath, 'rb') as overrides_file:
            reader = csv.reader(overrides_file)
            for row in reader:
                if not row:
                    continue
                assert len(row) == 3
                row[2] = Decimal(row[2])
                self.add_override(*row)
                total_overrides += 1

    def add_override(self, name1, name2, prob):
        if name1 < name2:
            self._overrides[(name1, name2)] = prob
        else:
            self._overrides[(name2, name1)] = 1 - prob

    def remove_override(self, name1, name2):
        if name1 < name2:
            del self._overrides[(name1, name2)]
        else:
            del self._overrides[(name2, name1)]

    def get_override(self, name1, name2):
        global total_overrides
        global overrides_used
        if name1 < name2:
            override = self._overrides.get((name1, name2), None)
        else:
            override = self._overrides.get((name2, name1), None)
            if override is not None:
                override = 1 - override
        if override is not None:
            total_overrides -= 1
            overrides_used += 1
            if DEBUG_PRINT:
                sys.stderr.write('using override for {0} vs. {1}\n'.format(
                    name1, name2))
        return override

def read_ratings_file(in_file):
    all_ratings = {}
    for line in in_file:
        fields = line.strip().split('|')
        team = fields[0]
        ratings = fields[1:]
        all_ratings[team] = ratings
    return all_ratings

# based on old kenpom pythag ratings
'''
def calculate_win_prob(team1, team2, overrides=None):
    if overrides:
        override = overrides.get_override(team1.name, team2.name)
        if override is not None:
            return override
    win1, win2 = team1.rating, team2.rating
    return (win1 * (1 - win2)) / ((win1 * (1 - win2)) + ((1 - win1) * win2))
'''

def calculate_win_prob(team1, team2, overrides=None):
    if overrides:
        override = overrides.get_override(team1.name, team2.name)
        if override is not None:
            return override

    if DEBUG_PRINT:
        print 'scoring {0}-{1}'.format(team1.name, team2.name)

    # number of expected possessions per team
    tempo = (team1.tempo * team2.tempo) / AVG_TEMPO

    # teams' points per possession, as percentage of national average
    team1_scoring = 1 + team1.offense + team2.defense
    team2_scoring = 1 + team2.offense + team1.defense

    # teams' actual points per possession
    team1_ppp = team1_scoring * (AVG_SCORING / 100)
    team2_ppp = team2_scoring * (AVG_SCORING / 100)

    # expected point differential is difference in per-possession scoring
    # times expected number of possesions per team
    team1_score = team1_ppp * tempo
    team2_score = team2_ppp * tempo
    point_diff = team1_score - team2_score

    if DEBUG_PRINT:
        print 'expected score {0}-{1}'.format(team1_score, team2_score)

    # deviation in scoring margin should scale (linearly?) based on tempo and
    # possibly also scoring rates
    stddev = ((team1_scoring + team2_scoring) / 2) * \
            (tempo / AVG_TEMPO) * SCORING_STDDEV
    
    # find probability that actual point diff will be positive
    return Decimal(norm.cdf(float(point_diff / stddev)))

def read_games_from_file(filepath, ratings, overrides=None):
    games = []
    with open(filepath, 'rb') as bracket_file:
        reader = csv.reader(bracket_file)
        for row in reader:
            if not len(row):
                continue
            if len(row) == 1:
                team = Team(name=row[0], ratings=ratings[row[0]])
                games.append({team: Decimal(1)})
            elif len(row) == 2:
                team1 = Team(name=row[0], ratings=ratings[row[0]])
                team2 = Team(name=row[1], ratings=ratings[row[1]])
                win_prob = calculate_win_prob(team1, team2, overrides)
                games.append({team1: win_prob, team2: 1 - win_prob})
            else:
                assert False
    assert games and not (len(games) & (len(games) - 1))
    return games


def game_transform_prob(child1, child2, overrides):
    parent = {}

    for team1, win1 in child1.iteritems():
        parent[team1] = 0
        for team2, win2 in child2.iteritems():
            if team2 not in parent:
                parent[team2] = 0
            game_prob = win1 * win2
            p1 = calculate_win_prob(team1, team2, overrides)
            parent[team1] += game_prob * p1
            parent[team2] += game_prob * (1 - p1)

    return parent


def game_transform_sim(child1, child2, overrides):
    assert len(child1) == 1 and len(child2) == 1
    team1 = child1.keys()[0]
    team2 = child2.keys()[0]

    prob = calculate_win_prob(team1, team2, overrides)
    winner = team1 if random.random() < prob else team2

    return { winner : Decimal(1) }


def calculate_scores(bracket, scoring, game_transform, overrides=None):
    tourney_round = 0
    games = list(bracket)
    total_scores = defaultdict(lambda: Decimal(0))
    while len(games) > 1:
        new_games = []
        for i in xrange(len(games) / 2):
            child1, child2 = games[2 * i: 2 * i + 2]
            parent = game_transform(child1, child2, overrides)
            for team, win_prob in parent.iteritems():
                total_scores[team.name] += win_prob * scoring[tourney_round]
            new_games.append(parent)

        games = new_games
        tourney_round += 1

        if DEBUG_PRINT:
            print 'Round', tourney_round
            sum_prob = 0
            team_scores = []
            for game in games:
                for item in game.iteritems():
                    team_scores.append(item)
            for team, win_prob in sorted(team_scores, key=lambda g: g[0].name):
                print ','.join((team.name, str(round(win_prob, 5))))
                sum_prob += win_prob
            print 'Sum: ', sum_prob

    return total_scores


def calculate_scores_prob(bracket, scoring, overrides=None):
    return calculate_scores(bracket, scoring, game_transform_prob, overrides)


def calculate_scores_sim(bracket, scoring, overrides=None):
    return calculate_scores(bracket, scoring, game_transform_sim, overrides)



