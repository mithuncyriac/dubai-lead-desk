"""Our DLD-derived figures vs published third-party figures. Writes dash_data/validation.csv."""
import csv, json
from pathlib import Path

W = json.loads(Path("data/war_results.json").read_text(encoding="utf-8"))
L = json.loads(Path("data/dld_results.json").read_text(encoding="utf-8"))
y = W["yoy_raw"]
pi = {(r["area"], r["kind"], r["month"]): r["index"] for r in W["price_index"]}
pct = lambda a, b: round(100 * (a / b - 1), 1)

rows = []
def add(check, ours, theirs, unit, source, tol, why):
    gap = round(ours - theirs, 1) if unit == "pts" else pct(ours, theirs)
    rows.append(dict(check=check, ours=ours, published=theirs, unit=unit, source=source,
                     gap=gap, verdict="match" if abs(gap) <= tol else ("close" if abs(gap) <= 2 * tol else "miss"), why=why))

add("Q3 2026 residential deals", y["q3_2026"], 34000, "deals", "Cavendish Maxwell via The National", 3, "same DLD source")
add("Q3 2026 deals, change vs Q3 2025", pct(y["q3_2026"], y["q3_2025"]), -38, "pts", "Cavendish Maxwell via The National", 2, "same DLD source")
add("Q3 2026 sales value, change vs Q3 2025", pct(y["q3_value_2026_bn"], y["q3_value_2025_bn"]), -47, "pts", "Cavendish Maxwell via The National", 2, "same DLD source")
add("Q3 2026 sales value, AED bn", y["q3_value_2026_bn"], 72.6, "AED bn", "Cavendish Maxwell via The National", 3,
    "level differs: their total likely includes procedures we exclude (e.g. land and building sales classed outside 'Residential')")
add("Jan–Sep 2026 deals", y["jan_sep_2026"], 112580, "deals", "Cavendish Maxwell via The National", 3, "same DLD source")
add("Jan–Sep 2026 deals, change vs 2025", pct(y["jan_sep_2026"], y["jan_sep_2025"]), -23, "pts", "Cavendish Maxwell via The National", 2,
    "small gap; their 2025 base may include late-registered deals our export dates differently")
add("Monthly sales Mar–Sep vs Jan–Feb 2026", pct(y["marsep_2026_per_month"], y["janfeb_2026_per_month"]), -26, "pts", "S&P Global Ratings (DLD data)", 2,
    "S&P counts all sales incl. commercial; we count residential only")
add("First 12 days of March, change vs 2025", pct(y["first12_mar_2026"], y["first12_mar_2025"]), -37, "pts", "Goldman Sachs (UAE-wide)", 5,
    "miss: Goldman covers the whole UAE with an unpublished method; March 2025 was Ramadan, which lowers our comparison base")
add("Price move in March 2026 (ready flats, JVC)", pct(pi[("JVC", "Ready", "2026-03")], pi[("JVC", "Ready", "2026-02")]), -5.9, "pts", "ValuStrat Price Index", 2,
    "miss in timing: ValuStrat is valuation-based and reacts at once; March registrations were mostly deals agreed before the war. Our index falls from May")
add("Price move Feb–Oct 2026 (ready flats, JVC)", pct(pi[("JVC", "Ready", "2026-10")], pi[("JVC", "Ready", "2026-02")]), -10, "pts", "ValuStrat (cumulative since late Feb)", 3,
    "same direction, smaller: ValuStrat covers all Dubai incl. prime villas")
add("JVC average flat price, AED", L["areas"]["JVC"]["mean_flat_price"], 1075878, "AED", "Bayut (DLD 12-month average)", 3, "different window, same source")
add("Marina flat sales per year", round(L["areas"]["Dubai Marina"]["flat_deals"] * 365 / 294), 2205, "deals", "Bayut (DLD 12-month count)", 3, "different window, same source")

with open("dash_data/validation.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r["verdict"].ljust(6), r["check"], "| ours", r["ours"], "| published", r["published"], "| gap", r["gap"])
