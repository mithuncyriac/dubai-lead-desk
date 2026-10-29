"""The JavaScript desk (n8n + dashboard) must read every test message exactly as scripts/rule_parser.py does.
Needs Node.js on PATH; skipped without it."""
import json, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def messages():
    out = {}
    for f in ["messages.json", "hard_messages.json", "variants.json", "real_messages.json", "v2_messages.json"]:
        p = ROOT / "eval_blind" / f
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else [dict(id=k, message=v) for k, v in data.items()]
            for m in items:
                text = m.get("message") or m.get("text")
                if isinstance(text, str):
                    out[f"{f}:{m.get('id')}"] = text
    return out


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python(monkeypatch):
    monkeypatch.chdir(ROOT)
    from rule_parser import score
    msgs = messages()
    prices = json.loads((ROOT / "eval" / "ref_v2.json").read_text())
    js = """
const D = require(process.argv[1]); const fs = require('fs');
const {msgs, prices} = JSON.parse(fs.readFileSync(0, 'utf8')); const out = {};
for (const [k, t] of Object.entries(msgs)) { const f = D.parse(t, {y: 2026, m: 10}); out[k] = {...f, tier: D.tier(f, prices).tier}; }
process.stdout.write(JSON.stringify(out));"""
    r = subprocess.run(["node", "-e", js, str(ROOT / "desk" / "desk_logic.js")], input=json.dumps(dict(msgs=msgs, prices=prices)),
                       capture_output=True, text=True, encoding="utf-8", check=True)
    got = json.loads(r.stdout)
    keys = ["area", "beds", "budget_aed", "timeline_months", "finance", "browsing", "tier"]
    diffs = {k: {f: (score(t)[f], got[k][f]) for f in keys if score(t)[f] != got[k][f]} for k, t in msgs.items()}
    diffs = {k: v for k, v in diffs.items() if v}
    assert len(msgs) >= 150, len(msgs)
    assert not diffs, f"{len(diffs)} of {len(msgs)} messages differ (python, js): {dict(list(diffs.items())[:5])}"
