#!python
#!/usr/bin/python

import argparse
from decimal import Decimal
import json
from math import sqrt
import os
import re
import sys
import requests
import urllib3

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

RATINGS_URL = "http://kenpom.com/"
BRACKET_URL = "http://espn.go.com/ncb/bracketology"
GAMEPREDICT_URL = (
    "http://gamepredict.us/teams/matchup_table?team_a={0}&team_b={1}&neutral=true"
)
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds?apiKey={}&regions=us&oddsFormat=decimal".format(
    ODDS_API_KEY
)
CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"

NAME_CONVERSIONS = {
    "Miami": "Miami FL",
    "Southern Cal": "USC",
    "St. Mary's (ca)": "Saint Mary's",
    "Virginia Commonwealth": "VCU",
    "Miami (fl)": "Miami FL",
    "Middle Tennessee St.": "Middle Tennessee",
    "Se Louisiana": "Southeastern Louisiana",
    "Arkansas-pine Bluff": "Arkansas Pine Bluff",
    "Louisiana": "Louisiana Lafayette",
    "Charleston": "College of Charleston",
    "Nc St.": "North Carolina St.",
    "Texas A&m;": "Texas A&M;",
    "Loyola-chicago": "Loyola Chicago",
    "Cs Fullerton": "Cal St. Fullerton",
    "Csu Fullerton": "Cal St. Fullerton",
    "Suny-buffalo": "Buffalo",
    "Md-baltimore County": "UMBC",
    "Texas Am": "Texas A&M;",
    "Pennsylvania": "Penn",
    "College Of Charleston": "College of Charleston",
    "Texas Christian": "TCU",
    "Ole Miss": "Mississippi",
    "Gardner-webb": "Gardner Webb",
    "Texas So.": "Texas Southern",
    "UCSB": "UC Santa Barbara",
    "E. Washington": "Eastern Washington",
    "Uconn": "Connecticut",
    "Uncg": "UNC Greensboro",
    "Louisiana St.": "LSU",
    "Texas A&m-cc": "Texas A&M Corpus Chris",
    "Loyola (chi)": "Loyola Chicago",
    "Se Missourist.": "Southeast Missouri St.",
    "Fdu": "Fairleigh Dickinson",
    "Tamu-cc": "Texas A&M Corpus Chris",
    "North Carolina St.": "N.C. State",
    "College of Charleston": "Charleston",
    "Louisiana Lafayette": "Louisiana",
    "Fla. Atlantic": "Florida Atlantic",
    "No. Kentucky": "Northern Kentucky",
}

WORD_ABBREVS = set(
    [
        "Unc",
        "Ucla",
        "Smu",
        "Vcu",
        "Uc",
        "Tcu",
        "Liu",
        "Usc",
        "A&m",
        "A&m;",
        "Lsu",
        "Ucf",
        "Ucsb",
        "Byu",
        "Uab",
    ]
)

WORD_CONVERSIONS = {
    "State": "St.",
    "St": "St.",
    "Marys": "Mary's",
}


def clean_name(s):
    s = s.replace("aq - ", "").replace(" - aq", "")
    words = s.split()
    for i in range(len(words)):
        word = words[i].lower()
        word = word[0].upper() + word[1:].lower()
        if word in WORD_ABBREVS:
            word = word.upper()
        word = WORD_CONVERSIONS.get(word, word)
        words[i] = word
    cleaned = " ".join(words)
    return NAME_CONVERSIONS.get(cleaned, cleaned)


def clean_api_name(s):
    words = s.split()

    # remove at least one word of team name
    words = words[:-1]

    if words[-1] in (
        "Blue",
        "Tar",
        "Red",
        "Fighting",
        "Scarlet",
        "Horned",
        "Golden",
        "Crimson",
    ):
        words = words[:-1]

    return clean_name(" ".join(words))


def get_bracket(out_file):
    html = requests.get(BRACKET_URL).text
    soup = BeautifulSoup(html, "html.parser")
    bracket = soup.find("div", {"class": "bracket__region"})
    for entry in bracket.find_all("a", {"class": "bracket__link"}):
        team_names = [clean_name(name) for name in entry.text.split("/")]
        out_file.write("{0}\n".format(",".join(team_names)))


