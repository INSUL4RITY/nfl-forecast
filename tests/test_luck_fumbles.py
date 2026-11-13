import polars as pl

from nflcast.predict import luck as LK


def _pbp(rows):
    return pl.DataFrame(rows, orient="row", schema={"game_id": pl.Utf8, "posteam": pl.Utf8, "defteam": pl.Utf8, "fumble": pl.Int32,
                                      "fumble_lost": pl.Float64, "fumbled_1_team": pl.Utf8})


def test_punt_return_fumble_recovered_by_the_punting_team_is_credited_to_it():
    # CHI punts, CAR's returner fumbles, CHI recovers (fumble_lost = 1 from CAR's side)
    s = LK.fumble_share(_pbp([("G", "CHI", "CAR", 1, 1.0, "CAR")]))
    assert s == {"CHI": (1, 1), "CAR": (0, 1)}


def test_offensive_fumble_unchanged_and_returner_keeping_it():
    s = LK.fumble_share(_pbp([("G", "KC", "BUF", 1, 1.0, "KC"),          # KC fumbles, BUF recovers
                              ("G", "GB", "NYJ", 1, 0.0, "NYJ")]))      # GB punts, NYJ fumbles and keeps it
    assert s["KC"] == (0, 1) and s["BUF"] == (1, 1)
    assert s["NYJ"] == (1, 1) and s["GB"] == (0, 1)


def test_missing_fumbler_falls_back_to_the_team_in_possession():
    s = LK.fumble_share(_pbp([("G", "KC", "BUF", 1, 0.0, None)]))
    assert s == {"KC": (1, 1), "BUF": (0, 1)}
