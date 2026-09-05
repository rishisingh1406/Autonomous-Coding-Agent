from app.stats import average


def test_average_returns_mean():
    assert average([2, 4, 6]) == 4


def test_average_handles_single_value():
    assert average([5]) == 5
