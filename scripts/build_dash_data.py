"""Turn audit, market and eval results into the CSV datasets the dashboard reads (dash_data/)."""
import csv, json
from pathlib import Path

OUT = Path("dash_data")
OUT.mkdir(exist_ok=True)
A = json.loads(Path("data/audit_results.json").read_text(encoding="utf-8"))
E = json.loads(Path("eval/eval_results.json").read_text(encoding="utf-8"))
H = json.loads(Path("eval/hard_results.json").read_text(encoding="utf-8"))
DESK = json.loads(Path("eval/desk_results.json").read_text(encoding="utf-8"))
BEDS = {0: "Studio", 1: "1 bed", 2: "2 bed", 3: "3 bed"}


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# headline figures
dup = A["duplicates"]
write("headline.csv", [
    dict(metric="listings_audited", value=A["sample"]["total"], detail=f"Bayut {A['sample']['bayut']} + Property Finder {A['sample']['pf']}, JVC and Dubai Marina, 21 Oct 2026"),
    dict(metric="duplicate_share_pct", value=dup["excess_pct"], detail=f"{dup['excess_listings']} surplus copies across {dup['clusters']} units listed more than once"),
    dict(metric="cross_agency_units", value=dup["cross_broker"], detail="units advertised by two or more different agencies"),
    dict(metric="max_same_unit_spread_pct", value=dup["max_spread_pct"], detail="largest asking-price gap for one unit across listings"),
    dict(metric="stale_offplan", value=A["stale_offplan"]["n"], detail=f"of {A['stale_offplan']['of_bayut_offplan']} Bayut off-plan listings show a handover date already passed; DLD still records these projects as off-plan, so handover is late"),
    dict(metric="stress_accuracy_pct", value=round(100 * H["accuracy"], 1), detail=f"tier accuracy on {H['n']} deliberately hard enquiries, scored blind"),
    dict(metric="clean_accuracy_pct", value=round(100 * E["accuracy"], 1), detail=f"tier accuracy on {E['n']} plainly written enquiries, 3 blind runs"),
    dict(metric="dupes_caught", value=DESK["duplicates_caught"], detail=f"of {DESK['planted_duplicates']} planted re-enquiries merged; {DESK['false_merges']} false merges"),
])

# duplicate clusters
rows = []
for k, c in enumerate(dup["detail"], 1):
    rows.append(dict(cluster=f"U{k:02d}", area=c["area"], building=c["building"], beds=BEDS.get(c["beds"], f"{c['beds']} bed"),
                     size_sqft=c["size"], listings=c["n"], portals=" + ".join(c["portals"]), agencies=c["brokers"],
                     min_aed=c["min"], max_aed=c["max"], spread_pct=c["spread_pct"],
                     kind="different agencies" if c["cross_broker"] else ("both portals, same agency" if c["cross_portal"] else "same agency, same portal")))
write("same_unit.csv", rows)

# --- raw DLD data (transactions + Ejari rents, 1 Jan – 21 Oct 2026)
L = json.loads(Path("data/dld_results.json").read_text(encoding="utf-8"))
DAYS = 294  # 1 Jan – 21 Oct 2026 inclusive
jv, ma = L["areas"]["JVC"], L["areas"]["Dubai Marina"]
mon = {m["month"]: m for m in L["dubai_monthly"]}
write("dld_monthly.csv", [dict(month=m, dubai_deals=mon[m]["deals"], dubai_offplan_pct=round(100 * mon[m]["offplan_share"], 1),
                               jvc_deals=next(x["deals"] for x in jv["monthly"] if x["month"] == m),
                               marina_deals=next(x["deals"] for x in ma["monthly"] if x["month"] == m),
                               partial="yes" if mon[m]["partial"] else "no") for m in sorted(mon)])
jan, sep = mon["2026-01"]["deals"], mon["2026-09"]["deals"]

# yields from DLD: new Ejari leases vs ready-flat sales, matched by size band
pf_y = {(y["area"], y["beds"]): y["gross_yield_pct"] for y in A["yield_area"]}
band_beds = {"Studio-size": 0, "1-bed size": 1, "2-bed size": 2, "3-bed size": 3}
write("yields.csv", [dict(area=y["area"], size_band=y["size_band"], median_new_rent_aed=y["median_new_rent"], median_ready_price_aed=y["median_ready_price"],
                          gross_yield_pct=y["gross_yield_pct"], new_leases=y["n_new_leases"], ready_sales=y["n_ready_sales"],
                          listings_check_pct=pf_y.get((y["area"], band_beds[y["size_band"].split(" (")[0]]), ""))
                     for y in L["dld_yields"]])

