"""Extra datasets for the interactive redesign: per-area registered vs expected, events, deal-size mix,
reply-time assumptions and three real buyer posts for the 'try the desk' box."""
import csv, json
from pathlib import Path

OUT = Path("dash_data")
W = json.loads(Path("data/war_results.json").read_text(encoding="utf-8"))


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


rows = [dict(key=f"All|{m['month']}", area="All", month=m["month"], actual=m["actual"], expected=m["counterfactual"])
        for m in W["dubai_monthly_cf"] if m["month"] >= "2026-03"]
rows += [dict(key=f"{m['area']}|{m['month']}", area=m["area"], month=m["month"], actual=m["actual"], expected=m["counterfactual"])
         for m in W["area_monthly_cf"] if m["month"] >= "2026-03"]
write("war_monthly.csv", rows)

write("events.csv", [
    dict(event="Ramadan", start="2026-02-18", end="2026-03-19", kind="holiday"),
    dict(event="War begins", start="2026-02-28", end="2026-02-28", kind="shock"),
    dict(event="Eid al-Fitr", start="2026-03-19", end="2026-03-22", kind="holiday"),
    dict(event="Eid al-Adha", start="2026-05-26", end="2026-05-29", kind="holiday"),
])

write("band_mix.csv", [dict(key=f"{b['area']}|{b['band']}", **b) for b in W["band_mix"]])

# reply-time assumption: share of a lead's chance to close kept, by first-reply delay.
# ASSUMPTION. The shape follows the speed-to-lead finding of Oldroyd, McElheran & Elkington (HBR, 2011); the levels are not Dubai data.
write("reply_assumptions.csv", [
    dict(reply="Under 5 minutes", minutes=5, retained_pct=100),
    dict(reply="30 minutes", minutes=30, retained_pct=60),
    dict(reply="1 hour", minutes=60, retained_pct=45),
    dict(reply="Same day", minutes=480, retained_pct=25),
    dict(reply="Next day", minutes=1440, retained_pct=15),
])

posts = {p["id"]: p for p in json.loads(Path("eval_blind/real_posts.json").read_text(encoding="utf-8"))}
write("examples.csv", [dict(id=i, posted=posts[i]["post_date"], source="Public Reddit post, lightly trimmed", text=posts[i]["excerpt"])
                       for i in ("R02", "R23", "R16")])
print(sorted(p.name for p in OUT.iterdir()))
