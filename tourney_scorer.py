import argparse
from collections import defaultdict
from decimal import Decimal
import sys

import portfolio_value as pv
import tourney_utils as tourney

ROUND_POINTS = [1, 1, 2, 2, 2, 3]

CALCUTTA_POINTS = map(Decimal, [0.5, 1.25, 2.5, 7.75, 3, 7])
CALCUTTA_POINTS = [Decimal(15.5) * x for x in CALCUTTA_POINTS]

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
        scoring = CALCUTTA_POINTS
    else:
        scoring = ROUND_POINTS

    overrides = tourney.OverridesMap()
    if args.overrides:
        for overrides_file in args.overrides:
            overrides.read_from_file(overrides_file)
    games = tourney.read_games_from_file(args.bracket_file, ratings, overrides)

    if args.operation == 'expected':
        team_scores = tourney.calculate_scores_prob(games, scoring, overrides)

        for team, win_prob in sorted(team_scores.iteritems(), key=sorter):
            print ','.join((team, str(round(win_prob, 3))))
    elif args.operation == 'portfolio_simulate':
        positions = pv.get_positions(API_KEY)
        portfolio_values = []
        for i in xrange(args.simulations):
            scores = tourney.calculate_scores_sim(games, scoring, overrides)
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