# asking vs what DLD says buyers paid, per sq ft (ready flats)
write("asking_premium.csv", [dict(area=a, listing_median_psf=A["psf_median"][a], dld_ready_median_psf=L["areas"][a]["ready_median_psf"],
                                  premium_pct=round(100 * (A["psf_median"][a] / L["areas"][a]["ready_median_psf"] - 1), 1))
                             for a in ["JVC", "Dubai Marina"]])

R = L["rents"]
write("rent_dynamics.csv", [dict(area=a, new_leases=R[a]["new"], renewals=R[a]["renewed"], renewal_share_pct=round(100 * R[a]["renewal_share"], 1),
                                 new_rent_per_sqm=R[a]["new_median_rent_per_sqm"], renewed_rent_per_sqm=R[a]["renewed_median_rent_per_sqm"],
                                 new_vs_renewal_pct=R[a]["new_vs_renewal_gap_pct"]) for a in ["JVC", "Dubai Marina"]])

# cross-checks: raw DLD vs what Bayut publishes from DLD, and vs our listing-based yields
def chk(name, ours, theirs, why):
    d = round(100 * (ours / theirs - 1), 1)
    return dict(check=name, raw_dld=ours, published=theirs, diff_pct=d, verdict="matches" if abs(d) <= 3 else "differs", why=why)
recon = [
    chk("JVC average flat price, AED", jv["mean_flat_price"], 1075878, "Bayut's DLD 12-month average"),
    chk("Marina average flat price, AED", ma["mean_flat_price"], 3268013, "2026 raw data includes new off-plan towers selling at AED 4,000+/sq ft"),
    chk("JVC flat sales per year", round(jv["flat_deals"] * 365 / DAYS), 11823, "Bayut counts the last 12 months; sales slowed through 2026"),
    chk("Marina flat sales per year", round(ma["flat_deals"] * 365 / DAYS), 2205, "Bayut's DLD 12-month count"),
    chk("JVC 1-bed gross yield, %", next(y["gross_yield_pct"] for y in L["dld_yields"] if y["area"] == "JVC" and y["size_band"].startswith("1-bed")), pf_y[("JVC", 1)], "our Property Finder rent vs sale listings"),
    chk("Marina 1-bed gross yield, %", next(y["gross_yield_pct"] for y in L["dld_yields"] if y["area"] == "Dubai Marina" and y["size_band"].startswith("1-bed")), pf_y[("Dubai Marina", 1)], "our Property Finder rent vs sale listings; asking rents run above signed leases"),
]
write("reconciliation.csv", recon)

