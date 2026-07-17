import pytest

from one_more_run.akash_adapter import BASELINE, CoordinateSearch


def baseline(search: CoordinateSearch, metric: float = 1.0) -> None:
    hypothesis, candidate = search.propose()
    assert hypothesis == "establish the baseline"
    assert candidate == BASELINE
    assert search.observe(metric)


def test_search_advances_from_the_measured_champion():
    search = CoordinateSearch()
    baseline(search)

    _, learning_rate = search.propose()
    assert learning_rate == {"learning_rate": 0.05, "momentum": 0.0, "steps": 80}
    assert search.observe(0.9)

    hypothesis, momentum = search.propose()
    assert "learning_rate improved" in hypothesis
    assert momentum == {"learning_rate": 0.05, "momentum": 0.4, "steps": 80}


def test_search_reverses_a_regressing_coordinate():
    search = CoordinateSearch()
    baseline(search)

    search.propose()
    assert not search.observe(1.1)

    hypothesis, candidate = search.propose()
    assert "regressed" in hypothesis
    assert candidate["learning_rate"] == pytest.approx(0.00001)
    assert candidate["momentum"] == 0.0


def test_search_skips_a_reverse_move_at_the_boundary():
    search = CoordinateSearch()
    baseline(search)

    search.propose()
    search.observe(0.9)
    search.propose()
    search.observe(1.1)

    hypothesis, candidate = search.propose()
    assert "boundary" in hypothesis
    assert candidate == {"learning_rate": 0.05, "momentum": 0.0, "steps": 120}


def test_search_can_maximize():
    search = CoordinateSearch(maximize=True)
    baseline(search)

    search.propose()
    assert search.observe(1.1)


def test_search_rejects_a_nonfinite_measurement():
    search = CoordinateSearch()
    search.propose()

    with pytest.raises(ValueError, match="finite"):
        search.observe(float("nan"))
