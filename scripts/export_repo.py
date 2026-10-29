"""Copies the publishable part of this project into public-repo/ (an allow-list: anything not named here stays private).

Never exported: raw portal listings and anything listing-level (URLs, buildings, agencies), forum post text,
the scraper, CVs and application material. DLD open data is exported gzipped, with attribution.
The dashboard is copied to docs/index.html for GitHub Pages. public-repo/.git is left untouched.
"""
import gzip, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public-repo"

FILES = [
    "run_all.py", "requirements.txt", "docker-compose.yml",
    *[f"scripts/{s}.py" for s in ["dld_analysis", "war_attribution", "forecast", "build_facts", "build_site", "build_readme", "export_repo",
                                  "audit", "stale_offplan", "supply", "build_dash_data", "build_v3_data", "validation",
                                  "evaluate", "evaluate_hard", "simulate_desk", "tier_shift", "rule_parser", "real_agreement",
                                  "make_specs", "make_hard_specs", "extract_history"]],
    "tests/test_facts.py", "tests/test_desk_parity.py", "tests/locked_headlines.json",
    "desk/desk_logic.js", "desk/build_workflows.py", "desk/test_set.json", "desk/pipeline_server.py", "desk/start-n8n.sh",
    "desk/Dockerfile.pipeline", "desk/SETUP.md", "desk/DEMO_SCRIPT.md", "desk/tier_csv.js", "scripts/build_posts.py", "scripts/build_carousel.py", "scripts/build_story.py",
    "proof/comprehension_test.md", "proof/agent_blind_test.md", "proof/agent_sheet.csv",
    *[f"desk/workflows/{p.name}" for p in sorted((ROOT / "desk" / "workflows").glob("*.json"))],
    "site/template.html", "site/design_tokens.json", "site/index.html", "site/facts.json", "site/chart_data.json", "site/desk_prices.json",
    "data/war_results.json", "data/dld_results.json", "data/forecast.json",
    *[f"eval/{n}" for n in ["specs.json", "hard_specs.json", "specs_v2_truth.json", "ref_v2.json", "dups.json", "eval_results.json",
                            "eval_results.csv", "hard_results.json", "desk_results.json", "desk_log.json", "tier_shift.json", "v2_results.json",
                            "scores_run1.json", "scores_run2.json", "scores_run3.json", "scores_hard.json", "scores_variants.json"]],
    *[f"eval_blind/{n}" for n in ["messages.json", "hard_messages.json", "variants.json", "v2_messages.json", "rubric.md", "rubric_v2.md"]],
    *[f"eval_blind/out/{n}" for n in ["scores_run1.json", "scores_run2.json", "scores_run3.json", "scores_hard.json", "scores_variants.json", "scores_v2.json"]],
]
# datasets the dashboard and facts are built from; listing-level and forum-text tables are left out
PRIVATE_DATASETS = {"same_unit.csv", "stale_offplan.csv", "examples.csv"}
DLD_RAW = ["transactions.csv", "rents_a.csv", "rents_b.csv", "rents_c.csv", "hist_sales_2024on.csv", "projects.csv", "valuations.csv"]
EXTRA = {"README.md": "public/README.md", "LICENSE": "public/LICENSE", ".gitignore": "public/gitignore",
         ".github/workflows/check.yml": "public/check.yml", "CITATION.cff": "public/CITATION.cff", "docs/banner-1-findings.png": "public/banners/banner-1-findings.png",
         "docs/screenshot.png": "public/shots/dashboard.png"}


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    OUT.mkdir(exist_ok=True)
    for p in OUT.iterdir():                      # start clean, keep the git history
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    missing = []
    for f in FILES:
        (copy(ROOT / f, OUT / f) if (ROOT / f).exists() else missing.append(f))
    for p in sorted((ROOT / "dash_data").glob("*.csv")):
        if p.name not in PRIVATE_DATASETS:
            copy(p, OUT / "dash_data" / p.name)
    for name in DLD_RAW:
        dst = OUT / "data" / "dld" / (name + ".gz")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(ROOT / "data" / "dld" / name, "rb") as fi, gzip.GzipFile(dst, "wb", mtime=0) as fo:   # mtime=0: same bytes every export
            shutil.copyfileobj(fi, fo)
    for dst, src in EXTRA.items():
        (copy(ROOT / src, OUT / dst) if (ROOT / src).exists() else missing.append(src))
    copy(ROOT / "site" / "index.html", OUT / "docs" / "index.html")
    for f in (ROOT / "public" / "story").glob("*"):      # the Medium explainer as a page, for Medium's "Import a story"
        copy(f, OUT / "docs" / "story" / f.name)
    # guard: nothing private slipped through
    leaks = [str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file() and ".git" not in p.parts and (".secrets" in p.parts or p.name.startswith("publish_") or 
        p.name in {"pf_sale.csv", "pf_rent.csv", "listings_audit.csv", "audit_results.json", "real_messages.json", "real_posts.json",
                   "scores_real.json", "real_disagreements.json", "pull_pf.py"} or p.name in PRIVATE_DATASETS)]
    assert not leaks, f"private files in export: {leaks}"
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file() and ".git" not in p.parts)
    print(f"public-repo: {sum(1 for p in OUT.rglob('*') if p.is_file() and '.git' not in p.parts)} files, {size / 1e6:.1f} MB",
          "| not found yet:", missing or "none")


if __name__ == "__main__":
    main()
