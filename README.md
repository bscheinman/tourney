tourney
=======

Miscellaneous Scripts Related to the NCAA Tournament

tourney\_scorer.py: Calculate expected scores for [casei](http://caseinsensitive.org) games
------------------

Usage:

    ./tourney_scorer.py bracket.txt [--overrides overrides.txt]

bracket.txt is a text file with a line for each team in the tournament consisting of 2 comma-separated fields.  The first field should be a string representing the team name and the second should be the [pythagorean expectation](http://en.wikipedia.org/wiki/Pythagorean_expectation) of that team.  For play-in games, include two such pairs separated by a comma.  The teams (or play-in pairs) should be listed in an order representing the bracket (as if it were flattened out instead of being split into two sides).

The output will be a text file with one line for each team.  Each line will be a comma-separated pair where the first field is the team name and the second field is the expected point total for that team (rounded to 3 decimal places).

You can optionally provide a file of manual overrides for specific matchups.  This file is a text file in which each line should be a comma-separated tuple of three fields.  The first two fields should be the string used to represent the teams involved in the matchup and the third field is the probability of the first team winning that matchup.

