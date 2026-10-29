"""Writes public/README.md for the public repo. Every number comes from site/facts.json and dash_data/validation.csv."""
import csv, json
from datetime import date
from pathlib import Path

F = json.loads(Path("site/facts.json").read_text(encoding="utf-8"))
V = list(csv.DictReader(open("dash_data/validation.csv", encoding="utf-8")))
FC, P, MK = F["forecast"], F["pace"], F["market"]
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

Who kept buying homes in Dubai since late February 2026? The answer comes from the Dubai Land Department's open records. A free n8n tool that answers buyer enquiries is built on it.

**Dashboard:** [{PAGES.replace('https://', '')}]({PAGES}) (one page, no login, works on a phone)
**Data to:** {F['data_to_label']}

![The dashboard](docs/screenshot.png)

## The question

A brokerage gets enquiries every day. It has to decide which ones get a fast reply and which need a senior agent. I wanted to know which buyers have been most active since late February, so that choice rests on data. Dubai publishes its property records openly, which made it possible to answer.

## What the data shows

- About {n(round(MK['sales_per_month_mar_sep'], -2))} homes sold a month from March to September. The third quarter had {n(MK['q3_sales'])} sales worth AED {MK['q3_value_aed_bn']} billion.
- Since 28 February, sales ran at about two-thirds of the usual pace: {n(F['sales_actual_post'])} registered against about {n(F['sales_expected_post'])}. The likely range is {P['low_pct']}% to {P['high_pct']}%. The pace was {P['march_pct']}% in March and {P['september_pct']}% in September.
- Homes under AED 1M were the steadiest part of the market, at about {P['under1m_pct']}% of their usual pace. Above AED 5M, about {P['over5m_pct']}%.
- Prices moved less than sales. Comparing the same buildings, JVC ready flats are about {abs(round(F['jvc_ready_price_change_pct']))}% below January and Dubai Marina about {abs(round(F['marina_ready_price_change_pct']))}%.
- Asking prices on the portals sit about {round(F['jvc_asking_premium_pct'])}% above recent sales in JVC and {round(F['marina_asking_premium_pct'])}% in Dubai Marina.
- Renting out still pays: gross rental yields on JVC flats are about {round(MK['jvc_yield_low_pct'])}%.
- A lot of new supply is on the way. JVC has {n(F['jvc_pipeline_units'])} flats sold off-plan and not yet handed over. That's about {round(F['jvc_pipeline_months'])} months of sales at {n(F['jvc_sales_per_month'])} a month.

**What I'd do with it** (a recommendation, not a measured result). {MK['under2m_share_pct']}% of sales were under AED 2M, so answer those enquiries fast and automatically. Give large purchases a senior agent from the first message. Check every budget against current DLD prices, refreshed each month.

## The lead desk

Five n8n workflows (n8n 2.42.5, self-hosted, free):

- **A · Lead desk**: reads an enquiry and checks the budget against DLD's recent sale prices. It sorts the lead into Hot, Warm or Cold, drafts a reply for an agent and logs it. Repeat enquiries from the same phone are merged.
- **F · Enquiry form**: a web form that feeds A.
- **B · Test harness**: sends 90 test enquiries through A and scores the result against answers A never sees.
- **C · Weekly refresh**: every Monday it picks up a new DLD export and reruns every number. Then it runs the tests and commits.
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

`run_all.py` goes from the raw DLD files to `site/facts.json`. Every number in the dashboard, this README and the posts comes from that one file. The tests fail if a headline number moves. They also check that the JavaScript desk reads every test message exactly as the Python version does. GitHub Actions runs all of this on every push (the badge at the top).

## How it was checked

My totals against figures other people published from the same DLD records: {verdicts['match']} match, {verdicts['close']} close, {verdicts['miss']} miss. The misses stay in, with the reason for each.

| Check | This analysis | Published | Source | Verdict |
|---|---|---|---|---|
{rows}

**Two checks anyone can run.** One is a one-minute comprehension test with five people outside property ([proof/comprehension_test.md](proof/comprehension_test.md)). The other is a sheet for one agent to sort 20 real enquiries blind against the desk ([proof/agent_blind_test.md](proof/agent_blind_test.md)). Results go here once they're done.

**A forecast you can check.** Dubai home sales in November 2026 should land between **{n(FC['forecast_low'])} and {n(FC['forecast_high'])}**. The usual pattern would expect about {n(round(FC['expected_without_war'], -2))}. The low end assumes the pace of recent weeks continues ({round(100 + FC['recent_gap_pct'])}% of usual). The high end assumes the average pace since 28 February ({round(100 + FC['whole_period_gap_pct'])}%). I'll check it against DLD's November records on {check_on}, and again on {date.fromisoformat(FC['recheck_on']).day} {date.fromisoformat(FC['recheck_on']):%B %Y}, because DLD can still add late registrations. If it lands outside the range, the model needs another look.

## Data

- **Dubai Land Department open data**: {n(F['sales_read'])} residential sales from {F['sales_read_from']} to {F['data_to']}, {n(F['leases_read'])} Ejari rental contracts for flats in JVC and Dubai Marina, DLD projects and valuations. Included in `data/dld/` (gzipped, unchanged).
- **Portal listings**: {F['listings_checked']} listings from Bayut and Property Finder, checked on 21 October 2026. Only totals are published (duplicate share, asking-price gap). The listings themselves are not in this repo.
- **Buyer posts from public forums**: used only to see how the desk handles real wording. Neither the posts nor any usernames are included.

## Limitations

- The "usual pattern" is a model of 2024 to early 2026 that allows for weekdays, seasons, Ramadan and Eid. It describes what happened after 28 February, not why.
- The range around the overall pace is wide. A simpler trend model gives {round(100 + F['war_gap_trend_model_pct'])}% of the usual pace instead of {P['overall_pct']}%.
- DLD registers a sale when it is recorded, sometimes weeks after the deal. The latest month covers only part of the month, and recent months may still rise a little.
- Asking prices come from one day's listings.
- The desk's test messages were written for the test.

## Licence

Code: MIT. The DLD files in `data/dld/` are Dubai Land Department open data, republished with attribution under its own terms.

Independent analysis by Mithun Cyriac, made possible by the Dubai Land Department's open data. Built with Python, statsmodels, n8n and an AI model. Not financial advice.
"""
Path("public/README.md").write_text(readme, encoding="utf-8")
print("public/README.md", len(readme.split()), "words")
