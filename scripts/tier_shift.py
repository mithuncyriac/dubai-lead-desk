"""Which test leads change tier when the rule's reference prices move from pre-war averages to post-war DLD medians,
and how the rule-based parser compares with the ground truth and with the AI model's earlier blind scores."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "scripts")
from rule_parser import score, REF

specs = json.loads(Path("eval/specs.json").read_text()) + json.loads(Path("eval/hard_specs.json").read_text())


def tier(s, ratio):
    if s["browsing"] or ratio < 0.70 or s["timeline_months"] > 12:
        return "Cold"
    if ratio >= 0.85 and s["timeline_months"] <= 3 and s["finance"] in ("cash", "mortgage_preapproved"):
        return "Hot"
    return "Warm"


shift = []
for s in specs:
    old_ref = s["budget_aed"] / s["ratio"]
    new_ref = REF[(s["area"], s["beds"])]
    old, new = tier(s, s["budget_aed"] / old_ref), tier(s, s["budget_aed"] / new_ref)
    s["true_tier_v2"] = new
    if old != new:
        shift.append(dict(case=s["id"], area=s["area"], beds=s["beds"], budget_aed=s["budget_aed"], old_ref=round(old_ref), new_ref=new_ref,
                          old_tier=old, new_tier=new))
moves = Counter(f"{x['old_tier']} → {x['new_tier']}" for x in shift)

# rule parser on the English test messages (60 originals + 30 stress), against v2 truth
msgs = {m["id"]: m["message"] for m in json.loads(Path("eval_blind/messages.json").read_text(encoding="utf-8"))}
msgs |= {m["id"]: m["message"] for m in json.loads(Path("eval_blind/hard_messages.json").read_text(encoding="utf-8"))}
truth = {s["id"]: s["true_tier_v2"] for s in specs}
parsed = {i: score(msgs[i]) for i in truth}
hit = {i: parsed[i]["tier"] == truth[i] for i in truth}
by_set = {k: f"{sum(hit[i] for i in truth if i.startswith(k))}/{sum(1 for i in truth if i.startswith(k))}" for k in ("E", "H")}
res = dict(n_cases=len(specs), changed=len(shift), moves=dict(moves), detail=shift,
           parser_accuracy_v2=round(sum(hit.values()) / len(hit), 3), parser_by_set=by_set,
           parser_misses=[dict(case=i, truth=truth[i], parser=parsed[i]["tier"]) for i in truth if not hit[i]])
Path("eval/tier_shift.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
Path("eval/specs_v2_truth.json").write_text(json.dumps(truth, indent=1))
print(json.dumps({k: v for k, v in res.items() if k not in ("detail", "parser_misses")}, indent=1))
for x in shift: print(x)
print("parser misses:", res["parser_misses"])
