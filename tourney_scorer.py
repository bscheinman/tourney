import argparse
from collections import defaultdict
from decimal import Decimal
import sys

import portfolio_value as pv
import tourney_utils as tourney

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('operation')
    parser.add_argument('bracket_file')
    parser.add_argument('ratings_file', nargs='?', default=None)
    parser.add_argument('--overrides', action='append')
    parser.add_argument('--sort', action='store', default='name')
    parser.add_argument('--calcutta', action='store_true')
    parser.add_argument('--simulations', action='store', type=int, default=10000)
    args = parser.parse_args()

    if args.sort == 'name':
        sorter = lambda g: g[0]
    elif args.sort == 'score':
        sorter = lambda g: -1 * g[1]
    else:
        sys.stderr.write('invalid sort type\n')
        exit(1)

    if args.ratings_file:
        with open(args.ratings_file, 'r') as ratings_file:
            ratings = tourney.read_ratings_file(ratings_file)
    else:
        ratings = defaultdict(lambda: None)

    if args.calcutta:
        scoring = tourney.CALCUTTA_POINTS
    else:
        scoring = tourney.ROUND_POINTS

    overrides = tourney.OverridesMap()
    if args.overrides:
        for overrides_file in args.overrides:
            overrides.read_from_file(overrides_file)
    games = tourney.read_games_from_file(args.bracket_file, ratings, overrides)

    state = tourney.TournamentState(bracket=games, ratings=ratings,
            scoring=scoring, overrides=overrides)

    if args.operation == 'expected':
        team_scores = state.calculate_scores_prob()

        for team, win_prob in sorted(team_scores.iteritems(), key=sorter):
            print ','.join((team, str(round(win_prob, 3))))
    elif args.operation == 'portfolio_simulate':
        positions = pv.get_positions(API_KEY)
        portfolio_values = []
        for i in xrange(args.simulations):
            scores = state.calculate_scores_sim()
            values = pv.get_portfolio_value(positions, scores)
            portfolio_values.append(values)
        portfolio_values = sorted(portfolio_values)
        percentiles = [1, 10, 25, 50, 75, 90, 99]
        print 'min value: {0}'.format(portfolio_values[0])
        for percentile in percentiles:
            print '{0} percentile value: {1}'.format(percentile, portfolio_values[(percentile * args.simulations) / 100])
        print 'max value: {0}'.format(portfolio_values[-1])
    elif args.operation == 'portfolio_expected':
        pass
    else:
        print 'invalid operation'

    print '{0} overrides used'.format(tourney.overrides_used)