# asking vs DLD sold, and supply
ref = {}
with open("data/market_reference.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["beds"].isdigit():
            ref[(r["area"], int(r["beds"]))] = (int(r["avg_asking_aed_bayut_6m"]), int(r["avg_sold_aed_dld_12m"]))
write("asking_vs_sold.csv", [dict(area=a, beds=BEDS[b], avg_asking_aed=v[0], avg_sold_aed=v[1], gap_pct=round(100 * (v[0] - v[1]) / v[1], 1))
                             for (a, b), v in ref.items()])
write("supply.csv", [
    dict(area="JVC", live_listings_bayut=9436, live_listings_pf=8778, dld_deals_per_month=jv["avg_monthly_deals_full_months"],
         months_of_supply=round(9436 / jv["avg_monthly_deals_full_months"], 1)),
    dict(area="Dubai Marina", live_listings_bayut=3422, live_listings_pf=3728, dld_deals_per_month=ma["avg_monthly_deals_full_months"],
         months_of_supply=round(3422 / ma["avg_monthly_deals_full_months"], 1)),
])

# value of a lead (DLD 2026 average flat sale x 2% buyer commission x close-rate scenarios)
val = []
for area, avg in [("JVC", jv["mean_flat_price"]), ("Dubai Marina", ma["mean_flat_price"])]:
    for scen, cr in [("Low", 0.01), ("Base", 0.02), ("High", 0.03)]:
        val.append(dict(area=area, scenario=scen, avg_deal_aed=avg, commission_pct=2, close_rate_pct=round(cr * 100),
                        commission_per_deal_aed=round(avg * 0.02), value_per_lead_aed=round(avg * 0.02 * cr),
                        value_per_100_leads_aed=round(avg * 0.02 * cr * 100)))
write("lead_value.csv", val)

# evaluation
ev = [
    dict(test="Plain enquiries · tier", cases=E["n"], passed=round(E["accuracy"] * E["n"]), note="60 messages with facts stated plainly"),
    dict(test="Same answer on 3 runs", cases=E["n"], passed=round(E["stability_3runs"] * E["n"]), note="identical tier in three separate runs"),
    dict(test="Arabic, Hinglish, Russian, broken English", cases=60, passed=round(E["language_consistency_overall"] * 60), note="same tier as the English original"),
    dict(test="Unrealistic-budget flag", cases=E["unrealistic_flag"]["tp"] + E["unrealistic_flag"]["fn"] + E["unrealistic_flag"]["fp"],
         passed=E["unrealistic_flag"]["tp"], note=f"precision {E['unrealistic_flag']['precision']:.0%}, recall {E['unrealistic_flag']['recall']:.0%}"),
    dict(test="Duplicate re-enquiries merged", cases=DESK["planted_duplicates"], passed=DESK["duplicates_caught"], note="phone written 4 different ways, name spelt differently"),
]
for h, r in H["by_hardness"].items():
    ev.append(dict(test=f"Stress · {r['label']}", cases=r["n"], passed=r["correct"], note=r["note"]))
for e in ev:
    e["pass_rate_pct"] = round(100 * e["passed"] / e["cases"], 1)
write("evaluation.csv", ev)
write("stress_misses.csv", [dict(case=m["id"], hardness=m["hardness"], expected=m["true"], got=m["got"], why=m["why"]) for m in H["misses"]] or
      [dict(case="none", hardness="", expected="", got="", why="no misses")])
print("written", sorted(p.name for p in OUT.iterdir()))

# raw-DLD headline figures, appended once the DLD block above has run
with open(OUT / "headline.csv", "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["dubai_sales_drop_pct", round(100 * (sep / jan - 1), 1), f"Dubai residential sales, January {jan:,} to September {sep:,} (DLD)"])
    w.writerow(["marina_asking_premium_pct", next(r["premium_pct"] for r in csv.DictReader(open(OUT / "asking_premium.csv", encoding="utf-8")) if r["area"] == "Dubai Marina"),
                "median asking price per sq ft above what DLD recorded for ready Marina flats"])
    w.writerow(["dld_sales_read", L["window"]["rows"], f"DLD residential sales, {L['window']['first']} to {L['window']['last']}, plus {sum(R[a]['contracts'] for a in R):,} Ejari flat leases in the two areas"])

# ======== deeper version: war attribution, segments, price index, post-war rule, validation ========
WR = json.loads(Path("data/war_results.json").read_text(encoding="utf-8"))
L = json.loads(Path("data/dld_results.json").read_text(encoding="utf-8"))
TS = json.loads(Path("eval/tier_shift.json").read_text(encoding="utf-8"))
V2 = json.loads(Path("eval/v2_results.json").read_text(encoding="utf-8"))

write("war_effect.csv", [dict(model=("Trend model" if k == "trend" else "Year-effects model"), effect_pct=v["effect_pct"], ci_low_pct=v["ci_low_pct"],
                              ci_high_pct=v["ci_high_pct"], actual_sales=v["actual_post"], expected_sales=v["counterfactual_post"],
                              lost_sales=v["lost_deals"], days=v["n_days"]) for k, v in WR["dubai"].items()])
write("war_monthly.csv", [dict(month=m["month"], actual=m["actual"], expected=m["counterfactual"]) for m in WR["dubai_monthly_cf"]])
write("segments.csv", [dict(segment=s["segment"], effect_pct=s["effect_pct"], ci_low_pct=s["ci_low_pct"], ci_high_pct=s["ci_high_pct"],
                            actual_sales=s["actual_post"], lost_sales=s["lost_deals"]) for s in WR["segments"]])
write("price_index.csv", [dict(key=f"{r['area']}|{r['kind']}|{r['month']}", **r) for r in WR["price_index"]])

# post-war versions replace the full-year ones
write("asking_premium.csv", [dict(area=a, listing_median_psf=A2["psf_median"][a], dld_postwar_ready_psf=WR["postwar_ready_psf"][a],
                                  premium_pct=round(100 * (A2["psf_median"][a] / WR["postwar_ready_psf"][a] - 1), 1))
                             for A2 in [json.loads(Path("data/audit_results.json").read_text(encoding="utf-8"))] for a in ["JVC", "Dubai Marina"]])
pwy = {(y["area"], y["size_band"]): y for y in L["dld_yields_postwar"]}
write("yields.csv", [dict(area=y["area"], size_band=y["size_band"], gross_yield_pct=pwy[(y["area"], y["size_band"])]["gross_yield_pct"],
                          full_year_yield_pct=y["gross_yield_pct"], median_new_rent_aed=pwy[(y["area"], y["size_band"])]["median_new_rent"],
                          median_ready_price_aed=pwy[(y["area"], y["size_band"])]["median_ready_price"],
                          new_leases=pwy[(y["area"], y["size_band"])]["n_new_leases"], ready_sales=pwy[(y["area"], y["size_band"])]["n_ready_sales"])
                     for y in L["dld_yields"] if (y["area"], y["size_band"]) in pwy])

old_ref = {("JVC", 0): 698377, ("JVC", 1): 1111172, ("JVC", 2): 1691084, ("JVC", 3): 2311391,
           ("Dubai Marina", 0): 1239570, ("Dubai Marina", 1): 1790596, ("Dubai Marina", 2): 3465088, ("Dubai Marina", 3): 6120796}
write("rule_prices.csv", [dict(key=f"{m['area']}|{int(m['beds'])}", area=m["area"], beds=BEDS[int(m["beds"])], old_reference=old_ref[(m["area"], int(m["beds"]))],
                               postwar_median=m["median_price"], change_pct=round(100 * (m["median_price"] / old_ref[(m["area"], int(m["beds"]))] - 1), 1), n=m["n"])
                          for m in WR["postwar_medians"]])
write("tier_shift.csv", [dict(case=x["case"], area=x["area"], beds=BEDS[x["beds"]], budget_aed=x["budget_aed"], old_tier=x["old_tier"], new_tier=x["new_tier"])
                         for x in TS["detail"]])

# evaluation: add the post-war rule run and the rules-only baseline
ev = list(csv.DictReader(open(OUT / "evaluation.csv", encoding="utf-8")))
ev += [dict(test="Post-war rule · AI model, blind", cases=V2["n"], passed=V2["correct"], note=f"includes all {TS['changed']} leads whose tier changed", pass_rate_pct=round(100 * V2["correct"] / V2["n"], 1)),
       dict(test="Rules-only parser (no AI) · baseline", cases=TS["n_cases"], passed=round(TS["parser_accuracy_v2"] * TS["n_cases"]),
            note="regular expressions + same rule; shows what the AI adds", pass_rate_pct=round(100 * TS["parser_accuracy_v2"], 1))]
write("evaluation.csv", [{k: e[k] for k in ("test", "cases", "passed", "note", "pass_rate_pct")} for e in ev])

seg = {s["segment"]: s for s in WR["segments"]}
with open(OUT / "headline.csv", "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    ye = WR["dubai"]["year_effects"]
    w.writerow(["war_effect_pct", ye["effect_pct"], f"Dubai residential sales vs expected, 28 Feb – 19 Oct 2026 (95% range {ye['ci_low_pct']}% to {ye['ci_high_pct']}%)"])
    w.writerow(["lost_sales", ye["lost_deals"], f"{ye['actual_post']:,} sales registered vs {ye['counterfactual_post']:,} expected without the war"])
    w.writerow(["under1m_effect_pct", seg["Price · Under AED 1M"]["effect_pct"], "sales under AED 1M vs expected"])
    w.writerow(["over5m_effect_pct", seg["Price · AED 5M+"]["effect_pct"], "sales above AED 5M vs expected"])
    w.writerow(["tier_changes", TS["changed"], f"of {TS['n_cases']} test leads change tier with post-war prices, all upward"])
print("deeper datasets written")

# headline clean-up: the war model replaces the raw Jan→Sep drop; the premium uses post-war prices
hl = [r for r in csv.DictReader(open(OUT / "headline.csv", encoding="utf-8")) if r["metric"] not in ("dubai_sales_drop_pct", "marina_asking_premium_pct")]
for r in csv.DictReader(open(OUT / "asking_premium.csv", encoding="utf-8")):
    key = "jvc" if r["area"] == "JVC" else "marina"
    hl.append(dict(metric=f"{key}_asking_premium_pct", value=r["premium_pct"],
                   detail=f"median asking AED {int(r['listing_median_psf']):,}/sq ft vs DLD post-war sold AED {int(r['dld_postwar_ready_psf']):,} (ready flats, Jul–Oct 2026)"))
write("headline.csv", hl)
(OUT / "reconciliation.csv").unlink(missing_ok=True)
(OUT / "asking_vs_sold.csv").unlink(missing_ok=True)
