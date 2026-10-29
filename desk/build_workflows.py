"""Builds the four n8n workflows (n8n 2.42.5) as importable JSON in desk/workflows/, plus desk/test_set.json.

A  Lead Desk      webhook or form -> read the enquiry -> tier + budget check against DLD prices -> draft reply
                  -> log to leads.csv + save the draft for approval (Telegram optional, off by default)
F  Enquiry form   a public web form that hands each submission to A (n8n keeps forms and webhook replies apart)
B  Test Harness   sends the 90 test enquiries through A and scores the tiers against the hidden answers
C  Weekly Refresh every Monday 07:00 Dubai (or on demand): asks the pipeline service to pick up a new DLD export,
                  rerun the numbers, test and commit
E  Desk Errors    any failure in A, B or C is written to errors.log (Telegram optional)
No paid service is needed: the reading is rules-only (scripts/rule_parser.py, ported to desk/desk_logic.js).
"""
import json, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "workflows"
OUT.mkdir(exist_ok=True)
DESK_JS = (HERE / "desk_logic.js").read_text(encoding="utf-8")
IDS = dict(A="DLDeskLeadDesk01", B="DLDeskHarness001", C="DLDeskRefresh001", E="DLDeskErrors0001", F="DLDeskForm000001")


def node(name, type_, version, pos, params=None, **extra):
    return dict(id=name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("?", "").replace("+", "and"),
                name=name, type=type_, typeVersion=version, position=pos, parameters=params or {}, **extra)


def note(text, pos, w=420, h=200, color=7):
    return node(f"Note {zlib.crc32(text.encode()) % 10000:04d}", "n8n-nodes-base.stickyNote", 1, pos, dict(content=text, width=w, height=h, color=color))


def connect(pairs):
    c = {}
    for a, b, *idx in pairs:
        out = idx[0] if idx else 0
        c.setdefault(a, {"main": []})
        while len(c[a]["main"]) <= out:
            c[a]["main"].append([])
        c[a]["main"][out].append(dict(node=b, type="main", index=0))
    return c


def workflow(key, name, nodes, pairs, error=True):
    settings = dict(executionOrder="v1", timezone="Asia/Dubai", saveManualExecutions=True)
    if error:
        settings["errorWorkflow"] = IDS["E"]
    return dict(id=IDS[key], name=name, nodes=nodes, connections=connect(pairs), settings=settings, active=False, pinData={})


def code(body):
    return dict(jsCode=body.strip() + "\n", mode="runOnceForAllItems", language="javaScript")


# ---------- A: Lead Desk ----------
READ = DESK_JS + r"""

// ---- n8n: read each enquiry ----
const fs = require('fs'), path = require('path');
const dir = $env.DESK_DIR, site = $env.SITE_DIR;
const { prices } = JSON.parse(fs.readFileSync(path.join(site, 'desk_prices.json'), 'utf8'));
const logFile = path.join(dir, 'leads.csv');
const seen = fs.existsSync(logFile) ? fs.readFileSync(logFile, 'utf8').split('\n').slice(1).filter(Boolean).map(l => l.split(',')) : [];
const out = [];
for (const item of $input.all()) {
  const b = item.json.body ?? item.json;                         // webhook puts fields in body; the form does not
  const message = String(b.message ?? b.Message ?? '').trim();
  if (!message) throw new Error('Enquiry has no message text');
  const now = new Date();
  const asOf = b.as_of ? { y: +b.as_of.slice(0, 4), m: +b.as_of.slice(5, 7) } : { y: now.getFullYear(), m: now.getMonth() + 1 };
  const f = DESK.parse(message, asOf);
  const t = DESK.tier(f, prices);
  const phone = DESK.e164(b.phone ?? b.Phone ?? '');
  // duplicate = same phone within 30 days (column 2 of leads.csv is the phone, column 1 the time)
  const dup = b.test_run ? null : seen.find(r => r[2] === phone && now - new Date(r[1]) <= 30 * 864e5);
  const needsHuman = f.area === 'unknown' || (f.budget_aed === 'unknown' && f.beds === 'unknown');
  out.push({ json: {
    id: 'L' + now.getTime().toString(36).toUpperCase(), received_at: now.toISOString(),
    name: String(b.name ?? b.Name ?? '').trim(), phone, channel: b.channel ?? b.Channel ?? 'Web form', message,
    ...f, reference_price_aed: t.ref, budget_ratio: t.ratio, tier: t.tier,
    duplicate_of: dup ? dup[0] : null, needs_human: needsHuman, test_run: !!b.test_run,
    prices_as_of: JSON.parse(fs.readFileSync(path.join(site, 'desk_prices.json'), 'utf8')).as_of,
  } });
}
return out;
"""

