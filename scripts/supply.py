"""New supply (DLD Projects, start date in 2026), supply cover, and the valuation gap (DLD valuations vs sale prices).
Writes dash_data/launches.csv, supply_cover.csv, valuation_gap.csv and adds headline rows."""
import csv, json
import pandas as pd
from pathlib import Path

D, OUT = Path("data/dld"), Path("dash_data")
WAR = pd.Timestamp("2026-02-28")
AREAS = {"JVC": "Al Barsha South Fourth", "Dubai Marina": "Marsa Dubai"}

p = pd.read_csv(D / "projects.csv", encoding="utf-8-sig", dtype=str)
p = p[p.PROJECT_STATUS != "CANCELLED"]
p["units"] = pd.to_numeric(p.CNT_UNIT, errors="coerce").fillna(0)
p["start"] = pd.to_datetime(p.START_DATE, errors="coerce")
p["end"] = pd.to_datetime(p.END_DATE, errors="coerce")
p["month"] = p.start.dt.strftime("%Y-%m")

launch = p.groupby("month").agg(projects=("units", "size"), units=("units", "sum")).reset_index()
for k, a in AREAS.items():
    launch[k.lower().replace(" ", "_") + "_units"] = launch.month.map(p[p.AREA_EN == a].groupby("month").units.sum()).fillna(0)
launch = launch.astype({c: int for c in launch.columns if c != "month"})
launch.to_csv(OUT / "launches.csv", index=False)

# post-war absorption: registered sales per month in each area since 28 Feb (from the war model's segment run)
W = json.loads(Path("data/war_results.json").read_text(encoding="utf-8"))
months_post = (pd.Timestamp(W["window"]["last"]) - WAR).days / 30.44
seg = {s["segment"]: s for s in W["segments"]}
listings = {"JVC": 9436, "Dubai Marina": 3422}   # live Bayut listings, 21 Oct 2026
cover = []
for k, a in AREAS.items():
    s = p[p.AREA_EN == a]
    per_month = seg[f"Area · {k}"]["actual_post"] / months_post
    due = s.groupby(s.end.dt.year).units.sum()
    cover.append(dict(area=k, launched_2026_units=int(s.units.sum()), launched_after_war_units=int(s[s.start >= WAR].units.sum()),
                      projects=len(s), due_2027=int(due.get(2027, 0)), due_2028=int(due.get(2028, 0)), due_2029_on=int(due[due.index >= 2029].sum()),
                      sales_per_month_postwar=round(per_month), months_from_listings=round(listings[k] / per_month, 1),
                      months_from_2026_launches=round(s.units.sum() / per_month, 1)))
pipe = {r["area"]: r for r in csv.DictReader(open(OUT / "pipeline.csv", encoding="utf-8"))}   # from stale_offplan.py
for c_ in cover:
    c_["units_awaiting_handover"] = int(pipe[c_["area"]]["units_sold_offplan_awaiting_handover"])
    c_["months_from_pipeline"] = float(pipe[c_["area"]]["months_from_pipeline"])
pd.DataFrame(cover).to_csv(OUT / "supply_cover.csv", index=False)

# valuation gap: DLD valuations of flats vs ready-flat sale prices, same periods (2026 file)
v = pd.read_csv(D / "valuations.csv", encoding="utf-8-sig", dtype=str)
v = v[v.AREA_EN.isin(AREAS.values()) & v.PROP_SUB_TYPE_EN.isin(["Flat", "Residential Flats"])].copy()
v["psf"] = pd.to_numeric(v.ACTUAL_WORTH, errors="coerce") / (pd.to_numeric(v.ACTUAL_AREA, errors="coerce") * 10.7639)
v["date"] = pd.to_datetime(v.INSTANCE_DATE)
t = pd.read_csv(D / "transactions.csv", encoding="utf-8-sig", dtype=str)
t = t[(t.PROP_SB_TYPE_EN == "Flat") & (t.IS_OFFPLAN_EN == "Ready")].copy()
t["date"] = pd.to_datetime(t.INSTANCE_DATE)
t["psf"] = pd.to_numeric(t.TRANS_VALUE, errors="coerce") / (pd.to_numeric(t.ACTUAL_AREA, errors="coerce") * 10.7639)
t = t[(t.psf > 300) & (t.psf < 20000)]
TX = {"JVC": ["JUMEIRAH VILLAGE CIRCLE"], "Dubai Marina": ["DUBAI MARINA", "Marsa Dubai"]}
PER = [("Jan–Feb (pre-war)", "2026-01-01", "2026-02-28"), ("Mar–Jun", "2026-02-28", "2026-07-01"), ("Jul–Oct", "2026-07-01", "2026-10-22")]
gap = []
for k, a in AREAS.items():
    for name, lo, hi in PER:
        vv = v[(v.AREA_EN == a) & (v.date >= lo) & (v.date < hi)]
        tt = t[t.AREA_EN.isin(TX[k]) & (t.date >= lo) & (t.date < hi)]
        gap.append(dict(key=f"{k}|{name}", area=k, period=name, valuations=len(vv), valuation_psf=round(vv.psf.median()),
                        sales=len(tt), sale_psf=round(tt.psf.median()), gap_pct=round(100 * (vv.psf.median() / tt.psf.median() - 1), 1)))
pd.DataFrame(gap).to_csv(OUT / "valuation_gap.csv", index=False)

# headline rows
c = {r["area"]: r for r in cover}
g = {r["key"]: r for r in gap}
pre = p[p.start < WAR]
post = p[p.start >= WAR]
with open(OUT / "headline.csv", "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["launched_after_war_units", int(post.units.sum()), f"units in projects started 28 Feb – 21 Oct 2026 across Dubai, vs {int(pre.units.sum()):,} in Jan–Feb (DLD Projects)"])
    w.writerow(["jvc_launch_months", c["JVC"]["months_from_2026_launches"], f"months of post-war JVC sales needed to absorb the {c['JVC']['launched_2026_units']:,} units launched in 2026"])
    w.writerow(["jvc_pipeline_months", c["JVC"]["months_from_pipeline"], f"months of post-war JVC sales in the {c['JVC']['units_awaiting_handover']:,} units sold off-plan since 2024 and not yet handed over (DLD)"])
    w.writerow(["jvc_valuation_gap_pct", g["JVC|Jul–Oct"]["gap_pct"], f"DLD valuations vs sale prices, JVC flats Jul–Oct 2026 (n={g['JVC|Jul–Oct']['valuations']} valuations)"])
print(pd.DataFrame(cover).to_string(), "\n", pd.DataFrame(gap).to_string())
