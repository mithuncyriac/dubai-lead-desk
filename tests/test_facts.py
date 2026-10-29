"""Fails if a headline number moves, or if the numbers stop agreeing with each other.
Run after `python run_all.py` (CI does both)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = json.loads((ROOT / "site" / "facts.json").read_text(encoding="utf-8"))
LOCK = json.loads((ROOT / "tests" / "locked_headlines.json").read_text(encoding="utf-8"))
CHARTS = json.loads((ROOT / "site" / "chart_data.json").read_text(encoding="utf-8"))


def test_headlines_unchanged():
    got = {k: FACTS["forecast"][k] if k.startswith("forecast_") else FACTS[k] for k in LOCK}
    changed = {k: (LOCK[k], got[k]) for k in LOCK if got[k] != LOCK[k]}
    assert not changed, f"headline numbers moved (locked, now): {changed}. If this is a deliberate data refresh, update tests/locked_headlines.json"


def test_sales_add_up():
    assert FACTS["sales_actual_post"] + FACTS["sales_missing_post"] == FACTS["sales_expected_post"]


def test_gap_inside_its_range():
    assert FACTS["war_gap_low_pct"] < FACTS["war_gap_pct"] < FACTS["war_gap_high_pct"] < 0


def test_cheaper_homes_fell_least():
    bands = [b["gap"] for b in CHARTS["bands"]]
    assert bands == sorted(bands, reverse=True), "the gap should grow with price band"
    assert FACTS["band_under1m_pct"] == bands[0] and FACTS["band_over5m_pct"] == bands[-1]


def test_monthly_matches_total():
    m = [r for r in CHARTS["monthly"] if r["area"] == "All"]
    assert sum(r["actual"] for r in m) == FACTS["sales_actual_post"]
    assert abs(sum(r["expected"] for r in m) - FACTS["sales_expected_post"]) <= len(m)   # rounding per month


def test_forecast_is_sane():
    f = FACTS["forecast"]
    assert f["forecast_low"] < f["forecast_mid"] < f["forecast_high"] < f["expected_without_war"]
    assert f["check_on"] > FACTS["data_to"]


def test_data_date_is_stamped():
    assert FACTS["data_to_label"] and FACTS["data_to"] <= FACTS["built"]
