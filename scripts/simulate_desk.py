"""Dry-run of the n8n Lead Desk logic in Python: normalise -> dedupe -> (AI model tier) -> human review -> route -> SLA.
Uses eval_blind/messages.json + eval/scores_run1.json, checks dedupe against eval/dups.json."""
import json, re
from datetime import datetime, timedelta
from pathlib import Path

msgs = json.loads(Path("eval_blind/messages.json").read_text(encoding="utf-8"))
scores = {s["id"]: s for s in json.loads(Path("eval/scores_run1.json").read_text(encoding="utf-8"))}
dups = {d["id"]: d["duplicate_of"] for d in json.loads(Path("eval/dups.json").read_text())}

ROSTER = [  # mock agent roster: area specialism + languages
    dict(agent="Agent A", areas={"JVC"}, langs={"en", "hi"}),
    dict(agent="Agent B", areas={"JVC"}, langs={"en", "ar"}),
    dict(agent="Agent C", areas={"Dubai Marina"}, langs={"en", "ru"}),
    dict(agent="Agent D", areas={"Dubai Marina"}, langs={"en", "ar"}),
]
SLA = {"Hot": 5, "Warm": 60, "Cold": 24 * 60}  # minutes to first reply before escalation


def e164(raw):
    d = re.sub(r"\D", "", raw)
    if d.startswith("00"):
        d = d[2:]
    if d.startswith("0"):
        d = "971" + d[1:]
    if not d.startswith("971"):
        d = "971" + d
    return "+" + d


def route(area, lang, load):
    pool = [r for r in ROSTER if area in r["areas"]] or ROSTER
    fit = [r for r in pool if lang in r["langs"]] or pool
    pick = min(fit, key=lambda r: load[r["agent"]])
    load[pick["agent"]] += 1
    return pick["agent"]


seen, load, log = {}, {r["agent"]: 0 for r in ROSTER}, []
t0 = datetime(2026, 10, 21, 9, 0)
for i, m in enumerate(msgs):
    ts = t0 + timedelta(minutes=7 * i)
    phone = e164(m["phone_raw"])
    rec = dict(id=m["id"], received_at=ts.isoformat(), phone=phone, channel=m["channel"])
    if phone in seen and ts - seen[phone]["ts"] <= timedelta(days=30):
        rec.update(action="merged_duplicate", merged_into=seen[phone]["id"])
        log.append(rec)
        continue
    s = scores.get(m["id"])
    if s is None:
        rec.update(action="error_no_score")
        log.append(rec)
        continue
    lang = (s.get("language") or "en")[:2]
    review = s.get("confidence", 1) < 0.6 or s.get("area") == "unknown"
    agent = route(s["area"], lang, load) if not review else "Human review"
    rec.update(action="human_review" if review else "routed", tier=s["tier"], agent=agent,
               sla_minutes=SLA[s["tier"]], draft_status="awaiting agent approval")
    seen[phone] = dict(id=m["id"], ts=ts)
    log.append(rec)

merged = {r["id"]: r["merged_into"] for r in log if r["action"] == "merged_duplicate"}
caught = sum(1 for d, orig in dups.items() if merged.get(d) == orig)
# a duplicate may arrive before its original; then the original is the one merged
caught += sum(1 for d, orig in dups.items() if merged.get(orig) == d)
false_merge = [k for k, v in merged.items() if k not in dups and v not in dups]
res = dict(messages=len(msgs), planted_duplicates=len(dups), duplicates_caught=caught, false_merges=len(false_merge),
           human_review=sum(r["action"] == "human_review" for r in log),
           routed=sum(r["action"] == "routed" for r in log), agent_load=load,
           hot_with_5min_sla=sum(r.get("tier") == "Hot" for r in log))
Path("eval/desk_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
Path("eval/desk_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
