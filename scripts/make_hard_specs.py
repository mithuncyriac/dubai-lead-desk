"""Stress set: 30 specs with the same truth rule, each assigned a 'hardness' the message writer must use."""
import json, random
from pathlib import Path

random.seed(424242)
DLD = {("JVC", 0): 698377, ("JVC", 1): 1111172, ("JVC", 2): 1691084, ("JVC", 3): 2311391,
       ("Dubai Marina", 0): 1239570, ("Dubai Marina", 1): 1790596, ("Dubai Marina", 2): 3465088, ("Dubai Marina", 3): 6120796}
HARD = {
    "budget_words": "budget written in words or an odd format (e.g. 'two point one five million dirhams', 'AED 2,150k', '2.15 mn dhs')",
    "relative_timeline": "timeline given relative to a dated event; today is 21 Oct 2026 (e.g. 'before New Year' = 2 months, 'after my bonus in March' = 5 months, 'once my lease ends next October' = 12 months)",
    "implicit_finance": "finance implied, never named (cash: 'paying from savings, no loan needed'; preapproved: 'bank already issued my approval letter'; not started: 'will need to sort financing with a bank later')",
    "decoy_numbers": "includes a decoy price or area that is NOT the budget (e.g. 'saw a JVC 1BR for 900k on another portal but I want Marina, my budget is ...')",
    "thread": "written as 3 short WhatsApp messages separated by ' / ', with the facts spread across them and one self-correction ('sorry, I meant 2 beds')",
    "terse": "very terse, under 15 words, abbreviations only (e.g. 'mrna 2br 3.3m cash asap')",
}


def tier(s):
    if s["browsing"] or s["ratio"] < 0.70 or s["timeline_months"] > 12:
        return "Cold"
    if s["ratio"] >= 0.85 and s["timeline_months"] <= 3 and s["finance"] in ("cash", "mortgage_preapproved"):
        return "Hot"
    return "Warm"


specs, kinds = [], list(HARD) * 5
random.shuffle(kinds)
want = ["Hot", "Warm", "Cold"] * 10   # balanced tiers, so hot recall isn't measured on a handful
i = 0
while len(specs) < 30:
    h = kinds[len(specs)]
    area, beds = random.choice(["JVC", "Dubai Marina"]), random.choice([0, 1, 2, 3])
    ref = DLD[(area, beds)]
    ratio = random.choice([0.6, 0.68, 0.72, 0.8, 0.86, 0.9, 1.0, 1.1])  # includes near-threshold values
    budget = int(round(ref * ratio, -4))
    s = dict(id=f"H{len(specs) + 1:02d}", hardness=h, hardness_rule=HARD[h], area=area, beds=beds, budget_aed=budget,
             ratio=round(budget / ref, 3), timeline_months=random.choice([0, 1, 2, 3, 5, 12, 18]),
             finance=random.choice(["cash", "mortgage_preapproved", "mortgage_not_started", "unknown"]),
             browsing=random.random() < 0.1, phone_e164="+97152" + str(random.randint(1000000, 9999999)))
    s["true_tier"] = tier(s)
    if s["true_tier"] != want[len(specs)]:
        continue
    s["unrealistic_budget"] = s["ratio"] < 0.70
    specs.append(s)
Path("eval/hard_specs.json").write_text(json.dumps(specs, indent=1))
from collections import Counter
print(Counter(s["true_tier"] for s in specs), Counter(s["hardness"] for s in specs))
