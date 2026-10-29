"""November 2026 forecast from the existing year-effects war model, written down before the data exists.

Expected November sales without the war come from the same model (weekday, month, year, no Ramadan/Eid in November).
Two readings of the war gap give the range:
  upper  the model's average gap over the whole post-war period
  lower  the gap in the latest full months (1 Sep - data end), which has been wider
Writes data/forecast.json. Check against DLD's November registrations once they are published (early December).
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pathlib import Path


H = pd.read_csv("data/dld/hist_sales_2024on.csv", dtype=str, usecols=["instance_date"])
H["date"] = pd.to_datetime(H.instance_date.str[:10])
H = H[H.date >= "2024-01-01"]
END = H.date.max()
WAR = pd.Timestamp("2026-02-28")
RAMADAN = [("2024-03-11", "2024-04-09"), ("2025-03-01", "2025-03-29"), ("2026-02-18", "2026-03-19")]
EID = [("2024-04-09", "2024-04-12"), ("2024-06-15", "2024-06-18"), ("2025-03-30", "2025-04-01"), ("2025-06-05", "2025-06-08"),
       ("2026-03-19", "2026-03-22"), ("2026-05-26", "2026-05-29"), ("2024-12-02", "2024-12-03"), ("2025-12-02", "2025-12-03")]


def frame(idx, n=None):
    d = pd.DataFrame(index=idx)
    d["n"] = 0 if n is None else n
    d["dow"] = d.index.dayofweek.astype(str)
    d["moy"] = d.index.month.astype(str)
    d["year"] = d.index.year.astype(str)
    d["ramadan"] = 0
    d["eid"] = 0
    for a, b in RAMADAN:
        d.loc[a:b, "ramadan"] = 1
    for a, b in EID:
        d.loc[a:b, "eid"] = 1
    d["war"] = (d.index >= WAR).astype(int)
    d["y"] = np.log1p(d.n)
    return d


# same specification as war_attribution.py (year effects), refitted here so this file stands alone
counts = H.groupby("date").size().reindex(pd.date_range("2024-01-01", END), fill_value=0)
d = frame(counts.index, counts.values)
m = smf.ols("y ~ C(dow) + C(moy) + ramadan + eid + C(year) + war", data=d).fit(cov_type="HAC", cov_kwds={"maxlags": 14})

nov = frame(pd.date_range("2026-11-01", "2026-11-30"))
expected = float(np.expm1(m.predict(nov.assign(war=0))).clip(lower=0).sum())

whole_gap = float(np.expm1(m.params["war"]))                       # e.g. -0.366
recent = d[d.index >= "2026-09-01"]
recent_cf = float(np.expm1(m.predict(recent.assign(war=0))).clip(lower=0).sum())
recent_gap = float(recent.n.sum() / recent_cf - 1)                 # e.g. -0.466

res = dict(month="2026-11", expected_without_war=round(expected),
           whole_period_gap_pct=round(100 * whole_gap, 1), recent_gap_pct=round(100 * recent_gap, 1),
           recent_window=f"2026-09-01 to {END.date()}",
           forecast_low=int(round(expected * (1 + min(whole_gap, recent_gap)), -2)),
           forecast_high=int(round(expected * (1 + max(whole_gap, recent_gap)), -2)),
           check_on="2026-12-07", recheck_on="2027-01-07",
           rule="Right if DLD's November 2026 residential sales land between forecast_low and forecast_high. First check on check_on; checked again on recheck_on because DLD can still add late registrations.")
res["forecast_mid"] = int(round((res["forecast_low"] + res["forecast_high"]) / 2, -2))
Path("data/forecast.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