DRAFT = DESK_JS + r"""

// ---- n8n: draft the first reply (the agent approves before anything is sent) ----
return $input.all().map(item => {
  const j = item.json;
  const draft = j.duplicate_of
    ? `Duplicate of ${j.duplicate_of}: same phone in the last 30 days. Add this message to that lead; no new reply.`
    : DESK.draftReply(j, { ref: j.reference_price_aed, ratio: j.budget_ratio }, new Date());
  return { json: { ...j, draft, status: j.duplicate_of ? 'merged' : j.needs_human ? 'needs a person' : 'awaiting approval' } };
});
"""

LOG = r"""
// ---- n8n: log every lead to leads.csv (opens in Excel or Google Sheets) and save the draft for approval ----
const fs = require('fs'), path = require('path');
const dir = $env.DESK_DIR;
fs.mkdirSync(path.join(dir, 'drafts'), { recursive: true });
const file = path.join(dir, 'leads.csv');
const cols = ['id', 'received_at', 'phone', 'name', 'channel', 'area', 'beds', 'budget_aed', 'timeline_months', 'finance', 'browsing',
              'reference_price_aed', 'budget_ratio', 'tier', 'duplicate_of', 'status', 'message'];
const cell = v => { const s = v === null || v === undefined ? '' : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
if (!fs.existsSync(file)) fs.writeFileSync(file, cols.join(',') + '\n');
for (const { json: j } of $input.all()) {
  fs.appendFileSync(file, cols.map(c => cell(j[c])).join(',') + '\n');
  if (!j.duplicate_of) fs.writeFileSync(path.join(dir, 'drafts', `${j.id}-${j.tier}.txt`),
    `Lead ${j.id} · ${j.tier} · ${j.status}\nFrom: ${j.name || 'unknown'} (${j.phone}) via ${j.channel}\nMessage: ${j.message}\n\n` +
    `Read as: area ${j.area}, beds ${j.beds}, budget ${j.budget_aed}, timeline ${j.timeline_months}, payment ${j.finance}` +
    (j.budget_ratio ? `, budget is ${Math.round(j.budget_ratio * 100)}% of the DLD median (AED ${j.reference_price_aed})` : '') +
    `\n\nDRAFT REPLY (approve or edit before sending):\n${j.draft}\n`);
}
return $input.all();
"""

RESPOND_BODY = "={{ { id: $json.id, tier: $json.tier, status: $json.status, read_as: { area: $json.area, beds: $json.beds, budget_aed: $json.budget_aed, timeline_months: $json.timeline_months, finance: $json.finance, browsing: $json.browsing }, budget_vs_dld_median: $json.budget_ratio, duplicate_of: $json.duplicate_of, draft: $json.draft } }}"

