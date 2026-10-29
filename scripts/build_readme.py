"""Writes public/README.md for the public repo. Every number comes from site/facts.json and dash_data/validation.csv."""
import csv, json
from datetime import date
from pathlib import Path

F = json.loads(Path("site/facts.json").read_text(encoding="utf-8"))
V = list(csv.DictReader(open("dash_data/validation.csv", encoding="utf-8")))
FC = F["forecast"]
USER, REPO = "mithuncyriac", "dubai-lead-desk"
PAGES = f"https://{USER}.github.io/{REPO}/"
pct = lambda v: ("−" if v < 0 else "+") + f"{abs(round(v))}%"
n = lambda v: f"{int(v):,}"
share = lambda gap: f"{round(100 + gap)}%"


def unit(v, u):
    v = float(v)
    return f"{v:+.1f}%".replace("-", "−") if u == "pts" else f"AED {v:g} bn" if u == "AED bn" else f"AED {v:,.0f}" if u == "AED" else f"{v:,.0f}"


rows = "\n".join(f"| {r['check']} | {unit(r['ours'], r['unit'])} | {unit(r['published'], r['unit'])} | {r['source']} | **{r['verdict']}**"
                 + ("" if r["verdict"] == "match" else f": {r['why']}") + " |" for r in V)
verdicts = {k: sum(r["verdict"] == k for r in V) for k in ("match", "close", "miss")}
check_on = f"{date.fromisoformat(FC['check_on']).day} {date.fromisoformat(FC['check_on']):%B %Y}"

