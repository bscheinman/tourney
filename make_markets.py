import argparse
import cix_client
from decimal import Decimal, ROUND_UP, ROUND_DOWN
import os

import portfolio_value as pv
import tourney_utils as tourney

APID = os.environ['CIX_APID']

# determine portfolio delta for each team
# determine pairwise deltas (foreach pair of teams, how does X's performance impact Y?)

# use this to determine how much risk any additional trade would expose (across all teams in portfolio)

def get_positions():
    return client.my_positions()
    return {
        'Virginia': 1000,
        'St. Bonaventure': 1000,
        'Houston': -1000
    }

def get_spread(team, values, portfolio, base_margin=Decimal('0.05')):
    team_ev = values[team]
    base_bid = team_ev * (1 - base_margin)
    base_ask = team_ev * (1 + base_margin)

    bid = base_bid.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    ask = base_ask.quantize(Decimal('0.01'), rounding=ROUND_UP)

    return bid, ask


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bracket_file')
    parser.add_argument('ratings_file')
    parser.add_argument('teams', nargs='*', default=None)
    parser.add_argument('--overrides', action='append')
    parser.add_argument('--adjustments', action='store')
    parser.add_argument('--point_delta', action='store', default='1.0')
    parser.add_argument('--save_deltas', action='store')
    parser.add_argument('--load_deltas', action='store')
    parser.add_argument('--spread_margin', action='store', default='0.05')
    parser.add_argument('--order_size', action='store', type=int, default=5000)
    parser.add_argument('-d', '--dry_run', action='store_true')
    parser.add_argument('--no_prompt', action='store_true')
    args = parser.parse_args()

    if args.adjustments:
        with open(args.adjustments, 'r') as adjustments_file:
            adjustments = tourney.read_adjustments_file(adjustments_file)
    else:
        adjustments = {}

    with open(args.ratings_file, 'r') as ratings_file:
        ratings = tourney.read_ratings_file(ratings_file, adjustments)

    overrides = tourney.OverridesMap()
    if args.overrides:
        for override_file in args.overrides:
            overrides.read_from_file(override_file)
    bracket = tourney.read_games_from_file(args.bracket_file, ratings, overrides)

    client = cix_client.CixClient(APID)

    positions = client.my_positions()
    point_delta = Decimal(args.point_delta)

    tourney_state = tourney.TournamentState(bracket=bracket, ratings=ratings,
            overrides=overrides, scoring=tourney.ROUND_POINTS)

    values = tourney_state.calculate_scores_prob()

    portfolio = pv.PortfolioState(tourney_state, positions,
            point_delta=Decimal(args.point_delta))

    if args.load_deltas:
        portfolio.load_deltas(args.load_deltas)
    else:
        portfolio.compute_deltas(args.teams)

    if args.save_deltas:
        portfolio.store_deltas(args.save_deltas)

    if args.teams:
        market_teams = args.teams
    else:
        market_teams = tourney.get_bracket_teams(bracket)

    for team in market_teams:
        bid, ask = get_spread(team, values, portfolio,
                base_margin=Decimal(args.spread_margin))
        print '{team} market: {bid} - {ask} (value = {value})'.format(
                team=team, bid=bid, ask=ask, value=values[team].quantize(Decimal('0.001')))
        if not args.dry_run:
            if args.no_prompt:
                do_order = True
            else:
                print 'place orders?'
                answer = raw_input()
                do_order = answer[0].lower() == 'y'
            if do_order:
                try:
                    client.make_market(team, bid=bid, bid_size=args.order_size,
                            ask=ask, ask_size=args.order_size)
                except cix_client.ApiException as ex:
                    print 'failed to make market: {}'.format(', '.join(ex.errors))
