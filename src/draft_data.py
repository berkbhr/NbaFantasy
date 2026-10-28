"""Canonical 14-team, 13-round draft used only when live rosters are unavailable.

Yahoo roster snapshots override this historical fallback. Keep names and snake
pick order here; generated reports are never a second source of draft truth.
"""

NUM_TEAMS = 14
NUM_ROUNDS = 13
MY_TEAM_IDX = 7  # Berk's Best Team = slot 8

TEAM_NAMES = [
    "MuCa Tandır",
    "Mordor Tulums",
    "Philadelphia Sikers",
    "Houston Buckets",
    "Kuvâ-yi Milfiye",
    "abu dhabi camels",
    "Samurai Strikers",
    "Berk's Best Team",
    "FatihTerimSpor",
    "Redeem Team",
    "Fikirtepe Warriors",
    "Istanbul Brickmakers",
    "SILE BULLS",
    "YearOne Tyrants",
]

# DRAFT_PICKS_BY_ROUND[round][i] = i-th overall pick of that round (i = 0..13)
DRAFT_PICKS_BY_ROUND = {
    1: [
        "Nikola Jokić",
        "Victor Wembanyama",
        "Luka Dončić",
        "Shai Gilgeous-Alexander",
        "Cade Cunningham",
        "Giannis Antetokounmpo",
        "Jayson Tatum",
        "Tyrese Maxey",
        "Anthony Edwards",
        "Tyrese Haliburton",
        "Cooper Flagg",
        "Jalen Johnson",
        "Donovan Mitchell",
        "Alperen Şengün",
    ],
    2: [
        "Jamal Murray",
        "Scottie Barnes",
        "Kevin Durant",
        "Karl-Anthony Towns",
        "Austin Reaves",
        "Jalen Duren",
        "James Harden",
        "Amen Thompson",
        "LaMelo Ball",
        "Devin Booker",
        "Stephen Curry",
        "Trae Young",
        "Trey Murphy III",
        "Jalen Brunson",
    ],
    3: [
        "Evan Mobley",
        "Chet Holmgren",
        "Lauri Markkanen",
        "Jalen Williams",
        "Walker Kessler",
        "Josh Giddey",
        "Domantas Sabonis",
        "Kawhi Leonard",
        "Keyonte George",
        "Onyeka Okongwu",
        "Bam Adebayo",
        "Kyrie Irving",
        "Derrick White",
        "Matas Buzelis",
    ],
    4: [
        "Brandon Miller",
        "Jaren Jackson Jr.",
        "Anthony Davis",
        "Deni Avdija",
        "Pascal Siakam",
        "Paolo Banchero",
        "Desmond Bane",
        "Donovan Clingan",
        "Franz Wagner",
        "Nickeil Alexander-Walker",
        "Jaylen Brown",
        "Ivica Zubac",
        "Damian Lillard",
        "Cameron Boozer",
    ],
    5: [
        "Kon Knueppel",
        "OG Anunoby",
        "Darius Garland",
        "Nic Claxton",
        "Michael Porter Jr.",
        "Dyson Daniels",
        "LeBron James",
        "Jarrett Allen",
        "Stephon Castle",
        "Mikal Bridges",
        "Dejounte Murray",
        "Ryan Rollins",
        "Payton Pritchard",
        "Kel'el Ware",
    ],
    6: [
        "De'Aaron Fox",
        "Julius Randle",
        "Zach Edey",
        "Jaden McDaniels",
        "Rudy Gobert",
        "Paul George",
        "Jabari Smith Jr.",
        "Tyler Herro",
        "Joel Embiid",
        "Naz Reid",
        "Derik Queen",
        "Immanuel Quickley",
        "Ty Jerome",
        "Caleb Wilson",
    ],
    7: [
        "Norman Powell",
        "John Collins",
        "Alex Sarr",
        "Keegan Murray",
        "Cedric Coward",
        "AJ Dybantsa",
        "Ausar Thompson",
        "Josh Hart",
        "Ja Morant",
        "Zion Williamson",
        "Coby White",
        "Dylan Harper",
        "VJ Edgecombe",
        "Jalen Suggs",
    ],
    8: [
        "Collin Murray-Boyles",
        "Isaiah Hartenstein",
        "Zach LaVine",
        "Myles Turner",
        "Fred VanVleet",
        "Aaron Gordon",
        "Neemias Queta",
        "Day'Ron Sharpe",
        "CJ McCollum",
        "Miles Bridges",
        "Andrew Wiggins",
        "Toumani Camara",
        "Tobias Harris",
        "Cason Wallace",
    ],
    9: [
        "Herbert Jones",
        "Cameron Johnson",
        "Jalen Green",
        "Brook Lopez",
        "Darryn Peterson",
        "Khaman Maluach",
        "Brandin Podziemski",
        "Brandon Ingram",
        "RJ Barrett",
        "Kevin Porter Jr.",
        "Yaxel Lendeborg",
        "Darius Acuff Jr.",
        "Collin Gillespie",
        "Jaime Jaquez Jr.",
    ],
    10: [
        "Christian Braun",
        "Kyshawn George",
        "Rui Hachimura",
        "Egor Dëmin",
        "Devin Vassell",
        "Quentin Grimes",
        "Ayo Dosunmu",
        "Andrew Nembhard",
        "Ajay Mitchell",
        "Gui Santos",
        "Tim Hardaway Jr.",
        "Jakob Poeltl",
        "Peyton Watson",
        "Sandro Mamukelashvili",
    ],
    11: [
        "Alex Caruso",
        "Mitchell Robinson",
        "Jonathan Kuminga",
        "DeMar DeRozan",
        "Ace Bailey",
        "Daniel Gafford",
        "Reed Sheppard",
        "Nikola Vučević",
        "Dillon Brooks",
        "Wendell Carter Jr.",
        "Saddiq Bey",
        "Yves Missi",
        "P.J. Washington",
        "Davion Mitchell",
    ],
    12: [
        "Tari Eason",
        "Jimmy Butler III",
        "Jaylen Wells",
        "Isaiah Jackson",
        "Draymond Green",
        "Bobby Portis Jr.",
        "Julian Champagnie",
        "Grayson Allen",
        "Aaron Nesmith",
        "Mikel Brown Jr.",
        "Jrue Holiday",
        "Jerami Grant",
        "Robert Williams III",
        "Scotty Pippen Jr.",
    ],
    13: [
        "Kelly Oubre Jr.",
        "Sam Hauser",
        "Bennedict Mathurin",
        "Tre Jones",
        "Moussa Diabaté",
        "Anthony Black",
        "Jeremiah Fears",
        "Jay Huff",
        "Deandre Ayton",
        "Ben Simmons",
        "Zaccharie Risacher",
        "Jake LaRavia",
        "Pelle Larsson",
        "Scoot Henderson",
    ],
}


