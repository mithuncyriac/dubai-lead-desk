"""Interrupted time series on daily DLD residential sales, 2024-01-01 to 2026-10-20.
log(1 + daily sales) ~ weekday + month-of-year + Ramadan + Eid + [trend | year effects] + post-war step (2026-02-28).
Newey-West (HAC) errors. Also per-segment war effects and a building-fixed price index. Writes data/war_results.json."""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pathlib import Path

H = pd.read_csv("data/dld/hist_sales_2024on.csv", dtype=str)
H["date"] = pd.to_datetime(H.instance_date.str[:10])
H = H[H.date >= "2024-01-01"]
H["value"] = pd.to_numeric(H.actual_worth, errors="coerce")
H["sqm"] = pd.to_numeric(H.procedure_area, errors="coerce")
H["offplan"] = H.reg_type_en.str.contains("Off", case=False, na=False)
H["area"] = np.select([H.master_project_en.eq("Jumeirah Village Circle"),
                       H.master_project_en.eq("Dubai Marina")], ["JVC", "Dubai Marina"], None)
WAR = pd.Timestamp("2026-02-28")
END = H.date.max()

# Islamic holidays (approximate Gregorian dates; UAE observance may differ by a day)
RAMADAN = [("2024-03-11", "2024-04-09"), ("2025-03-01", "2025-03-29"), ("2026-02-18", "2026-03-19")]
EID = [("2024-04-09", "2024-04-12"), ("2024-06-15", "2024-06-18"), ("2025-03-30", "2025-04-01"), ("2025-06-05", "2025-06-08"),
       ("2026-03-19", "2026-03-22"), ("2026-05-26", "2026-05-29"), ("2024-12-02", "2024-12-03"), ("2025-12-02", "2025-12-03")]


def daily(mask=None):
    s = H if mask is None else H[mask]
    d = s.groupby("date").size().reindex(pd.date_range("2024-01-01", END), fill_value=0).rename("n").to_frame()
    d["dow"] = d.index.dayofweek.astype(str)
    d["moy"] = d.index.month.astype(str)
    d["year"] = d.index.year.astype(str)
    d["t"] = (d.index - pd.Timestamp("2024-01-01")).days / 365.25
    d["ramadan"] = 0
    d["eid"] = 0
    for a, b in RAMADAN:
        d.loc[a:b, "ramadan"] = 1
    for a, b in EID:
        d.loc[a:b, "eid"] = 1
    d["war"] = (d.index >= WAR).astype(int)
    d["y"] = np.log1p(d.n)
    return d


SPECS = {"trend": "y ~ C(dow) + C(moy) + ramadan + eid + t + war",
         "year_effects": "y ~ C(dow) + C(moy) + ramadan + eid + C(year) + war"}


def fit(d, spec):
    m = smf.ols(SPECS[spec], data=d).fit(cov_type="HAC", cov_kwds={"maxlags": 14})
    b, lo, hi = m.params["war"], *m.conf_int().loc["war"]
    post = d[d.index >= WAR]
    cf = np.expm1(m.predict(post.assign(war=0))).clip(lower=0).sum()
    return dict(effect_pct=round(100 * np.expm1(b), 1), ci_low_pct=round(100 * np.expm1(lo), 1), ci_high_pct=round(100 * np.expm1(hi), 1),
                actual_post=int(post.n.sum()), counterfactual_post=int(round(cf)), lost_deals=int(round(cf - post.n.sum())),
                r2=round(m.rsquared, 3), n_days=len(d)), m


res = {"window": dict(first=str(H.date.min().date()), last=str(END.date()), rows=len(H)),
       "rows_by_year": {k: int(v) for k, v in H.date.dt.year.value_counts().sort_index().items()}}
d_all = daily()
res["dubai"] = {}
for spec in SPECS:
    r, m = fit(d_all, spec)
    res["dubai"][spec] = r
    if spec == "year_effects":
        post = d_all[d_all.index >= WAR].copy()
        post["cf"] = np.expm1(m.predict(post.assign(war=0))).clip(lower=0)
        mon = post.resample("MS").agg({"n": "sum", "cf": "sum"})
        res["dubai_monthly_cf"] = [dict(month=i.strftime("%Y-%m"), actual=int(r_.n), counterfactual=int(round(r_.cf))) for i, r_ in mon.iterrows()]

# 2026 vs same days of 2025 and 2024 (raw, no model)
def span(a, b):
    return int(((H.date >= a) & (H.date <= b)).sum())
res["yoy_raw"] = dict(
    q3_2026=span("2026-07-01", "2026-09-30"), q3_2025=span("2025-07-01", "2025-09-30"),
    first12_mar_2026=span("2026-03-01", "2026-03-12"), first12_mar_2025=span("2025-03-01", "2025-03-12"),
    feb13_24_2026=span("2026-02-13", "2026-02-24"),
    jan_sep_2026=span("2026-01-01", "2026-09-30"), jan_sep_2025=span("2025-01-01", "2025-09-30"),
    janfeb_2026_per_month=round(span("2026-01-01", "2026-02-28") / 2), marsep_2026_per_month=round(span("2026-03-01", "2026-09-30") / 7),
    q3_value_2026_bn=round(H[(H.date >= "2026-07-01") & (H.date <= "2026-09-30")].value.sum() / 1e9, 1),
    q3_value_2025_bn=round(H[(H.date >= "2025-07-01") & (H.date <= "2025-09-30")].value.sum() / 1e9, 1))

