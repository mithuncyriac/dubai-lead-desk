"""Analyse raw DLD sales transactions + Ejari rent contracts (1 Jan – 21 Oct 2026). Writes data/dld_results.json."""
import json
import pandas as pd
from pathlib import Path

D = Path("data/dld")
SQFT = 10.7639
TX_AREAS = {"JVC": ["JUMEIRAH VILLAGE CIRCLE"], "Dubai Marina": ["DUBAI MARINA", "Marsa Dubai"]}
RENT_AREAS = {"JVC": ["Al Barsha South Fourth"], "Dubai Marina": ["Marsa Dubai"]}
BANDS = [(0, 45, "Studio-size (<45 m²)"), (45, 85, "1-bed size (45–85 m²)"), (85, 130, "2-bed size (85–130 m²)"), (130, 200, "3-bed size (130–200 m²)")]
ROOMS = {"Studio": 0, "1 B/R": 1, "2 B/R": 2, "3 B/R": 3}


def band(sqm):
    for lo, hi, name in BANDS:
        if lo <= sqm < hi:
            return name
    return None


t = pd.read_csv(D / "transactions.csv", encoding="utf-8-sig", dtype=str)
t["date"] = pd.to_datetime(t.INSTANCE_DATE)
t["month"] = t.date.dt.strftime("%Y-%m")
t["value"] = pd.to_numeric(t.TRANS_VALUE, errors="coerce")
t["sqm"] = pd.to_numeric(t.ACTUAL_AREA, errors="coerce")
t["area"] = None
for k, names in TX_AREAS.items():
    t.loc[t.AREA_EN.isin(names), "area"] = k
flats = t[(t.PROP_SB_TYPE_EN == "Flat") & (t.sqm > 15) & (t.value > 100000)].copy()
flats["psf"] = flats.value / (flats.sqm * SQFT)
flats = flats[(flats.psf > 300) & (flats.psf < 20000)]
flats["beds"] = flats.ROOMS_EN.map(ROOMS)
flats["band"] = flats.sqm.map(band)

full_months = sorted(m for m in t.month.unique() if m < "2026-10")
res = {"window": dict(first=str(t.date.min())[:10], last=str(t.date.max())[:10], rows=len(t))}

# Dubai-wide
dm = t.groupby("month").agg(deals=("TRANSACTION_NUMBER", "size"), offplan=("IS_OFFPLAN_EN", lambda s: (s == "Off-Plan").mean())).reset_index()
res["dubai_monthly"] = [dict(month=r.month, deals=int(r.deals), offplan_share=round(r.offplan, 3), partial=r.month not in full_months) for r in dm.itertuples()]
res["dubai_top_areas"] = [dict(area=a, deals=int(n)) for a, n in t.AREA_EN.value_counts().head(10).items()]
res["dubai_offplan_share"] = round((t.IS_OFFPLAN_EN == "Off-Plan").mean(), 3)

# per area
res["areas"] = {}
for k in TX_AREAS:
    a = t[t.area == k]
    f = flats[flats.area == k]
    ready = f[f.IS_OFFPLAN_EN == "Ready"]
    m = a.groupby("month").agg(deals=("TRANSACTION_NUMBER", "size"), offplan=("IS_OFFPLAN_EN", lambda s: (s == "Off-Plan").mean())).reset_index()
    by_beds = []
    for b in [0, 1, 2, 3]:
        fb = f[f.beds == b]
        rb = fb[fb.IS_OFFPLAN_EN == "Ready"]
        by_beds.append(dict(beds=b, deals=len(fb), median_price=int(fb.value.median()) if len(fb) else None,
                            ready_deals=len(rb), ready_median_price=int(rb.value.median()) if len(rb) >= 5 else None,
                            ready_median_psf=round(rb.psf.median()) if len(rb) >= 5 else None,
                            offplan_median_psf=round(fb[fb.IS_OFFPLAN_EN == "Off-Plan"].psf.median()) if (fb.IS_OFFPLAN_EN == "Off-Plan").sum() >= 5 else None))
    bands = pd.cut(f.value, [0, 750e3, 1e6, 1.5e6, 2e6, 3e6, 5e6, 1e12], labels=["<750k", "750k–1M", "1–1.5M", "1.5–2M", "2–3M", "3–5M", "5M+"])
    res["areas"][k] = dict(
        deals=len(a), flat_deals=len(f), mean_flat_price=int(f.value.mean()), median_flat_price=int(f.value.median()), offplan_share=round((a.IS_OFFPLAN_EN == "Off-Plan").mean(), 3),
        avg_monthly_deals_full_months=round(a[a.month.isin(full_months)].groupby("month").size().mean(), 1),
        ready_median_psf=round(ready.psf.median()), offplan_median_psf=round(f[f.IS_OFFPLAN_EN == "Off-Plan"].psf.median()),
        monthly=[dict(month=r.month, deals=int(r.deals), offplan_share=round(r.offplan, 3), partial=r.month not in full_months) for r in m.itertuples()],
        by_beds=by_beds, price_bands=[dict(band=str(b), deals=int(n)) for b, n in bands.value_counts(sort=False).items()],
        top_projects=[dict(project=p, deals=int(n)) for p, n in a.PROJECT_EN.value_counts().head(8).items()],
    )

