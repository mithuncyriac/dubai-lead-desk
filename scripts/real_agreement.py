"""Real forum posts: AI model (blind) vs the rules-only parser. No answer key exists, so this reports agreement. Writes dash_data/real_posts.csv."""
import csv, json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "scripts")
from rule_parser import score

posts = {p["id"]: p["message"] for p in json.loads(Path("eval_blind/real_messages.json").read_text(encoding="utf-8"))}
cl = {s["id"]: s for s in json.loads(Path("eval_blind/out/scores_real.json").read_text(encoding="utf-8"))}
pr = {i: score(t) for i, t in posts.items()}
n = len(posts)


def same(a, b, tol=0.0):
    if a == "unknown" or b == "unknown":
        return a == b
    try:
        return abs(float(a) - float(b)) <= tol * max(abs(float(b)), 1)
    except (TypeError, ValueError):
        return str(a).lower() == str(b).lower()


tier = sum(cl[i]["tier"] == pr[i]["tier"] for i in posts)
fields = {f: sum(same(cl[i].get(f), pr[i][f], 0.05 if f == "budget_aed" else 0) for i in posts) for f in ("area", "beds", "budget_aed", "finance")}
review = sum(cl[i].get("area") == "unknown" or (cl[i].get("confidence") or 0) < 0.6 for i in posts)
unknown_budget = sum(cl[i].get("budget_aed") == "unknown" for i in posts)
mix = Counter(cl[i]["tier"] for i in posts)
disagree = [dict(id=i, ai_model=cl[i]["tier"], parser=pr[i]["tier"], ai_reason=cl[i].get("reason", "")) for i in posts if cl[i]["tier"] != pr[i]["tier"]]

rows = [
    dict(measure="Posts scored", value=n, note="public Reddit posts by buyers, 2024–2026, in their own words"),
    dict(measure="Same tier, AI model vs parser", value=f"{tier}/{n}", note="no answer key exists; this is agreement, not accuracy"),
    dict(measure="Same area read", value=f"{fields['area']}/{n}", note=""),
    dict(measure="Same bedrooms read", value=f"{fields['beds']}/{n}", note=""),
    dict(measure="Same budget read (±5%)", value=f"{fields['budget_aed']}/{n}", note="real posts often give ranges or no budget"),
    dict(measure="Budget not stated (AI model)", value=f"{unknown_budget}/{n}", note="these can never reach Hot under the rule"),
    dict(measure="Sent to human review", value=f"{review}/{n}", note="area unknown or confidence below 0.6"),
    dict(measure="AI tier mix", value=f"{mix['Hot']} Hot · {mix['Warm']} Warm · {mix['Cold']} Cold", note="real buyers mostly arrive Warm"),
]
with open("dash_data/real_posts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["measure", "value", "note"])
    w.writeheader()
    w.writerows(rows)
Path("eval/real_disagreements.json").write_text(json.dumps(disagree, indent=1), encoding="utf-8")
for r in rows:
    print(r["measure"], "|", r["value"])
for d in disagree:
    print(d)