class DraftResolutionError(RuntimeError):
    """Raised when draft names cannot be mapped 1:1 onto model players."""


def slot_of_pick(round_no, pick_idx, num_teams=NUM_TEAMS):
    """0-based team slot for the pick_idx-th pick of a round (snake draft)."""
    return pick_idx if (round_no % 2 == 1) else (num_teams - 1 - pick_idx)


def all_pick_names(picks_by_round=None):
    picks_by_round = picks_by_round or DRAFT_PICKS_BY_ROUND
    return [n for r in range(1, NUM_ROUNDS + 1) for n in picks_by_round[r]]


def build_rosters(picks_by_round=None, num_teams=NUM_TEAMS):
    """{slot_idx: [player names]} via snake assignment."""
    picks_by_round = picks_by_round or DRAFT_PICKS_BY_ROUND
    rosters = {i: [] for i in range(num_teams)}
    for r in range(1, NUM_ROUNDS + 1):
        for i, name in enumerate(picks_by_round[r]):
            rosters[slot_of_pick(r, i, num_teams)].append(name)
    return rosters


def resolve_rosters(assistant, rosters=None):
    """
    Map every drafted name to a model player id. NEVER silent: raises DraftResolutionError
    listing unresolved names and ids that were resolved for more than one pick.
    """
    rosters = rosters or build_rosters()
    out, unresolved, seen, duplicates = {}, [], {}, []
    for slot, names in rosters.items():
        out[slot] = []
        for name in names:
            pid = assistant.resolve_player_id(name, only_available=False)
            if pid is None or pid not in assistant.players:
                unresolved.append((slot + 1, name))
                continue
            if pid in seen:
                duplicates.append((name, seen[pid]))
            seen[pid] = name
            out[slot].append(pid)
    if unresolved or duplicates:
        raise DraftResolutionError(
            f"unresolved (slot, name): {unresolved}; resolved to an already-used id (name, first name): {duplicates}"
        )
    return out