readme = f"""# Dubai Lead Desk

[![Rerun the numbers](https://github.com/{USER}/{REPO}/actions/workflows/check.yml/badge.svg)](https://github.com/{USER}/{REPO}/actions/workflows/check.yml)

Who kept buying homes in Dubai after 28 February 2026, worked out from the Dubai Land Department's own records, and a free lead desk in n8n built on the answer.

**Dashboard:** [{PAGES.replace('https://', '')}]({PAGES}) (one page, no login, works on a phone)
**Data to:** {F['data_to_label']}

![The dashboard](docs/screenshot.png)

## The problem

Since the war began on 28 February, fewer people have been buying homes in Dubai. A brokerage still gets enquiries every day, though, and it has to decide which ones get a fast reply and which ones need a senior agent. I wanted to know which buyers were still active, so that decision could rest on data rather than on a feeling.

## What the data shows

- Home sales since 28 February ran **{abs(round(F['war_gap_pct']))}%** below what the usual pattern predicted ({n(F['sales_actual_post'])} registered against about {n(F['sales_expected_post'])} expected). The likely range is {pct(F['war_gap_high_pct'])} to {pct(F['war_gap_low_pct'])}.
- The gap is getting wider: {pct(F['gap_march_pct'])} in March, {pct(F['gap_september_pct'])} in September.
- The cheaper the home, the smaller the drop. Under AED 1M, sales run at about {share(F['band_under1m_pct'])} of the usual pace. Above AED 5M, about {share(F['band_over5m_pct'])}.
- Prices moved far less than sales. Ready flats in JVC are {abs(round(F['jvc_ready_price_change_pct']))}% cheaper than in January, comparing sales in the same buildings, and in Dubai Marina {abs(round(F['marina_ready_price_change_pct']))}% cheaper.
- Asking prices on the portals sit above what homes sold for: about {round(F['jvc_asking_premium_pct'])}% in JVC and {round(F['marina_asking_premium_pct'])}% in Dubai Marina.
- JVC has {n(F['jvc_pipeline_units'])} off-plan flats still waiting for handover. At the current pace of {n(F['jvc_sales_per_month'])} sales a month, that is about {round(F['jvc_pipeline_months'])} months of sales.

**What I'd do with it** (a recommendation, not a measured result): answer the many smaller enquiries fast and automatically, give the rare large ones to a senior agent from the first message, and check every budget against post-war prices that are refreshed each month.

## The lead desk

Five n8n workflows (n8n 2.42.5, self-hosted, free):

- **A · Lead desk**: reads an enquiry, checks the budget against DLD's recent sale prices, sorts it into Hot, Warm or Cold, drafts a reply for an agent to approve, and logs it. Repeat enquiries from the same phone are merged.
- **F · Enquiry form**: a web form that feeds A.
- **B · Test harness**: sends 90 test enquiries through A and scores the result against answers A never sees.
- **C · Weekly refresh**: every Monday, picks up a new DLD export, reruns every number, runs the tests and commits.
- **E · Errors**: logs any failure.

The version here reads enquiries with rules, so it costs nothing to run. On the 90 test enquiries it gets {round(F['rules_only_pass_pct'] * 0.9)} right ({round(F['rules_only_pass_pct'])}%). It misses wording it has no rule for, like numbers written as words or "a year and a half". An AI model reading the same messages blind got {F['desk_postwar_pass']}, but that needs a paid API key. The test messages were written for the test; they are not real buyers.

Setup and a demo script: [desk/SETUP.md](desk/SETUP.md), [desk/DEMO_SCRIPT.md](desk/DEMO_SCRIPT.md).

## Run it yourself

Python 3.14, about a minute:

```bash
pip install -r requirements.txt
gunzip -k data/dld/*.csv.gz
python run_all.py
python -m pytest tests
```

`run_all.py` goes from the raw DLD files to `site/facts.json`, the single file every number in the dashboard, this README and the posts comes from. The tests fail if a headline number moves, and they check that the JavaScript desk reads every test message exactly as the Python version does. GitHub Actions runs all of this on every push (the badge at the top).

## How it was checked

My totals against figures other people published from the same DLD records: {verdicts['match']} match, {verdicts['close']} close, {verdicts['miss']} miss. The misses stay in, with the reason.

| Check | This analysis | Published | Source | Verdict |
|---|---|---|---|---|
{rows}

**Two checks anyone can run.** A one-minute comprehension test with five people who don't work in property ([proof/comprehension_test.md](proof/comprehension_test.md)), and a sheet for one agent to sort 20 real enquiries blind against the desk ([proof/agent_blind_test.md](proof/agent_blind_test.md)). Results go here once they're done.

**A forecast you can check.** Dubai home sales in November 2026 should land between **{n(FC['forecast_low'])} and {n(FC['forecast_high'])}**. The usual pattern would expect about {n(round(FC['expected_without_war'], -2))}. The low end assumes the gap of the latest weeks holds ({pct(FC['recent_gap_pct'])}), the high end the average since 28 February ({pct(FC['whole_period_gap_pct'])}). I'll check it against DLD's November records on {check_on}. If it misses, the model is missing something.

## Data

- **Dubai Land Department open data**: {n(F['sales_read'])} residential sales from {F['sales_read_from']} to {F['data_to']}, {n(F['leases_read'])} Ejari rental contracts for flats in JVC and Dubai Marina, DLD projects and valuations. Included in `data/dld/` (gzipped, unchanged).
- **Portal listings**: {F['listings_checked']} listings from Bayut and Property Finder, checked on 21 October 2026. Only totals are published (duplicate share, asking-price gap). The listings themselves are not in this repo.
- **Buyer posts from public forums**: used only to see how the desk handles real wording. Neither the posts nor any usernames are included.

## Limitations

- The "usual pattern" is a model of 2024 to early 2026 that allows for weekdays, seasons, Ramadan and Eid. It cannot separate the war from anything else that changed after 28 February, so the gap is "below the usual pattern", not "caused by" one thing.
- The range around the main figure is wide. A simpler trend model gives {pct(F['war_gap_trend_model_pct'])} instead of {pct(F['war_gap_pct'])}.
- DLD registers a sale when it is recorded, sometimes weeks after the deal. The latest month covers only part of the month, and recent months may still rise a little.
- Asking prices come from one day's listings.
- The desk's test messages were written for the test.

## Licence

Code: MIT. The DLD files in `data/dld/` are Dubai Land Department open data, republished with attribution under its own terms.

Independent analysis by Mithun Cyriac. Built with Python, statsmodels, n8n and an AI model. Not financial advice.
"""
Path("public/README.md").write_text(readme, encoding="utf-8")
print("public/README.md", len(readme.split()), "words")