A = workflow("A", "Dubai Lead Desk · A · Lead desk", [
    node("Enquiry in (webhook)", "n8n-nodes-base.webhook", 2, [0, 0], dict(httpMethod="POST", path="lead-desk", responseMode="responseNode", options={}),
         webhookId="9b1f0d6e-6a51-4c1e-9f0a-1d2b3c4d5e01"),
    node("Read the enquiry", "n8n-nodes-base.code", 2, [260, 100], code(READ)),
    node("Draft the reply", "n8n-nodes-base.code", 2, [500, 100], code(DRAFT)),
    node("Test run?", "n8n-nodes-base.if", 2.2, [740, 100], dict(
        conditions=dict(options=dict(caseSensitive=True, leftValue="", typeValidation="loose", version=2), combinator="and",
                        conditions=[dict(id="t1", leftValue="={{ $json.test_run }}", rightValue=True, operator=dict(type="boolean", operation="true", singleValue=True))]),
        looseTypeValidation=True, options={})),
    node("Log lead + save draft", "n8n-nodes-base.code", 2, [980, 200], code(LOG)),
    node("Send draft to Telegram (optional)", "n8n-nodes-base.telegram", 1.2, [1220, 200], dict(
        chatId="={{ $env.TELEGRAM_CHAT_ID }}", text="={{ `New ${$json.tier} lead ${$json.id}\\n${$json.message}\\n\\nDraft:\\n${$json.draft}` }}",
        additionalFields=dict(appendAttribution=False)), disabled=True),
    node("Reply to caller", "n8n-nodes-base.respondToWebhook", 1.1, [1700, 100], dict(respondWith="json", responseBody=RESPOND_BODY, options={})),
    note("## A · Lead desk\nEnquiries arrive at the webhook: from the form (workflow F), a portal or a WhatsApp bridge. Reads the enquiry with rules (no AI, no cost), checks the budget against DLD's post-war median price, sets Hot/Warm/Cold and drafts a reply.\n\nNothing is sent to the buyer: drafts wait in `desk/runtime/drafts/` for an agent. Every lead goes to `leads.csv`.\n\nTelegram is off. To use it: add a Telegram credential, set TELEGRAM_CHAT_ID, enable the node.", [-40, -300], 520, 260, 4),
], [("Enquiry in (webhook)", "Read the enquiry"), ("Read the enquiry", "Draft the reply"),
    ("Draft the reply", "Test run?"), ("Test run?", "Reply to caller", 0), ("Test run?", "Log lead + save draft", 1),
    ("Log lead + save draft", "Send draft to Telegram (optional)"), ("Send draft to Telegram (optional)", "Reply to caller")])


# ---------- F: public enquiry form -> A ----------
F = workflow("F", "Dubai Lead Desk · F · Enquiry form", [
    node("Enquiry form", "n8n-nodes-base.formTrigger", 2.2, [0, 0], dict(
        formTitle="Ask about a home in JVC or Dubai Marina",
        formDescription="Demo of the Dubai Lead Desk. Please use test details, not real ones.",
        formFields=dict(values=[dict(fieldLabel="Name", requiredField=True), dict(fieldLabel="Phone", requiredField=True),
                                dict(fieldLabel="Message", fieldType="textarea", requiredField=True)]),
        responseMode="onReceived", options=dict(path="lead-form", respondWithOptions=dict(values=dict(formSubmittedText="Thanks. An agent will reply shortly.")))),
         webhookId="9b1f0d6e-6a51-4c1e-9f0a-1d2b3c4d5e02"),
    node("Hand to lead desk", "n8n-nodes-base.httpRequest", 4.2, [260, 0], dict(
        method="POST", url="http://127.0.0.1:5678/webhook/lead-desk", sendBody=True, specifyBody="json",
        jsonBody="={{ { name: $json.Name, phone: $json.Phone, message: $json.Message, channel: 'Web form' } }}", options=dict(timeout=30000))),
    note("## F · Enquiry form\nOpen `/form/lead-form`. Each submission goes to the lead desk (A) exactly like a webhook enquiry.", [-40, -220], 420, 160, 4),
], [("Enquiry form", "Hand to lead desk")])

