"""Score the blind AI-model runs against the hidden spec. Writes eval/eval_results.json and eval/eval_results.csv."""
import csv, json
from collections import Counter
from pathlib import Path

E = Path("eval")
spec = {s["id"]: s for s in json.loads((E / "specs.json").read_text())}
runs = [{s["id"]: s for s in json.loads((E / f"scores_run{k}.json").read_text(encoding="utf-8"))} for k in (1, 2, 3)]
var = json.loads((E / "scores_variants.json").read_text(encoding="utf-8"))
T = ["Hot", "Warm", "Cold"]
ids = sorted(spec)

r1 = runs[0]
acc = sum(r1[i]["tier"] == spec[i]["true_tier"] for i in ids) / len(ids)
conf = {t: {p: sum(1 for i in ids if spec[i]["true_tier"] == t and r1[i]["tier"] == p) for p in T} for t in T}
hot_prec = conf["Hot"]["Hot"] / max(1, sum(conf[t]["Hot"] for t in T))
hot_rec = conf["Hot"]["Hot"] / 20
misses = [dict(id=i, true=spec[i]["true_tier"], got=r1[i]["tier"], reason=r1[i].get("reason", ""),
               extracted=dict(budget=r1[i].get("budget_aed"), timeline=r1[i].get("timeline_months"), finance=r1[i].get("finance")),
               truth=dict(budget=spec[i]["budget_aed"], timeline=spec[i]["timeline_months"], finance=spec[i]["finance"]))
          for i in ids if r1[i]["tier"] != spec[i]["true_tier"]]

field_acc = {}
for f, key in [("budget", "budget_aed"), ("timeline", "timeline_months"), ("finance", "finance")]:
    field_acc[f] = sum(str(r1[i].get(key)) == str(spec[i][key]) for i in ids) / len(ids)

stable = sum(len({r[i]["tier"] for r in runs}) == 1 for i in ids) / len(ids)
run_acc = [sum(r[i]["tier"] == spec[i]["true_tier"] for i in ids) / len(ids) for r in runs]

vc = Counter()
vt = Counter()
for v in var:
    vt[v["lang"]] += 1
    vc[v["lang"]] += v["tier"] == r1[v["base_id"]]["tier"]
v_true = sum(v["tier"] == spec[v["base_id"]]["true_tier"] for v in var) / len(var)

tp = sum(r1[i]["unrealistic_budget"] and spec[i]["unrealistic_budget"] for i in ids)
fp = sum(r1[i]["unrealistic_budget"] and not spec[i]["unrealistic_budget"] for i in ids)
fn = sum((not r1[i]["unrealistic_budget"]) and spec[i]["unrealistic_budget"] for i in ids)

res = dict(n=len(ids), accuracy=round(acc, 3), run_accuracy=[round(a, 3) for a in run_acc], confusion_true_by_pred=conf,
           hot_precision=round(hot_prec, 3), hot_recall=round(hot_rec, 3), field_accuracy={k: round(v, 3) for k, v in field_acc.items()},
           stability_3runs=round(stable, 3),
           language_consistency={k: f"{vc[k]}/{vt[k]}" for k in vt}, language_consistency_overall=round(sum(vc.values()) / len(var), 3),
           variants_vs_truth=round(v_true, 3),
           unrealistic_flag=dict(tp=tp, fp=fp, fn=fn, precision=round(tp / max(1, tp + fp), 3), recall=round(tp / max(1, tp + fn), 3)),
           misses=misses)
(E / "eval_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
with open(E / "eval_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "true_tier", "run1", "run2", "run3", "true_budget", "got_budget", "true_timeline", "got_timeline", "true_finance", "got_finance"])
    for i in ids:
        w.writerow([i, spec[i]["true_tier"], *[r[i]["tier"] for r in runs], spec[i]["budget_aed"], r1[i].get("budget_aed"),
                    spec[i]["timeline_months"], r1[i].get("timeline_months"), spec[i]["finance"], r1[i].get("finance")])
print(json.dumps({k: v for k, v in res.items() if k != "misses"}, indent=1))
for m in misses:
    print(m)
