from decimal import Decimal
import json
import sys
import urllib2

API_KEY = 'XXX'
POSITIONS_URL = 'http://caseinsensitive.org/ncaa/entry/{0}/positions?name=full'

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

def get_positions(api_key):
    return json.loads(urllib2.urlopen(POSITIONS_URL.format(api_key)).read())

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

if __name__ == '__main__':
    positions = get_positions(API_KEY)
    with open(sys.argv[1], 'r') as ratings_file:
        values = read_values(ratings_file)

    print get_portfolio_value(positions, values)
