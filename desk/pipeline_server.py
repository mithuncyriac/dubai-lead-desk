"""The small Python service n8n's weekly refresh calls (Workflow C). Standard library only.

POST /refresh
  1. If a new DLD export is waiting in desk/inbox/ (the two full-history Transactions CSV parts), extract 2024+ residential sales from it.
  2. Rerun every number: run_all.py.
  3. Compare the headline numbers with the previous facts.json and, when they moved, record the new values as the locked ones.
  4. Run the tests, export the public copy and commit it (and push, if the public repo has a remote).
  Returns a JSON summary: what was picked up, what changed, test result, commit.
GET /health  -> {"ok": true}
Run: python desk/pipeline_server.py   (listens on 127.0.0.1:8765)
"""
import json, shutil, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "desk" / "inbox"
LOCK = ROOT / "tests" / "locked_headlines.json"
REPO = ROOT / "public-repo"
PY = sys.executable


def sh(args, cwd=ROOT, timeout=1200):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def locked_view(facts):
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    return {k: facts["forecast"][k] if k.startswith("forecast_") else facts[k] for k in lock}


def refresh():
    out = dict(new_export=[], changed={}, tests=None, commit=None, pushed=False)
    INBOX.mkdir(parents=True, exist_ok=True)
    parts = sorted(p for p in INBOX.glob("*.csv"))
    if parts:
        code, log = sh([PY, "scripts/extract_history.py", *map(str, parts)])
        if code:
            return dict(out, error="could not read the new export", log=log)
        done = INBOX / "done"
        done.mkdir(exist_ok=True)
        for p in parts:
            shutil.move(str(p), done / p.name)
        out["new_export"] = [p.name for p in parts]

    before = json.loads((ROOT / "site" / "facts.json").read_text(encoding="utf-8"))
    code, log = sh([PY, "run_all.py"])
    if code:
        return dict(out, error="run_all.py failed", log=log)
    after = json.loads((ROOT / "site" / "facts.json").read_text(encoding="utf-8"))
    old, new = locked_view(before), locked_view(after)
    out["changed"] = {k: [old[k], new[k]] for k in new if old[k] != new[k]}
    out["data_to"] = after["data_to"]
    if out["changed"]:   # a deliberate refresh: the new numbers become the locked ones
        LOCK.write_text(json.dumps(new, indent=1, ensure_ascii=False), encoding="utf-8")

    code, log = sh([PY, "-m", "pytest", "-q", "tests"])
    out["tests"] = "passed" if code == 0 else "FAILED"
    if code:
        return dict(out, log=log)

    if (ROOT / "scripts" / "export_repo.py").exists():
        code, log = sh([PY, "scripts/export_repo.py"])
        if code:
            return dict(out, error="export failed", log=log)
        if (REPO / ".git").exists():
            sh(["git", "add", "-A"], cwd=REPO)
            msg = f"Data to {after['data_to']}: " + (", ".join(f"{k} {a}→{b}" for k, (a, b) in out["changed"].items()) or "numbers unchanged")
            code, log = sh(["git", "commit", "-m", msg], cwd=REPO)
            if code == 0:
                out["commit"] = sh(["git", "rev-parse", "--short", "HEAD"], cwd=REPO)[1].strip()
                if sh(["git", "remote"], cwd=REPO)[1].strip():
                    out["pushed"] = sh(["git", "push"], cwd=REPO)[0] == 0
            else:
                out["commit"] = "nothing to commit"
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/refresh":
            return self._send(404, {"error": "not found"})
        try:
            res = refresh()
            self._send(500 if res.get("error") or res.get("tests") == "FAILED" else 200, res)
        except Exception as e:   # surfaced to n8n's error workflow
            self._send(500, {"error": repr(e)})


if __name__ == "__main__":
    import os
    host = os.environ.get("PIPELINE_HOST", "127.0.0.1")     # 0.0.0.0 inside Docker
    print(f"pipeline listening on http://{host}:8765")
    ThreadingHTTPServer((host, 8765), Handler).serve_forever()
