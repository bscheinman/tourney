#!/usr/bin/python

import argparse
import collections
import csv
from decimal import Decimal
import sys

DEBUG_PRINT = False
#DEBUG_PRINT = True
ROUND_POINTS = [1, 1, 2, 2, 2, 3]

total_overrides = 0

class Team:
    def __init__(self, name, rating=0.0):
        self.name = name
        self.rating = Decimal(rating)

class OverridesMap:
    _overrides = {}

    def init_from_file(self, filepath):
        global total_overrides
        self._overrides.clear()
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

    def get_override(self, name1, name2):
        global total_overrides
        if name1 < name2:
            override = self._overrides.get((name1, name2), None)
        else:
            override = self._overrides.get((name2, name1), None)
            if override is not None:
                override = 1 - override
        if override is not None:
            total_overrides -= 1
            if DEBUG_PRINT:
                sys.stderr.write('using override for {0} vs. {1}\n'.format(
                    name1, name2))
        return override

def read_ratings_file(in_file):
    ratings = {}
    for line in in_file:
        team, rating = tuple(field.strip() for field in line.split('|'))
        ratings[team] = rating
    return ratings


def calculate_win_prob(team1, team2, overrides=None):
    if overrides:
        override = overrides.get_override(team1.name, team2.name)
        if override is not None:
            return override
    win1, win2 = team1.rating, team2.rating
    return (win1 * (1 - win2)) / ((win1 * (1 - win2)) + ((1 - win1) * win2))


def read_games_from_file(filepath, ratings, overrides=None):
    games = []
    with open(filepath, 'rb') as bracket_file:
        reader = csv.reader(bracket_file)
        for row in reader:
            if not len(row):
                continue
            if len(row) == 1:
                team = Team(name=row[0], rating=ratings[row[0]])
                games.append({team: Decimal(1)})
            elif len(row) == 2:
                team1 = Team(name=row[0], rating=ratings[row[0]])
                team2 = Team(name=row[1], rating=ratings[row[1]])
                win_prob = calculate_win_prob(team1, team2, overrides)
                games.append({team1: win_prob, team2: 1 - win_prob})
            else:
                assert False
    assert games and not (len(games) & (len(games) - 1))
    return games


def calculate_scores(bracket, overrides=None):
    tourney_round = 0
    games = list(bracket)
    total_scores = collections.defaultdict(lambda: Decimal(2))
    while len(games) > 1:
        new_games = []
        for i in xrange(len(games) / 2):
            child1, child2 = games[2 * i: 2 * i + 2]
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

            for team, win_prob in parent.iteritems():
                total_scores[team.name] += win_prob * ROUND_POINTS[tourney_round]
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


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('bracket_file')
    parser.add_argument('ratings_file')
    parser.add_argument('--overrides')
    args = parser.parse_args()

    with open(args.ratings_file, 'r') as ratings_file:
        ratings = read_ratings_file(ratings_file)

    overrides = None
    if args.overrides:
        overrides = OverridesMap()
        overrides.init_from_file(args.overrides)
    games = read_games_from_file(args.bracket_file, ratings, overrides)

    team_scores = calculate_scores(games, overrides)

    for team, win_prob in sorted(team_scores.iteritems(), key=lambda g: g[0]):
        print ','.join((team, str(round(win_prob, 3))))

    assert total_overrides == 0
