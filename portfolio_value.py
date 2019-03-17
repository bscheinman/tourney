import cPickle as pickle
from decimal import Decimal
import json
import sys
import urllib2

import tourney_utils as tourney

# why do i do this to myself
CIX_NAME_CONVERSIONS = {
    'Michigan State' : 'Michigan St.',
    'Southern California' : 'USC',
    'Middle Tennessee State' : 'Middle Tennessee',
    'Miami' : 'Miami FL',
    'Iowa State' : 'Iowa St.',
    'Kent State' : 'Kent St.',
    'Nevada Reno' : 'Nevada',
    'Virginia Commonwealth' : 'VCU',
    'California Davis' : 'UC Davis',
    'Wichita State' : 'Wichita St.',
    'Florida State' : 'Florida St.',
}


class PortfolioState:
    def __init__(self, tournament, positions, point_delta=Decimal(1)):
        self.tournament = tournament
        self.positions = positions
        self.team_deltas = {}
        self.pairwise_deltas = {}
        self.point_delta = point_delta

    def compute_deltas(self, teams=None):
        if teams:
            for team in teams:
                self.team_deltas[team] = get_team_portfolio_delta(self.positions,
                        self.tournament, team, point_delta=self.point_delta)
                self.pairwise_deltas[team] = get_team_pairwise_deltas(
                        self.positions, self.tournament, team,
                        point_delta=self.point_delta)
        else:
            self.team_deltas, self.pairwise_deltas = get_all_team_deltas(
                    self.positions, self.tournament,
                    point_delta=self.point_delta)


    def store_deltas(self, path):
        with open(path, 'wb') as outfile:
            pickle.dump((self.team_deltas, self.pairwise_deltas), outfile)

    def load_deltas(self, path):
        with open(path, 'rb') as infile:
            self.team_deltas, self.pairwise_deltas = pickle.load(infile)


def read_values(values_file):
    values = {}
    for line in values_file.readlines():
        team, value = tuple(line.strip().split(','))
        values[team] = Decimal(value)
    return values

def get_portfolio_value(positions, values):
    total_value = Decimal(0)
    for team, count in positions.iteritems():
        if not count:
            continue

        if team == 'points':
            total_value += Decimal(count)
        else:
            try:
                team_name = CIX_NAME_CONVERSIONS.get(team, team)
                value = values[team_name]
            except KeyError:
                print 'missing team ' + team
                value = Decimal(0)
            total_value += Decimal(value * count)

    return total_value

def game_delta(positions, tournament, team1, team2):
    original_override = tournament.overrides.get_override(team1, team2)

    tournament.overrides.add_override(team1, team2, Decimal(1))
    win_values = tournament.calculate_scores_prob()
    win_portfolio = get_portfolio_value(positions, win_values)

    tournament.overrides.add_override(team1, team2, Decimal(0))
    loss_values = tournament.calculate_scores_prob()
    loss_portfolio = get_portfolio_value(positions, loss_values)

    if original_override:
        tournament.overrides.add_override(team1, team2, original_override)
    else:
        tournament.overrides.remove_override(team1, team2)

    return win_portfolio, loss_portfolio

def get_team_delta(tournament, team, point_delta=Decimal(1)):
    point_adjustment = point_delta / tourney.AVG_SCORING

    orig_team = tournament.ratings[team]
    orig_offense = orig_team.offense
    orig_defense = orig_team.defense

    positive_team = orig_team.copy()
    positive_team.offense += point_adjustment
    positive_team.defense -= point_adjustment
    tournament.ratings[team] = positive_team
    positive_scores = tournament.calculate_scores_prob()

    negative_team = orig_team.copy()
    negative_team.offense -= point_adjustment
    negative_team.defense += point_adjustment
    tournament.ratings[team] = negative_team
    negative_scores = tournament.calculate_scores_prob()

    tournament.ratings[team] = orig_team

    return positive_scores, negative_scores

def calculate_team_portfolio_delta(positions, positive_values, negative_values):
    positive_value = get_portfolio_value(positions, positive_values)
    negative_value = get_portfolio_value(positions, negative_values)

    return positive_value - negative_value

def get_team_portfolio_delta(positions, tournament, team,
        point_delta=Decimal(1)):
    positive_values, negative_values = get_team_delta(tournament, team,
            point_delta=point_delta)
    
    return calculate_team_portfolio_delta(positions, positive_values,
            negative_values)

def calculate_team_pairwise_deltas(positive_values, negative_values):
    team_deltas = {}

    for team, positive_value in positive_values.iteritems():
        negative_value = negative_values[team]
        #print team, positive_value, negative_value
        share_delta = positive_value - negative_value
        team_deltas[team] = share_delta

    return team_deltas

def get_team_pairwise_deltas(positions, tournament, team,
        point_delta=Decimal(1)):
    positive_values, negative_values = get_team_delta(tournament, team,
            point_delta=point_delta)

    return calculate_team_pairwise_deltas(positive_values, negative_values)
    
def get_all_team_deltas(positions, tournament, point_delta=Decimal(1)):
    team_deltas = {}
    pairwise_deltas = {}

    for team in tourney.get_bracket_teams(tournament.bracket):
        positive_values, negative_values = get_team_delta(tournament, team,
                point_delta=point_delta)

        team_deltas[team] = calculate_team_portfolio_delta(positions,
                positive_values, negative_values)
        pairwise_deltas[team] = calculate_team_pairwise_deltas(positive_values,
                negative_values)

        print 'computed deltas for {0}'.format(team)

    return team_deltas, pairwise_deltas

if __name__ == '__main__':
    positions = get_positions(API_KEY)
    with open(sys.argv[1], 'r') as values_file:
        values = read_values(values_file)

    print get_portfolio_value(positions, values)