def get_ratings(out_file):
    headers = {"User-Agent": CHROME_UA}
    html = requests.get(RATINGS_URL, headers=headers).text
    soup = BeautifulSoup(html, "html.parser")
    ratings = soup.find("table", {"id": "ratings-table"})
    ratings = ratings.tbody
    for row in ratings.find_all("tr"):
        columns = row.find_all("td")
        data_columns = row.find_all("td", {"class": "td-left"})
        if not columns or not data_columns or len(data_columns) < 3:
            continue
        team_name = columns[1].a.string
        offense = data_columns[0].string
        defense = data_columns[1].string
        tempo = data_columns[2].string
        out_file.write("{0}\n".format("|".join((team_name, offense, defense, tempo))))


def get_pairwise_prob(a, b):
    html = requests.get(
        GAMEPREDICT_URL.format(urllib3.quote(a), urllib3.quote(b))
    ).read()
    soup = BeautifulSoup(html, "html.parser")
    cols = soup.find_all("div", {"class": "col-xs-6"})
    perc_str = cols[2].find_all("p")[0].string.strip()
    return int(perc_str[:-1]) / 100.0


# Start with the lazy approach of scraping all probs from gamepredict
def get_pairwise_probs(teams, out_file):
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            try:
                prob = get_pairwise_prob(teams[i], teams[j])
                out_file.write(
                    "{0}\n".format(",".join((teams[i], teams[j], str(prob))))
                )
            except:
                sys.stderr.write(
                    "prob failed for teams {0}, {1}\n".format(teams[i], teams[j])
                )
                raise


ODDS_REGEX = re.compile("[-+][1-9][0-9]{2,}")


def extract_odds(cell_str):
    return ODDS_REGEX.findall(cell_str)


def convert_american_odds(odds_str):
    num_comp = int(odds_str[1:])
    if odds_str[0] == "-":
        return num_comp / (100.0 + num_comp)
    elif odds_str[0] == "+":
        return 100.0 / (100.0 + num_comp)
    else:
        assert False


def get_odds():
    raw_odds = json.loads(requests.get(ODDS_API_URL).text)
    all_odds = {}

    for game in raw_odds:
        away_team = game["away_team"]
        home_team = game["home_team"]

        away_odds = []
        home_odds = []

        for book in game["bookmakers"]:
            line = book["markets"][0]["outcomes"]
            for side in line:
                if side["name"] == away_team:
                    away_odds.append(Decimal(side["price"]))
                elif side["name"] == home_team:
                    home_odds.append(Decimal(side["price"]))
                else:
                    assert False

        if len(away_odds) == 0 or len(home_odds) == 0:
            continue

        away_price = sum(away_odds) / len(away_odds)
        home_price = sum(home_odds) / len(home_odds)

        away_win_prob = Decimal(1.0) / away_price
        home_win_prob = Decimal(1.0) / home_price

        mixed_win_prob = sqrt(float(away_win_prob * (Decimal(1.0) - home_win_prob)))

        all_odds[
            (clean_api_name(away_team), clean_api_name(home_team))
        ] = mixed_win_prob

    return all_odds


def read_team_names(bracket_file):
    names = []
    for line in bracket_file:
        if line.strip():
            names += line.strip().split(",")
    return names


def get_previous_odds():
    odds = {}

    try:
        with open("odds.txt", "r") as odds_file:
            for line in odds_file:
                fields = line.strip().split(",")
                assert len(fields) == 3

                odds[tuple(fields[:2])] = float(fields[2])

    except FileNotFoundError:
        pass

    return odds


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_type", choices=["bracket", "ratings", "probs", "odds"])
    args = parser.parse_args()

    if args.data_type == "bracket":
        with open("bracket.txt", "w") as bracket_file:
            get_bracket(bracket_file)
    elif args.data_type == "ratings":
        with open("ratings.txt", "w") as ratings_file:
            get_ratings(ratings_file)
    elif args.data_type == "probs":
        with open("bracket.txt", "r") as bracket_file:
            all_teams = read_team_names(bracket_file)
        with open("probs.txt", "w") as probs_file:
            get_pairwise_probs(all_teams, probs_file)
    elif args.data_type == "odds":
        old_odds = get_previous_odds()
        new_odds = get_odds()

        with open("odds.txt", "w") as overrides_file:
            for teams, win_prob in new_odds.items():
                win_prob = round(win_prob, 3)

                overrides_file.write(
                    "{}\n".format(",".join((teams[0], teams[1], str(win_prob))))
                )

                old_win_prob = old_odds.get(teams, None)
                if old_win_prob != win_prob:
                    print(
                        "{0}-{1} {2} (was {3})".format(
                            teams[0], teams[1], win_prob, old_win_prob
                        )
                    )
    else:
        print("unrecognized data type {}".format(args.data_type))
