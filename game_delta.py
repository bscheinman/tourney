import argparse
import cix_client
import os

import portfolio_value as pv
import tourney_utils as tourney

def bracket_games(bracket, overrides):
    games = list(bracket)
    while games:
        new_games = []
        for i in xrange(len(games) / 2):
            team1, team2 = tuple(games[i*2 : (i+1)*2])
            prob = overrides.get_override(team1, team2)
            if prob >= Decimal(1):
                new_games.append(team1)
            elif prob == Decimal(0):
                new_games.append(team2)
            else:
                yield team1, team2
        games = new_games

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bracket_file')
    parser.add_argument('ratings_file')
    parser.add_argument('team1')
    parser.add_argument('team2')
    parser.add_argument('--overrides', action='append')
    parser.add_argument('--adjustments', action='store')
    parser.add_argument('--sort', action='store', default='name')
    parser.add_argument('--calcutta', action='store_true')
    args = parser.parse_args()

    if args.adjustments:
        with open(args.adjustments, 'r') as adjustments_file:
            adjustments = tourney.read_adjustments_file(adjustments_file)
    else:
        adjustments = {}

    with open(args.ratings_file, 'r') as ratings_file:
        ratings = tourney.read_ratings_file(ratings_file, adjustments)

    if args.calcutta:
        scoring = tourney.CALCUTTA_POINTS
    else:
        scoring = tourney.ROUND_POINTS

    overrides = tourney.OverridesMap()
    if args.overrides:
        for override_file in args.overrides:
            overrides.read_from_file(override_file)
    bracket = tourney.read_games_from_file(args.bracket_file, ratings, overrides)

    APID = os.environ['CIX_APID']
    client = cix_client.CixClient(APID)
    positions = client.my_positions(full_names=True)

    tournament = tourney.TournamentState(bracket=bracket, ratings=ratings,
            overrides=overrides, scoring=scoring)

    win_value, loss_value = pv.game_delta(positions, tournament, args.team1,
            args.team2)

    print 'If {0} wins: {1:.2f}'.format(args.team1, win_value)
    print 'If {0} wins: {1:.2f}'.format(args.team2, loss_value)
    print 'Delta: {0:.2f}'.format(win_value - loss_value)