# segments: same model (year effects), one segment at a time
bands = pd.cut(H.value, [0, 1e6, 2e6, 5e6, 1e13], labels=["Under AED 1M", "AED 1–2M", "AED 2–5M", "AED 5M+"])
segs = {f"Price · {b}": bands.eq(b) for b in bands.cat.categories}
segs |= {"Type · Off-plan": H.offplan, "Type · Ready": ~H.offplan, "Area · JVC": H.area.eq("JVC"), "Area · Dubai Marina": H.area.eq("Dubai Marina")}
res["segments"] = []
for name, mask in segs.items():
    r, _ = fit(daily(mask), "year_effects")
    res["segments"].append(dict(segment=name, **{k: r[k] for k in ("effect_pct", "ci_low_pct", "ci_high_pct", "actual_post", "counterfactual_post", "lost_deals")}))

# building-fixed price index (flats, AED per sq ft), Jan 2025 – Oct 2026, Jan 2026 = 100
F = H[(H.property_sub_type_en == "Flat") & (H.sqm > 15) & (H.value > 1e5) & H.area.notna() & (H.date >= "2025-01-01")].copy()
F["psf"] = F.value / (F.sqm * 10.7639)
F = F[(F.psf > 300) & (F.psf < 20000)]
F["bldg"] = F.building_name_en.fillna("").where(F.building_name_en.fillna("") != "", F.project_name_en.fillna("unknown"))
F["month"] = F.date.dt.strftime("%Y-%m")
res["price_index"] = []
for area in ["JVC", "Dubai Marina"]:
    for kind, sub in [("Ready", F[(F.area == area) & ~F.offplan]), ("Off-plan", F[(F.area == area) & F.offplan])]:
        sub = sub[sub.groupby("bldg").bldg.transform("size") >= 5]
        m = smf.ols("np.log(psf) ~ C(month, Treatment('2026-01')) + C(bldg)", data=sub).fit()
        raw = sub.groupby("month").psf.median()
        for mo in sorted(sub.month.unique()):
            key = f"C(month, Treatment('2026-01'))[T.{mo}]"
            res["price_index"].append(dict(area=area, kind=kind, month=mo, n=int((sub.month == mo).sum()),
                                           index=round(100 * np.exp(m.params.get(key, 0.0)), 1),
                                           raw_median_index=round(100 * raw[mo] / raw["2026-01"], 1)))
# post-war (Jul–Oct 2026) medians by area x beds, for the rubric and the premium
RM = {"Studio": 0, "1 B/R": 1, "2 B/R": 2, "3 B/R": 3}
post = F[(F.date >= "2026-07-01")]
res["postwar_medians"] = [dict(area=a, beds=b, n=int(len(g)), median_price=int(g.value.median()), ready_median_psf=round(g[~g.offplan].psf.median()) if (~g.offplan).sum() >= 10 else None)
                          for (a, b), g in post.assign(beds=post.rooms_en.map(RM)).dropna(subset=["beds"]).groupby(["area", "beds"])]
res["postwar_ready_psf"] = {a: round(post[(post.area == a) & ~post.offplan].psf.median()) for a in ["JVC", "Dubai Marina"]}

Path("data/war_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k not in ("price_index", "dubai_monthly_cf")}, indent=1, default=str))

# per-area monthly registered vs expected (for the dashboard's area switch)
res["area_monthly_cf"] = []
for name, mask in [("JVC", H.area.eq("JVC")), ("Dubai Marina", H.area.eq("Dubai Marina"))]:
    d = daily(mask)
    _, m = fit(d, "year_effects")
    post = d[d.index >= WAR].copy()
    post["cf"] = np.expm1(m.predict(post.assign(war=0))).clip(lower=0)
    for i, r_ in post.resample("MS").agg({"n": "sum", "cf": "sum"}).iterrows():
        res["area_monthly_cf"].append(dict(area=name, month=i.strftime("%Y-%m"), actual=int(r_.n), counterfactual=int(round(r_.cf))))
# post-war deal-size mix and mean value, for the what-if panel
post = H[H.date >= WAR].copy()
post["band"] = pd.cut(post.value, [0, 1e6, 2e6, 5e6, 1e13], labels=["Under AED 1M", "AED 1–2M", "AED 2–5M", "AED 5M+"])
res["band_mix"] = []
for name, s in [("All", post), ("JVC", post[post.area == "JVC"]), ("Dubai Marina", post[post.area == "Dubai Marina"])]:
    for b, g in s.groupby("band", observed=True):
        res["band_mix"].append(dict(area=name, band=str(b), sales=len(g), share=round(len(g) / len(s), 4), mean_value=int(g.value.mean())))
Path("data/war_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("area monthly + band mix added")