# ---------- B: Test harness ----------
LOAD = r"""
// the hidden answers stay in this workflow; A only ever sees the message
const fs = require('fs'), path = require('path');
const cases = JSON.parse(fs.readFileSync(path.join($env.DESK_DIR, '..', 'test_set.json'), 'utf8'));
return cases.map(c => ({ json: c }));
"""
SCORE = r"""
const fs = require('fs'), path = require('path');
const cases = $('Load test set').all().map(i => i.json);
const got = $input.all().map(i => i.json);
const rows = cases.map((c, i) => ({ id: c.id, set: c.set, expected: c.truth, got: got[i].tier, ok: got[i].tier === c.truth }));
const by = s => { const r = rows.filter(x => x.set === s); return `${r.filter(x => x.ok).length}/${r.length}`; };
const report = { ran_at: new Date().toISOString(), cases: rows.length, correct: rows.filter(r => r.ok).length,
  accuracy_pct: Math.round(1000 * rows.filter(r => r.ok).length / rows.length) / 10,
  plain_set: by('plain'), stress_set: by('stress'), misses: rows.filter(r => !r.ok),
  note: 'Rules-only reading (no AI). The published Python baseline is 77/90 (85.6%); the AI model scored 90/90 blind.' };
fs.writeFileSync(path.join($env.DESK_DIR, 'harness_report.json'), JSON.stringify(report, null, 1));
return [{ json: report }];
"""
B = workflow("B", "Dubai Lead Desk · B · Test harness", [
    node("Run harness (webhook)", "n8n-nodes-base.webhook", 2, [0, 0], dict(httpMethod="POST", path="desk-test", responseMode="responseNode", options={}),
         webhookId="9b1f0d6e-6a51-4c1e-9f0a-1d2b3c4d5e03"),
    node("Run harness (manual)", "n8n-nodes-base.manualTrigger", 1, [0, 200]),
    node("Load test set", "n8n-nodes-base.code", 2, [240, 100], code(LOAD)),
    node("Send to lead desk", "n8n-nodes-base.httpRequest", 4.2, [480, 100], dict(
        method="POST", url="http://127.0.0.1:5678/webhook/lead-desk", sendBody=True, specifyBody="json",
        jsonBody="={{ { message: $json.message, name: $json.name, phone: $json.phone, channel: 'Test harness', test_run: true, as_of: '2026-10' } }}",
        options=dict(batching=dict(batch=dict(batchSize=10, batchInterval=200)), timeout=30000))),
    node("Score against hidden answers", "n8n-nodes-base.code", 2, [720, 100], code(SCORE)),
    node("Came from webhook?", "n8n-nodes-base.if", 2.2, [960, 100], dict(
        conditions=dict(options=dict(caseSensitive=True, leftValue="", typeValidation="loose", version=2), combinator="and",
                        conditions=[dict(id="w2", leftValue="={{ $('Run harness (webhook)').isExecuted }}", rightValue=True, operator=dict(type="boolean", operation="true", singleValue=True))]),
        looseTypeValidation=True, options={})),
    node("Return report", "n8n-nodes-base.respondToWebhook", 1.1, [1200, 100], dict(respondWith="json", responseBody="={{ $json }}", options={})),
    note("## B · Test harness\n90 test enquiries (60 plain, 30 deliberately hard) go through A exactly like real ones, marked as test runs so nothing is logged. The tiers are scored against answers A never sees. Report: `desk/runtime/harness_report.json`.", [-40, -260], 520, 200, 5),
], [("Run harness (webhook)", "Load test set"), ("Run harness (manual)", "Load test set"), ("Load test set", "Send to lead desk"),
    ("Send to lead desk", "Score against hidden answers"), ("Score against hidden answers", "Came from webhook?"), ("Came from webhook?", "Return report", 0)])

