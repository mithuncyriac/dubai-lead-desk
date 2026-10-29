"""Generate the hidden ground-truth spec for the evaluation set (60 enquiries + 12 planted duplicates)."""
import json, random
from pathlib import Path

random.seed(21102026)
OUT = Path("eval")
OUT.mkdir(exist_ok=True)

# DLD average sold price, last 12 months (Bayut-published), AED
DLD = {("JVC", 0): 698377, ("JVC", 1): 1111172, ("JVC", 2): 1691084, ("JVC", 3): 2311391,
       ("Dubai Marina", 0): 1239570, ("Dubai Marina", 1): 1790596, ("Dubai Marina", 2): 3465088, ("Dubai Marina", 3): 6120796}
CHANNELS = ["Bayut", "Property Finder", "WhatsApp", "Instagram DM", "Website form"]
FIRST = ["Ahmed", "Priya", "Olga", "James", "Fatima", "Rahul", "Elena", "Omar", "Sarah", "Vikram", "Aisha", "Dmitri",
         "Hannah", "Arjun", "Layla", "Tom", "Nadia", "Sanjay", "Irina", "Khalid"]
LAST = ["Khan", "Sharma", "Ivanova", "Smith", "Al Mansoori", "Nair", "Petrova", "Haddad", "Johnson", "Reddy",
        "Rahman", "Volkov", "Clarke", "Menon", "Saeed", "Walker", "Aziz", "Gupta", "Sokolova", "Al Hashimi"]


def tier(s):
    if s["browsing"] or s["ratio"] < 0.70 or s["timeline_months"] > 12:
        return "Cold"
    if s["ratio"] >= 0.85 and s["timeline_months"] <= 3 and s["finance"] in ("cash", "mortgage_preapproved"):
        return "Hot"
    return "Warm"


target = ["Hot"] * 20 + ["Warm"] * 20 + ["Cold"] * 20
specs = []
i = 0
while len(specs) < 60:
    want = target[len(specs)]
    area = random.choice(["JVC", "Dubai Marina"])
    beds = random.choice([0, 1, 1, 2, 2, 3])
    ref = DLD[(area, beds)]
    s = dict(area=area, beds=beds, dld_avg=ref, channel=random.choice(CHANNELS),
             residency=random.choice(["UAE resident", "UAE resident", "overseas"]), browsing=False)
    if want == "Hot":
        s.update(ratio=random.choice([0.86, 0.9, 0.95, 1.0, 1.05, 1.15]), timeline_months=random.choice([0, 1, 2, 3]),
                 finance=random.choice(["cash", "mortgage_preapproved"]))
    elif want == "Warm":
        s.update(ratio=random.choice([0.72, 0.78, 0.82, 0.9, 1.0, 1.1]), timeline_months=random.choice([1, 2, 4, 6, 9, 12]),
                 finance=random.choice(["mortgage_not_started", "unknown", "cash", "mortgage_preapproved"]))
    else:
        kind = random.choice(["budget", "timeline", "browsing"])
        s.update(ratio=random.choice([0.45, 0.55, 0.62, 0.68]) if kind == "budget" else random.choice([0.8, 0.95, 1.0]),
                 timeline_months=random.choice([18, 24, 36]) if kind == "timeline" else random.choice([1, 3, 6]),
                 finance=random.choice(["cash", "unknown", "mortgage_not_started"]), browsing=kind == "browsing")
    s["budget_aed"] = int(round(ref * s["ratio"], -4))
    s["ratio"] = round(s["budget_aed"] / ref, 3)
    s["true_tier"] = tier(s)
    if s["true_tier"] != want:
        continue
    i += 1
    s["id"] = f"E{i:02d}"
    s["name"] = f"{random.choice(FIRST)} {random.choice(LAST)}"
    s["phone_e164"] = "+97150" + str(random.randint(1000000, 9999999))
    s["unrealistic_budget"] = s["ratio"] < 0.70
    specs.append(s)

random.shuffle(specs)
# 12 planted duplicates: same person re-enquiring on another channel, phone and name written differently
dups = []
for k, s in enumerate(random.sample(specs, 12)):
    local = s["phone_e164"][4:]  # 50xxxxxxx
    fmt = ["0" + local, "00971" + local, "+971 " + local[:2] + " " + local[2:5] + " " + local[5:], "971" + local][k % 4]
    first, last = s["name"].split(" ", 1)
    alt = [first.lower() + " " + last.lower(), first[0] + ". " + last, first + " " + last.replace("a", "aa", 1), first][k % 4]
    dups.append(dict(id=f"D{k+1:02d}", duplicate_of=s["id"], phone_raw=fmt, name_raw=alt,
                     channel=random.choice([c for c in CHANNELS if c != s["channel"]])))

(OUT / "specs.json").write_text(json.dumps(specs, indent=1))
(OUT / "dups.json").write_text(json.dumps(dups, indent=1))
from collections import Counter
print(Counter(s["true_tier"] for s in specs), Counter((s["area"], s["beds"]) for s in specs).most_common(3))
print(json.dumps(specs[:2], indent=1))
