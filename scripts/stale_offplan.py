"""Off-plan listings checked against DLD's own sales history, and an off-plan pipeline estimate.
A project counts as handed over when DLD registers resales of ready ("Existing Properties") units in it during 2026.
Writes dash_data/stale_offplan.csv and dash_data/pipeline.csv."""
import csv, json, re
import pandas as pd
from pathlib import Path

H = pd.read_csv("data/dld/hist_sales_2024on.csv", dtype=str,
                usecols=["instance_date", "reg_type_en", "master_project_en", "project_name_en", "building_name_en", "property_sub_type_en"])
H["area"] = H.master_project_en.map({"Jumeirah Village Circle": "JVC", "Dubai Marina": "Dubai Marina"})
H = H[H.area.notna() & H.project_name_en.notna()].copy()
H["ready"] = H.reg_type_en.str.startswith("Existing", na=False)


def key(s):
    s = str(s).lower()
    s = re.sub(r"\bby\b.*$", "", s)
    s = re.sub(r"\b(tower|towers|residence|residences|the|apartments|building|jvc|dubai|marina)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


H["k"] = H.project_name_en.map(key)
proj = H.groupby(["area", "project_name_en", "k"]).agg(
    offplan_sales=("ready", lambda s: int((~s).sum())), ready_sales_2026=("ready", lambda s: 0), first=("instance_date", "min"),
    last_offplan=("instance_date", lambda s: s.max())).reset_index()
r26 = H[H.ready & (H.instance_date >= "2026-01-01")].groupby("project_name_en").size()
proj["ready_sales_2026"] = proj.project_name_en.map(r26).fillna(0).astype(int)
proj["handed_over"] = proj.ready_sales_2026 > 0

# --- stale check on our off-plan listings
L = []
for r in csv.DictReader(open("data/listings_audit.csv", encoding="utf-8")):
    if r["status"] == "off-plan":
        L.append(dict(portal="Bayut", listing_id=r["listing_id"], area=r["area"], building=r["building"], listed_handover=r["handover"], url=r["url"]))
for r in csv.DictReader(open("data/pf_sale.csv", encoding="utf-8")):
    if r["completion_status"] == "off_plan":
        L.append(dict(portal="Property Finder", listing_id=r["listing_id"], area=r["area"], building=r["building"], listed_handover="", url=r["url"]))
L = list({(x["portal"], x["listing_id"]): x for x in L}.values())
rows = []
for x in L:
    k = key(x["building"])
    m = proj[(proj.area == x["area"]) & (proj.k == k)]
    if m.empty and len(k) >= 6:
        m = proj[(proj.area == x["area"]) & (proj.k.str.startswith(k[:7]) | proj.k.map(lambda s: len(s) >= 6 and k.startswith(s[:7])))]
    if m.empty:
        rows.append(dict(**x, dld_project="", ready_resales_2026="", verdict="not found in DLD sales"))
        continue
    pr = m.sort_values("ready_sales_2026").iloc[-1]
    rows.append(dict(**x, dld_project=pr.project_name_en, ready_resales_2026=int(pr.ready_sales_2026),
                     verdict="handed over, still sold as off-plan" if pr.handed_over else "still off-plan in DLD"))
st = pd.DataFrame(rows)
st.insert(0, "key", st.portal.str[0] + st.listing_id)
st.to_csv("dash_data/stale_offplan.csv", index=False)

# --- pipeline: units sold off-plan since 2024 in projects with no ready resales yet (a floor: excludes unsold units and pre-2024 sales)
W = json.loads(Path("data/war_results.json").read_text(encoding="utf-8"))
months_post = (pd.Timestamp(W["window"]["last"]) - pd.Timestamp("2026-02-28")).days / 30.44
seg = {s["segment"]: s for s in W["segments"]}
listings = {"JVC": 9436, "Dubai Marina": 3422}
pipe = []
for a in ["JVC", "Dubai Marina"]:
    pa = proj[proj.area == a]
    waiting = pa[~pa.handed_over]
    per_month = seg[f"Area · {a}"]["actual_post"] / months_post
    pipe.append(dict(area=a, projects_selling_offplan=len(pa), projects_handed_over=int(pa.handed_over.sum()),
                     units_sold_offplan_awaiting_handover=int(waiting.offplan_sales.sum()), sales_per_month_postwar=round(per_month),
                     months_from_listings=round(listings[a] / per_month, 1),
                     months_from_pipeline=round(waiting.offplan_sales.sum() / per_month, 1)))
pd.DataFrame(pipe).to_csv("dash_data/pipeline.csv", index=False)

print(st.verdict.value_counts().to_dict())
print(st[st.verdict.str.startswith("handed")][["portal", "area", "building", "dld_project", "ready_resales_2026", "listed_handover"]].to_string())
print(pd.DataFrame(pipe).to_string())
