"""One command from the raw DLD files to every number: python run_all.py

Runs the analysis scripts in dependency order, then writes site/facts.json (every headline number) and
site/chart_data.json (what the dashboard draws). The blind AI runs are recorded inputs (eval/, eval_blind/):
they are scored again here, not re-asked.
  --skip-model   reuse data/*.json and only rebuild the datasets and facts (seconds instead of minutes)
"""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = [
    "dld_analysis.py",      # raw DLD sales + Ejari -> data/dld_results.json
    "war_attribution.py",   # interrupted time series, segments, price index -> data/war_results.json
    "forecast.py",          # November forecast from the same model -> data/forecast.json
    "audit.py",             # portal listings (kept private; aggregates only) -> data/audit_results.json
]
DATASETS = [
    "evaluate.py", "evaluate_hard.py", "simulate_desk.py", "tier_shift.py",   # score the recorded blind runs
    "build_dash_data.py", "build_v3_data.py", "validation.py",
    "stale_offplan.py", "supply.py", "real_agreement.py",
    "build_facts.py",       # -> site/facts.json + site/chart_data.json
    "build_site.py",        # -> site/index.html, the dashboard, with the new numbers
    "build_readme.py",      # -> public/README.md
]


PRIVATE = {"audit.py", "stale_offplan.py"}     # need the raw portal listings, which are never published
HAVE_LISTINGS = (ROOT / "data" / "pf_sale.csv").exists()


def run(script):
    if script in PRIVATE and not HAVE_LISTINGS:
        print(f"--  {script:<22} skipped: raw listings are private; using the committed aggregates")
        return
    t = time.time()
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAILED {script}\n{r.stdout}\n{r.stderr}")
    print(f"ok  {script:<22} {time.time() - t:5.1f}s")


if __name__ == "__main__":
    datasets = DATASETS
    if not HAVE_LISTINGS:   # public copy: rerun the DLD model, rebuild facts from the committed datasets
        print("public mode: raw listings and forum posts are private, so the committed dash_data/ is reused")
        datasets = ["build_facts.py", "build_site.py"]
    for s in ([] if "--skip-model" in sys.argv else MODEL) + datasets:
        run(s)
    print("done: site/facts.json")