# rents
rc = []
for f in ["rents_a.csv", "rents_b.csv", "rents_c.csv"]:
    r = pd.read_csv(D / f, encoding="utf-8-sig", dtype=str,
                    usecols=["REGISTRATION_DATE", "VERSION_EN", "AREA_EN", "ANNUAL_AMOUNT", "ACTUAL_AREA", "PROP_SUB_TYPE_EN", "USAGE_EN", "PROJECT_EN"])
    rc.append(r[r.AREA_EN.isin(sum(RENT_AREAS.values(), [])) & (r.PROP_SUB_TYPE_EN == "Flat") & (r.USAGE_EN == "Residential")])
r = pd.concat(rc)
r["rent"] = pd.to_numeric(r.ANNUAL_AMOUNT, errors="coerce")
r["sqm"] = pd.to_numeric(r.ACTUAL_AREA, errors="coerce")
r = r[(r.sqm > 15) & (r.rent > 10000)]
r["rpsm"] = r.rent / r.sqm
r = r[(r.rpsm > 200) & (r.rpsm < 6000)]
r["month"] = r.REGISTRATION_DATE.str[:7]
r["band"] = r.sqm.map(band)
r["area"] = r.AREA_EN.map({v: k for k, vs in RENT_AREAS.items() for v in vs})

res["rents"] = {}
yields = []
for k in RENT_AREAS:
    ra = r[r.area == k]
    new, ren = ra[ra.VERSION_EN == "New"], ra[ra.VERSION_EN == "Renewed"]
    ready = flats[(flats.area == k) & (flats.IS_OFFPLAN_EN == "Ready")]
    res["rents"][k] = dict(
        contracts=len(ra), new=len(new), renewed=len(ren), renewal_share=round(len(ren) / len(ra), 3),
        new_median_rent_per_sqm=round(new.rpsm.median()), renewed_median_rent_per_sqm=round(ren.rpsm.median()),
        new_vs_renewal_gap_pct=round(100 * (new.rpsm.median() / ren.rpsm.median() - 1), 1),
        monthly_new_leases=[dict(month=m, n=int(n)) for m, n in new.groupby("month").size().items()],
    )
    for lo, hi, name in BANDS:
        nb = new[new.band == name]
        sb = ready[ready.band == name]
        if len(nb) >= 20 and len(sb) >= 10:
            rent_med, price_med = nb.rent.median(), sb.value.median()
            yields.append(dict(area=k, size_band=name, n_new_leases=len(nb), n_ready_sales=len(sb),
                               median_new_rent=int(rent_med), median_ready_price=int(price_med),
                               gross_yield_pct=round(100 * (nb.rpsm.median() * 1) / (sb.value / sb.sqm).median(), 2)))
res["dld_yields"] = yields

Path("data/dld_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
show = {k: v for k, v in res.items() if k not in ("areas", "rents")}
print(json.dumps(show, indent=1, default=str)[:3500])
for k, v in res["areas"].items():
    print(k, {x: v[x] for x in v if x not in ("monthly", "price_bands", "top_projects")})
    print("  bands", v["price_bands"])
for k, v in res["rents"].items():
    print(k, {x: v[x] for x in v if x != "monthly_new_leases"})

# post-war only (Jul–Oct 2026): yields and ready-flat price per sq ft, to avoid mixing pre-war prices in
pw_y = []
for k in RENT_AREAS:
    nb_all = r[(r.area == k) & (r.VERSION_EN == "New") & (r.month >= "2026-07")]
    sb_all = flats[(flats.area == k) & (flats.IS_OFFPLAN_EN == "Ready") & (flats.month >= "2026-07")]
    for lo, hi, name in BANDS:
        nb, sb = nb_all[nb_all.band == name], sb_all[sb_all.band == name]
        if len(nb) >= 20 and len(sb) >= 10:
            pw_y.append(dict(area=k, size_band=name, n_new_leases=len(nb), n_ready_sales=len(sb), median_new_rent=int(nb.rent.median()),
                             median_ready_price=int(sb.value.median()), gross_yield_pct=round(100 * nb.rpsm.median() / (sb.value / sb.sqm).median(), 2)))
res["dld_yields_postwar"] = pw_y
Path("data/dld_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("post-war yields", [(y["area"], y["size_band"][:10], y["gross_yield_pct"], y["n_ready_sales"]) for y in pw_y])
