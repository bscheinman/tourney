#!/usr/bin/python

import argparse
import collections
import csv
import decimal

DEBUG_PRINT = False
ROUND_POINTS = [1, 1, 2, 2, 2, 3]


class Team:
    def __init__(self, name, pythag):
        self.name = name
        self.pythag = decimal.Decimal(pythag)


class OverridesMap:
    _overrides = {}

    def init_from_file(self, filepath):
        self._overrides.clear()
        with open(filepath, 'rb') as overrides_file:
            reader = csv.reader(overrides_file)
            for row in reader:
                assert len(row) == 3
                row[2] = decimal.Decimal(row[2])
                self.add_override(*row)

    def add_override(self, name1, name2, prob):
        if name1 < name2:
            self._overrides[(name1, name2)] = prob
        else:
            self._overrides[(name2, name1)] = 1 - prob

    def get_override(self, name1, name2):
        if name1 < name2:
            return self._overrides.get((name1, name2), None)
        else:
            override = self._overrides.get((name2, name1), None)
            return None if override is None else 1 - override


def calculate_win_prob(team1, team2, overrides=None):
    if overrides:
        override = overrides.get_override(team1.name, team2.name)
        if override is not None:
            return override
    win1, win2 = team1.pythag, team2.pythag
    return (win1 * (1 - win2)) / ((win1 * (1 - win2)) + ((1 - win1) * win2))


def read_games_from_file(filepath):
    games = []
    with open(filepath, 'rb') as bracket_file:
        reader = csv.reader(bracket_file)
        for row in reader:
            if not len(row):
                continue
            if len(row) == 2:
                team = Team(*row)
                games.append({team: 1})
            elif len(row) == 4:
                team1 = Team(*row[:2])
                team2 = Team(*row[2:])
                win_prob = calculate_win_prob(team1, team2)
                games.append({team1: win_prob, team2: 1 - win_prob})
            else:
                assert False
    assert games and not (len(games) & (len(games) - 1))
    return games


def calculate_scores(bracket, overrides=None):
    tourney_round = 0
    games = list(bracket)
    total_scores = collections.defaultdict(int)
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
            for game in games:
                for team, win_prob in game.iteritems():
                    print ','.join((team.name, str(round(win_prob, 5))))
                    sum_prob += win_prob
            print 'Sum: ', sum_prob

    return total_scores


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('bracket_file')
    parser.add_argument('--overrides')
    args = parser.parse_args()

    games = read_games_from_file(args.bracket_file)
    overrides = None
    if args.overrides:
        overrides = OverridesMap()
        overrides.init_from_file(args.overrides)

    team_scores = calculate_scores(games, overrides)

    for team, win_prob in team_scores.iteritems():
        print ','.join((team, str(round(win_prob, 3))))
