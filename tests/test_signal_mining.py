"""Tests for the PRR / ROR arithmetic in analytics/signal_mining.py (no database needed)."""
from analytics.signal_mining import disproportionality, is_signal


def test_prr_and_ror_match_the_2x2_table():
    # 1000 reports; drug in 50, reaction in 40, both in 10  ->  b=40, c=30, d=920
    prr, ror, chi2 = disproportionality(10, 50, 40, 1000)
    assert prr == round((10 / 50) / (30 / 950), 3)
    assert ror == round((10 * 920) / (40 * 30), 3)
    assert chi2 > 4 and is_signal(10, (prr, ror, chi2))


def test_weak_or_undefined_pairs_are_not_signals():
    assert disproportionality(0, 50, 40, 1000) is None      # no co-reports
    assert disproportionality(5, 5, 40, 1000) is None       # b = 0: ROR undefined
    stats = disproportionality(2, 50, 40, 1000)             # only 2 reports
    assert not is_signal(2, stats)
