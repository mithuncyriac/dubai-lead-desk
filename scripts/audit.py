"""Listing-truth audit across Bayut + Property Finder, plus rental yields. Writes data/audit_results.json."""
import csv, json, re, statistics as st
from collections import defaultdict
from datetime import date
from pathlib import Path

D = Path("data")
TODAY = date(2026, 10, 21)


def load(name):
    # portal search pages repeat promoted listings across pages; keep one row per listing id
    with open(D / name, encoding="utf-8") as f:
        return list({r["listing_id"]: r for r in csv.DictReader(f)}.values())


def norm_bldg(s):
    s = s.lower().replace("tower", "").replace("residences", "residence")
    s = re.sub(r"\bby\b.*$", "", s)           # "Pearl House III by Imtiaz" -> "pearl house iii"
    return re.sub(r"[^a-z0-9]", "", s)


bayut = load("listings_audit.csv")
pf = load("pf_sale.csv")
rent = load("pf_rent.csv")

sale = []
for r in bayut:
    sale.append(dict(portal="Bayut", id=r["listing_id"], area=r["area"], bldg=r["building"], beds=int(r["beds"]),
                     size=int(r["size_sqft"]), price=int(r["asking_aed"]), broker=r["brokerage"],
                     offplan=r["status"] == "off-plan", handover=r["handover"], url=r["url"], listed=""))
for r in pf:
    if not r["size_sqft"]:
        continue
    sale.append(dict(portal="Property Finder", id=r["listing_id"], area=r["area"], bldg=r["building"], beds=int(r["beds"]),
                     size=int(float(r["size_sqft"])), price=int(float(r["price_aed"])), broker=r["brokerage"],
                     offplan=r["completion_status"] == "off_plan", handover="", url=r["url"], listed=r["listed_date"]))
for s in sale:
    s["key"] = norm_bldg(s["bldg"])
    s["psf"] = s["price"] / s["size"]


def same_unit(a, b):
    return (a["area"] == b["area"] and a["key"] == b["key"] and a["beds"] == b["beds"]
            and abs(a["size"] - b["size"]) <= max(5, 0.005 * a["size"]))


