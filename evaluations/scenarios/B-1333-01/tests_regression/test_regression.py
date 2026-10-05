"""Point parsing tests from geopy's own test suite (test/test_point.py), plus one long valid input."""
import pytest

from geopy.point import Point

LAT, LON = 40.74113, -73.989656


@pytest.mark.parametrize("template", ["%s,%s", "%s %s", "%s;%s"])
def test_point_str_simple(template):
    point = Point(template % (LAT, LON))
    assert (point.latitude, point.longitude, point.altitude) == (LAT, LON, 0)


def test_point_str_deg():
    point = Point("UT: N 39\xb020' 0'' / W 74\xb035' 0''")
    assert (point.latitude, point.longitude, point.altitude) == (39.333333333333336, -74.58333333333333, 0)


def test_point_format_round_trip():
    assert Point("51 19m 12.9s N, 0 1m 24.95s E").format() == "51 19m 12.9s N, 0 1m 24.95s E"
    assert Point("51 19m 12.9s N, -1 1m 24.95s E, 15000m").format() == "51 19m 12.9s N, 1 1m 24.95s W, 15.0km"


def test_strings_that_are_not_points_raise():
    for text in ("gibberish", "75 5th Avenue, NYC, USA", "41.5 -81.0 aaa", ""):
        with pytest.raises(ValueError):
            Point.from_string(text)


def test_point_from_string_docstring_examples():
    assert Point("41.5;-81.0") == (41.5, -81.0, 0.0)
    assert Point("41.5,-81.0") == (41.5, -81.0, 0.0)
    assert Point("41.5 -81.0") == (41.5, -81.0, 0.0)
    assert Point("+41.5 -81.0") == (41.5, -81.0, 0.0)
    assert Point("+41.5 +81.0") == (41.5, 81.0, 0.0)
    assert Point("41.5 N -81.0 W") == (41.5, 81.0, 0.0)
    assert Point("-41.5 S;81.0 E") == (41.5, 81.0, 0.0)
    assert Point("23 26m 22s N 23 27m 30s E") == (23.439444444444444, 23.458333333333332, 0.0)
    assert Point("23 26' 22\" N 23 27' 30\" E") == (23.439444444444444, 23.458333333333332, 0.0)


def test_point_from_string_tolerates_irrelevant_surroundings():
    assert Point("aaa 41.5 -81.0") == (41.5, -81.0, 0.0)
    assert Point("  41.5 -81.0  ") == (41.5, -81.0, 0.0)


def test_coordinates_after_a_sentence_of_leading_text_still_parse():
    text = "Summit cairn as surveyed by the club in August 2019: 23 26m 22s N 23 27m 30s E"
    assert Point(text) == (23.439444444444444, 23.458333333333332, 0.0)


def test_other_ways_to_build_a_point_are_unaffected():
    assert tuple(Point(1, 2, 3)) == tuple(Point([1, 2, 3])) == (1.0, 2.0, 3.0)
    assert tuple(Point(Point(LAT, LON, 3))) == (LAT, LON, 3)
    assert Point(latitude=41.5, longitude=81.0, altitude=2.5).format_decimal() == "41.5, 81.0, 2.5km"