# ---------- C: Weekly refresh ----------
SUMMARY = r"""
const fs = require('fs'), path = require('path');
const r = $json;
const line = `${new Date().toISOString()} data_to=${r.data_to} new_export=${(r.new_export || []).join('+') || 'none'} ` +
  `changed=${Object.keys(r.changed || {}).length} tests=${r.tests} commit=${r.commit} pushed=${r.pushed}\n`;
fs.appendFileSync(path.join($env.DESK_DIR, 'refresh_log.txt'), line);
const moved = Object.entries(r.changed || {}).map(([k, [a, b]]) => `${k}: ${a} → ${b}`);
return [{ json: { ...r, summary: moved.length ? `Numbers moved: ${moved.join('; ')}` : `No headline number moved (data to ${r.data_to}).` } }];
"""
C = workflow("C", "Dubai Lead Desk · C · Weekly refresh", [
    node("Every Monday 07:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0], dict(rule=dict(interval=[dict(field="weeks", weeksInterval=1, triggerAtDay=[1], triggerAtHour=7)]))),
    node("Refresh now (webhook)", "n8n-nodes-base.webhook", 2, [0, 200], dict(httpMethod="POST", path="desk-refresh", responseMode="responseNode", options={}),
         webhookId="9b1f0d6e-6a51-4c1e-9f0a-1d2b3c4d5e04"),
    node("Rerun the numbers", "n8n-nodes-base.httpRequest", 4.2, [260, 100], dict(
        method="POST", url="={{ $env.PIPELINE_URL }}/refresh", options=dict(timeout=900000))),
    node("Summarise + log", "n8n-nodes-base.code", 2, [500, 100], code(SUMMARY)),
    node("Tell me on Telegram (optional)", "n8n-nodes-base.telegram", 1.2, [740, 100], dict(
        chatId="={{ $env.TELEGRAM_CHAT_ID }}", text="={{ 'Dubai Lead Desk refresh: ' + $json.summary }}", additionalFields=dict(appendAttribution=False)), disabled=True),
    node("Came from webhook?", "n8n-nodes-base.if", 2.2, [980, 100], dict(
        conditions=dict(options=dict(caseSensitive=True, leftValue="", typeValidation="loose", version=2), combinator="and",
                        conditions=[dict(id="w3", leftValue="={{ $('Refresh now (webhook)').isExecuted }}", rightValue=True, operator=dict(type="boolean", operation="true", singleValue=True))]),
        looseTypeValidation=True, options={})),
    node("Return summary", "n8n-nodes-base.respondToWebhook", 1.1, [1220, 100], dict(respondWith="json", responseBody="={{ $json }}", options={})),
    note("## C · Weekly refresh\nDrop the new DLD Transactions export into `desk/inbox/`. On Monday (or on demand) the pipeline service extracts it, reruns `run_all.py`, checks the tests, and commits facts.json + chart data to the public repo. Start the service with `python desk/pipeline_server.py`.", [-40, -280], 520, 220, 6),
], [("Every Monday 07:00", "Rerun the numbers"), ("Refresh now (webhook)", "Rerun the numbers"), ("Rerun the numbers", "Summarise + log"),
    ("Summarise + log", "Tell me on Telegram (optional)"), ("Tell me on Telegram (optional)", "Came from webhook?"), ("Came from webhook?", "Return summary", 0)])

# ---------- E: Errors ----------
ERR = r"""
const fs = require('fs'), path = require('path');
const e = $json;
const line = `${new Date().toISOString()} workflow="${e.workflow?.name}" node="${e.execution?.lastNodeExecuted}" error="${e.execution?.error?.message}" execution=${e.execution?.id}\n`;
fs.appendFileSync(path.join($env.DESK_DIR, 'errors.log'), line);
return [{ json: { logged: line.trim() } }];
"""
E = workflow("E", "Dubai Lead Desk · E · Errors", [
    node("When a desk workflow fails", "n8n-nodes-base.errorTrigger", 1, [0, 0]),
    node("Write to errors.log", "n8n-nodes-base.code", 2, [240, 0], code(ERR)),
    node("Alert on Telegram (optional)", "n8n-nodes-base.telegram", 1.2, [480, 0], dict(
        chatId="={{ $env.TELEGRAM_CHAT_ID }}", text="={{ 'Dubai Lead Desk error: ' + $json.logged }}", additionalFields=dict(appendAttribution=False)), disabled=True),
], [("When a desk workflow fails", "Write to errors.log"), ("Write to errors.log", "Alert on Telegram (optional)")], error=False)

for key, wf in dict(A=A, B=B, C=C, E=E, F=F).items():
    (OUT / f"{key}_{wf['name'].split(' · ')[-1].lower().replace(' ', '_')}.json").write_text(json.dumps(wf, indent=1, ensure_ascii=False), encoding="utf-8")

# the 90 scored cases: message + hidden answer (synthetic test data, safe to publish)
truth = json.loads((ROOT / "eval" / "specs_v2_truth.json").read_text())
msgs = json.loads((ROOT / "eval_blind" / "messages.json").read_text(encoding="utf-8")) + json.loads((ROOT / "eval_blind" / "hard_messages.json").read_text(encoding="utf-8"))
cases = [dict(id=m["id"], set="plain" if m["id"].startswith("E") else "stress", message=m["message"],
              name=m.get("name_raw", "Test buyer"), phone=m.get("phone_raw", "0500000000"), truth=truth[m["id"]]) for m in msgs if m["id"] in truth]
(HERE / "test_set.json").write_text(json.dumps(cases, indent=1, ensure_ascii=False), encoding="utf-8")
print("workflows:", sorted(p.name for p in OUT.iterdir()), "| test cases:", len(cases))
