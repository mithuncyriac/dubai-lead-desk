"""The single source of truth. Every number the dashboard, posts and README quote comes from site/facts.json;
site/chart_data.json holds the series the dashboard draws. Both are rebuilt from data/*.json and dash_data/*.csv.
Nothing here is typed by hand except labels."""
import csv, json
from datetime import date
from pathlib import Path

D = Path("dash_data")
OUT = Path("site")
OUT.mkdir(exist_ok=True)
W = json.loads(Path("data/war_results.json").read_text(encoding="utf-8"))
L = json.loads(Path("data/dld_results.json").read_text(encoding="utf-8"))
F = json.loads(Path("data/forecast.json").read_text(encoding="utf-8"))


def rows(name):
    return list(csv.DictReader(open(D / f"{name}.csv", encoding="utf-8")))


def num(x):
    f = float(x)
    return int(f) if f.is_integer() else f


HL = {r["metric"]: num(r["value"]) for r in rows("headline")}
seg = {r["segment"]: r for r in rows("segments")}
ye = W["dubai"]["year_effects"]
pi = {(r["area"], r["kind"], r["month"]): r for r in W["price_index"]}
last_month = max(m for (a, k, m) in pi if a == "JVC" and k == "Ready")
sc = {r["area"]: r for r in rows("supply_cover")}
ev = {r["test"]: r for r in rows("evaluation")}
monthly = {r["month"]: r for r in W["dubai_monthly_cf"]}
gap = lambda m: round(100 * (monthly[m]["actual"] / monthly[m]["counterfactual"] - 1), 1)

facts = {
    "data_to": W["window"]["last"],
    "data_to_label": f"{date.fromisoformat(W['window']['last']).day} {date.fromisoformat(W['window']['last']):%b %Y}",
    "war_start": "2026-02-28",
    "built": date.today().isoformat(),
    "source": "Dubai Land Department open data (sales transactions, Ejari rent contracts, projects, valuations)",

    "sales_read": W["window"]["rows"],                       # residential sales 2024-01-01 .. data_to
    "sales_read_from": W["window"]["first"],
    "leases_read": sum(r["contracts"] for r in L["rents"].values()),     # Ejari flat leases, JVC + Marina, 2026
    "listings_checked": HL["listings_audited"],

    "war_gap_pct": ye["effect_pct"],
    "war_gap_low_pct": ye["ci_low_pct"],
    "war_gap_high_pct": ye["ci_high_pct"],
    "war_gap_trend_model_pct": W["dubai"]["trend"]["effect_pct"],
    "sales_actual_post": ye["actual_post"],
    "sales_expected_post": ye["counterfactual_post"],
    "sales_missing_post": ye["lost_deals"],
    "gap_march_pct": gap("2026-03"),
    "gap_september_pct": gap("2026-09"),

    "band_under1m_pct": num(seg["Price · Under AED 1M"]["effect_pct"]),
    "band_1to2m_pct": num(seg["Price · AED 1–2M"]["effect_pct"]),
    "band_2to5m_pct": num(seg["Price · AED 2–5M"]["effect_pct"]),
    "band_over5m_pct": num(seg["Price · AED 5M+"]["effect_pct"]),
    "jvc_gap_pct": num(seg["Area · JVC"]["effect_pct"]),
    "marina_gap_pct": num(seg["Area · Dubai Marina"]["effect_pct"]),

    "jvc_ready_price_change_pct": round(float(pi[("JVC", "Ready", last_month)]["index"]) - 100, 1),
    "marina_ready_price_change_pct": round(float(pi[("Dubai Marina", "Ready", last_month)]["index"]) - 100, 1),
    "price_index_last_month": last_month,

    "jvc_pipeline_units": num(sc["JVC"]["units_awaiting_handover"]),
    "jvc_pipeline_months": num(sc["JVC"]["months_from_pipeline"]),
    "jvc_sales_per_month": num(sc["JVC"]["sales_per_month_postwar"]),
    "jvc_asking_premium_pct": HL["jvc_asking_premium_pct"],
    "marina_asking_premium_pct": HL["marina_asking_premium_pct"],
    "duplicate_share_pct": HL["duplicate_share_pct"],

    "desk_clean_pass": f"{ev['Plain enquiries · tier']['passed']}/{ev['Plain enquiries · tier']['cases']}",
    "desk_stress_pass": f"{sum(int(r['passed']) for t, r in ev.items() if t.startswith('Stress'))}/{sum(int(r['cases']) for t, r in ev.items() if t.startswith('Stress'))}",
    "desk_postwar_pass": f"{ev['Post-war rule · AI model, blind']['passed']}/{ev['Post-war rule · AI model, blind']['cases']}",
    "rules_only_pass_pct": num(ev["Rules-only parser (no AI) · baseline"]["pass_rate_pct"]),
    "dupes_caught": f"{HL['dupes_caught']}/12",
    "tier_changes": HL["tier_changes"],

    "forecast": F,
}