# union-find clusters of "same unit" listings
parent = list(range(len(sale)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
for i in range(len(sale)):
    for j in range(i + 1, len(sale)):
        if same_unit(sale[i], sale[j]):
            parent[find(i)] = find(j)
groups = defaultdict(list)
for i, s in enumerate(sale):
    groups[find(i)].append(s)
clusters = [g for g in groups.values() if len(g) > 1]

cl_out = []
for g in sorted(clusters, key=lambda g: -len(g)):
    prices = [x["price"] for x in g]
    portals = sorted({x["portal"] for x in g})
    brokers = sorted({x["broker"].lower().split(" - ")[0].split(" real estate")[0].strip() for x in g})
    cl_out.append(dict(area=g[0]["area"], building=g[0]["bldg"], beds=g[0]["beds"], size=g[0]["size"],
                       n=len(g), portals=portals, brokers=len(brokers), cross_portal=len(portals) > 1,
                       cross_broker=len(brokers) > 1, same_price=len(set(prices)) == 1,
                       min=min(prices), max=max(prices), spread_pct=round(100 * (max(prices) - min(prices)) / min(prices), 1),
                       listings=[dict(portal=x["portal"], id=x["id"], broker=x["broker"], price=x["price"], url=x["url"]) for x in g]))

in_clusters = sum(c["n"] for c in cl_out)
excess = sum(c["n"] - 1 for c in cl_out)

# stale off-plan (handover passed)
def passed(h):
    m = re.match(r"Q(\d) (\d{4})", h or "")
    if not m:
        return False
    q, y = int(m.group(1)), int(m.group(2))
    return (y, q * 3) < (TODAY.year, TODAY.month)
stale = [s for s in sale if s["offplan"] and passed(s["handover"])]
bayut_offplan = [s for s in sale if s["portal"] == "Bayut" and s["offplan"]]

# listing age on PF
ages = [(TODAY - date.fromisoformat(s["listed"])).days for s in sale if s["listed"]]

# top-2 broker share of first pages, per portal x area
conc = {}
for portal in ["Bayut", "Property Finder"]:
    for area in ["JVC", "Dubai Marina"]:
        xs = [s["broker"].lower().split(" - ")[0] for s in sale if s["portal"] == portal and s["area"] == area]
        cnt = sorted(defaultdict(int, {b: xs.count(b) for b in set(xs)}).values(), reverse=True)
        conc[f"{portal}|{area}"] = dict(n=len(xs), top2_share=round(sum(cnt[:2]) / len(xs), 3), distinct=len(cnt))

# rental yields: median annual rent / median sale price, by area x beds; and by building where n>=2 both sides
rents = [dict(area=r["area"], key=norm_bldg(r["building"]), bldg=r["building"], beds=int(r["beds"]), rent=float(r["price_aed"]))
         for r in rent if r["price_period"] in ("yearly", "year") and r["price_aed"]]
ready = [s for s in sale if not s["offplan"]]
yld = []
for area in ["JVC", "Dubai Marina"]:
    for beds in [0, 1, 2, 3]:
        rr = [x["rent"] for x in rents if x["area"] == area and x["beds"] == beds]
        ss = [x["price"] for x in ready if x["area"] == area and x["beds"] == beds]
        if len(rr) >= 3 and len(ss) >= 3:
            yld.append(dict(area=area, beds=beds, n_rent=len(rr), n_sale=len(ss), median_rent=st.median(rr),
                            median_price=st.median(ss), gross_yield_pct=round(100 * st.median(rr) / st.median(ss), 2)))
bld_yld = []
for key in {x["key"] for x in rents}:
    for beds in [0, 1, 2, 3]:
        rr = [x for x in rents if x["key"] == key and x["beds"] == beds]
        ss = [x for x in ready if x["key"] == key and x["beds"] == beds]
        if rr and ss:
            bld_yld.append(dict(area=rr[0]["area"], building=rr[0]["bldg"], beds=beds, n_rent=len(rr), n_sale=len(ss),
                                rent=st.median(x["rent"] for x in rr), price=st.median(x["price"] for x in ss),
                                gross_yield_pct=round(100 * st.median(x["rent"] for x in rr) / st.median(x["price"] for x in ss), 2)))
bld_yld.sort(key=lambda x: -x["gross_yield_pct"])

res = dict(
    sample=dict(total=len(sale), bayut=sum(s["portal"] == "Bayut" for s in sale), pf=sum(s["portal"] != "Bayut" for s in sale),
                rent=len(rents), by_area={a: sum(s["area"] == a for s in sale) for a in ["JVC", "Dubai Marina"]}),
    duplicates=dict(clusters=len(cl_out), listings_in_clusters=in_clusters, excess_listings=excess,
                    excess_pct=round(100 * excess / len(sale), 1),
                    cross_portal=sum(c["cross_portal"] for c in cl_out), cross_broker=sum(c["cross_broker"] for c in cl_out),
                    max_spread_pct=max((c["spread_pct"] for c in cl_out), default=0), detail=cl_out),
    stale_offplan=dict(n=len(stale), of_bayut_offplan=len(bayut_offplan),
                       detail=[dict(bldg=s["bldg"], handover=s["handover"], url=s["url"]) for s in stale]),
    pf_listing_age_days=dict(n=len(ages), median=st.median(ages), over_60=sum(a > 60 for a in ages)),
    concentration=conc,
    psf_median={a: round(st.median(s["psf"] for s in ready if s["area"] == a)) for a in ["JVC", "Dubai Marina"]},
    yield_area=yld, yield_building=bld_yld,
)
(D / "audit_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
summary = {k: v for k, v in res.items() if k != "yield_building"}
summary["duplicates"] = {k: v for k, v in res["duplicates"].items() if k != "detail"}
print(json.dumps(summary, indent=1))
for c in cl_out:
    print(c["area"], c["building"], c["beds"], c["size"], c["n"], c["portals"], "brokers", c["brokers"], c["min"], c["max"], c["spread_pct"])
print("building yields (n_rent>=2):", [b for b in bld_yld if b["n_rent"] >= 2][:8])
