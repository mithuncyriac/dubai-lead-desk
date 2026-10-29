"""Score the blind stress-set run against hard_specs. Writes eval/hard_results.json."""
import json
from pathlib import Path

spec = {s["id"]: s for s in json.loads(Path("eval/hard_specs.json").read_text())}
got = {s["id"]: s for s in json.loads(Path("eval/scores_hard.json").read_text(encoding="utf-8"))}
LABEL = {"budget_words": "budget in words or odd format", "relative_timeline": "timeline relative to a date",
         "implicit_finance": "payment implied, not named", "decoy_numbers": "decoy price or area in the text",
         "thread": "facts spread over 3 messages", "terse": "under 15 words, abbreviations"}
FIELDS = [("area", "area"), ("beds", "beds"), ("budget", "budget_aed"), ("timeline", "timeline_months"),
          ("finance", "finance"), ("browsing", "browsing")]

by, misses, field_err = {}, [], {f: 0 for f, _ in FIELDS}
for i, s in spec.items():
    g = got[i]
    wrong = [f for f, k in FIELDS if str(g.get(k)).lower() != str(s[k]).lower()]
    for f in wrong:
        field_err[f] += 1
    ok = g["tier"] == s["true_tier"]
    b = by.setdefault(s["hardness"], dict(label=LABEL[s["hardness"]], n=0, correct=0, field_errors=0))
    b["n"] += 1
    b["correct"] += ok
    b["field_errors"] += bool(wrong)
    if wrong or not ok:   # record fact-level slips too, even when the tier still came out right
        misses.append(dict(id=i, hardness=LABEL[s["hardness"]], true=s["true_tier"], got=g["tier"],
                           why="misread " + ", ".join(f"{f} ({g.get(k)} vs {s[k]})" for f, k in FIELDS if f in wrong) if wrong
                           else "facts right, rule applied wrongly"))
for b in by.values():
    b["note"] = f"{b['field_errors']} with a misread fact" if b["field_errors"] else "all facts read correctly"
res = dict(n=len(spec), accuracy=sum(got[i]["tier"] == s["true_tier"] for i, s in spec.items()) / len(spec),
           hot_recall=sum(got[i]["tier"] == "Hot" for i, s in spec.items() if s["true_tier"] == "Hot") / 10,
           hot_false_alarms=sum(got[i]["tier"] == "Hot" for i, s in spec.items() if s["true_tier"] != "Hot"),
           field_errors=field_err, by_hardness=by, misses=misses)
Path("eval/hard_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