# the same results stated as pace (100% = the usual pattern), for calm, plain wording; nothing new is estimated
Y = {(r["area"], r["size_band"]): float(r["gross_yield_pct"]) for r in rows("yields")}
raw = W["yoy_raw"]
facts["pace"] = {
    "overall_pct": round(100 + ye["effect_pct"]), "low_pct": round(100 + ye["ci_low_pct"]), "high_pct": round(100 + ye["ci_high_pct"]),
    "march_pct": round(100 + gap("2026-03")), "september_pct": round(100 + gap("2026-09")),
    "under1m_pct": round(100 + facts["band_under1m_pct"]), "1to2m_pct": round(100 + facts["band_1to2m_pct"]),
    "2to5m_pct": round(100 + facts["band_2to5m_pct"]), "over5m_pct": round(100 + facts["band_over5m_pct"]),
}
facts["market"] = {
    "sales_per_month_mar_sep": raw["marsep_2026_per_month"],          # average registered sales a month, Mar-Sep 2026
    "q3_sales": raw["q3_2026"], "q3_value_aed_bn": raw["q3_value_2026_bn"],
    "jvc_yield_low_pct": min(v for (a, s), v in Y.items() if a == "JVC"), "jvc_yield_high_pct": max(v for (a, s), v in Y.items() if a == "JVC"),
    "marina_yield_low_pct": min(v for (a, s), v in Y.items() if a == "Dubai Marina"), "marina_yield_high_pct": max(v for (a, s), v in Y.items() if a == "Dubai Marina"),
    "under2m_share_pct": round(100 * (int(seg["Price · Under AED 1M"]["actual_sales"]) + int(seg["Price · AED 1–2M"]["actual_sales"])) / ye["actual_post"]),
}

charts = {
    "monthly": [dict(area=r["area"], month=r["month"], actual=int(r["actual"]), expected=int(r["expected"])) for r in rows("war_monthly")],
    "bands": [dict(band=s["segment"].split(" · ")[1], gap=num(s["effect_pct"]), low=num(s["ci_low_pct"]), high=num(s["ci_high_pct"]), sales=int(s["actual_sales"]))
              for s in rows("segments") if s["segment"].startswith("Price")],
    "price_index": [dict(area=a, month=m, index=float(r["index"]), n=int(r["n"])) for (a, k, m), r in sorted(pi.items()) if k == "Ready" and m >= "2025-07"],
    "supply": [dict(area=a, units=num(r["units_awaiting_handover"]), per_month=num(r["sales_per_month_postwar"]), months=num(r["months_from_pipeline"])) for a, r in sc.items()],
    "evaluation": [dict(test=r["test"], cases=int(r["cases"]), passed=int(r["passed"]), note=r["note"]) for r in rows("evaluation")],
    "validation": rows("validation"),
    "rule_prices": [dict(area=r["area"], beds=r["beds"], median=int(r["postwar_median"]), n=int(r["n"])) for r in rows("rule_prices")],
    "yields": [dict(area=r["area"], size=r["size_band"], gross_yield=float(r["gross_yield_pct"])) for r in rows("yields")],
}
(OUT / "facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False), encoding="utf-8")
# what the lead desk checks budgets against: DLD median sale price by area and bedrooms, Jul 2026 onwards
prices = {f"{r['area']}|{r['key'].split('|')[1]}": int(r["postwar_median"]) for r in rows("rule_prices")}
(OUT / "desk_prices.json").write_text(json.dumps(dict(as_of=facts["data_to"], prices=prices), indent=1), encoding="utf-8")
(OUT / "chart_data.json").write_text(json.dumps(charts, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v for k, v in facts.items() if k != "forecast"}, indent=1, ensure_ascii=False))
