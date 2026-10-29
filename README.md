# Dubai Lead Desk

[![Rerun the numbers](https://github.com/mithuncyriac/dubai-lead-desk/actions/workflows/check.yml/badge.svg)](https://github.com/mithuncyriac/dubai-lead-desk/actions/workflows/check.yml) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23759151.svg)](https://doi.org/10.5281/zenodo.23759151)

Who kept buying homes in Dubai since late February 2026? The answer comes from the Dubai Land Department's open records. A free n8n tool that answers buyer enquiries is built on it.

**Dashboard:** [mithuncyriac.github.io/dubai-lead-desk/](https://mithuncyriac.github.io/dubai-lead-desk/) (one page, no login, works on a phone)
**Data to:** 19 Oct 2026

![The dashboard](docs/screenshot.png)

## The question

A brokerage gets enquiries every day. It has to decide which ones get a fast reply and which need a senior agent. I wanted to know which buyers have been most active since late February, so that choice rests on data. Dubai publishes its property records openly, which made it possible to answer.

## What the data shows

- About 11,600 homes sold a month from March to September. The third quarter had 34,047 sales worth AED 67.9 billion.
- Since late February, sales ran at about two-thirds of the usual pace: 87,052 registered against about 137,260. The likely range is 52% to 77%. The pace was 68% in March and 54% in September.
- Homes under AED 1M were the steadiest part of the market, at about 80% of their usual pace. Above AED 5M, about 48%.
- Prices moved less than sales. Comparing the same buildings, JVC ready flats are about 8% below January and Dubai Marina about 5%.
- Asking prices on the portals sit about 7% above recent sales in JVC and 9% in Dubai Marina.
- Renting out still pays: gross rental yields on JVC flats are about 7%.
- A lot of new supply is on the way. JVC has 19,756 flats sold off-plan and not yet handed over. That's about 26 months of sales at 767 a month.

**What I'd do with it** (a recommendation, not a measured result). 70% of sales were under AED 2M, so answer those enquiries fast and automatically. Give large purchases a senior agent from the first message. Check every budget against current DLD prices, refreshed each month.

## The lead desk

Five n8n workflows (n8n 2.42.5, self-hosted, free):

- **A · Lead desk**: reads an enquiry and checks the budget against DLD's recent sale prices. It sorts the lead into Hot, Warm or Cold, drafts a reply for an agent and logs it. Repeat enquiries from the same phone are merged.
- **F · Enquiry form**: a web form that feeds A.
- **B · Test harness**: sends 90 test enquiries through A and scores the result against answers A never sees.
- **C · Weekly refresh**: every Monday it picks up a new DLD export and reruns every number. Then it runs the tests and commits.
- **E · Errors**: logs any failure.

The version here reads enquiries with rules, so it costs nothing to run. On the 90 test enquiries it gets 77 right (86%). It misses wording it has no rule for, like numbers written as words or "a year and a half". An AI model reading the same messages blind got 90/90, but that needs a paid API key. The test messages were written for the test; they are not real buyers.

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

My totals against figures other people published from the same DLD records: 6 match, 3 close, 3 miss. The misses stay in, with the reason for each.

| Check | This analysis | Published | Source | Verdict |
|---|---|---|---|---|
| Q3 2026 residential deals | 34,047 | 34,000 | Cavendish Maxwell via The National | **match** |
| Q3 2026 deals, change vs Q3 2025 | −36.5% | −38.0% | Cavendish Maxwell via The National | **match** |
| Q3 2026 sales value, change vs Q3 2025 | −46.4% | −47.0% | Cavendish Maxwell via The National | **match** |
| Q3 2026 sales value, AED bn | AED 67.9 bn | AED 72.6 bn | Cavendish Maxwell via The National | **miss**: level differs: their total likely includes procedures we exclude (e.g. land and building sales classed outside 'Residential') |
| Jan–Sep 2026 deals | 110,672 | 112,580 | Cavendish Maxwell via The National | **match** |
| Jan–Sep 2026 deals, change vs 2025 | −19.9% | −23.0% | Cavendish Maxwell via The National | **close**: small gap; their 2025 base may include late-registered deals our export dates differently |
| Monthly sales Mar–Sep vs Jan–Feb 2026 | −22.2% | −26.0% | S&P Global Ratings (DLD data) | **close**: S&P counts all sales incl. commercial; we count residential only |
| First 12 days of March, change vs 2025 | −6.4% | −37.0% | Goldman Sachs (UAE-wide) | **miss**: miss: Goldman covers the whole UAE with an unpublished method; March 2025 was Ramadan, which lowers our comparison base |
| Price move in March 2026 (ready flats, JVC) | +2.0% | −5.9% | ValuStrat Price Index | **miss**: miss in timing: ValuStrat is valuation-based and reacts at once; March registrations were mostly deals agreed before 28 February. Our index moves from May |
| Price move Feb–Oct 2026 (ready flats, JVC) | −5.8% | −10.0% | ValuStrat (cumulative since late Feb) | **close**: same direction, smaller: ValuStrat covers all Dubai incl. prime villas |
| JVC average flat price, AED | AED 1,070,795 | AED 1,075,878 | Bayut (DLD 12-month average) | **match** |
| Marina flat sales per year | 2,197 | 2,205 | Bayut (DLD 12-month count) | **match** |

**Two checks anyone can run.** One is a one-minute comprehension test with five people outside property ([proof/comprehension_test.md](proof/comprehension_test.md)). The other is a sheet for one agent to sort 20 real enquiries blind against the desk ([proof/agent_blind_test.md](proof/agent_blind_test.md)). Results go here once they're done.

**A forecast you can check.** Dubai home sales in November 2026 should land between **9,800 and 11,600**. The usual pattern would expect about 18,400. The low end assumes the pace of recent weeks continues (53% of usual). The high end assumes the average pace since late February (63%). I'll check it against DLD's November records on 7 December 2026, and again on 7 January 2027, because DLD can still add late registrations. If it lands outside the range, the model needs another look.

## Data

- **Dubai Land Department open data**: 472,404 residential sales from 2024-01-01 to 2026-10-19, 46,023 Ejari rental contracts for flats in JVC and Dubai Marina, DLD projects and valuations. Included in `data/dld/` (gzipped, unchanged).
- **Portal listings**: 214 listings from Bayut and Property Finder, checked on 21 October 2026. Only totals are published (duplicate share, asking-price gap). The listings themselves are not in this repo.
- **Buyer posts from public forums**: used only to see how the desk handles real wording. Neither the posts nor any usernames are included.

## Limitations

- The "usual pattern" is a model of 2024 to early 2026 that allows for weekdays, seasons, Ramadan and Eid. It describes what happened after 28 February, not why.
- The range around the overall pace is wide. A simpler trend model gives 65% of the usual pace instead of 63%.
- DLD registers a sale when it is recorded, sometimes weeks after the deal. The latest month covers only part of the month, and recent months may still rise a little.
- Asking prices come from one day's listings.
- The desk's test messages were written for the test.

## Cite

Cyriac, M. (2026). *Dubai Lead Desk: who kept buying homes in Dubai since 28 February 2026* (v1.0). Zenodo. https://doi.org/10.5281/zenodo.23759152

The November forecast was written down and archived before the data existed: [Zenodo, v1.0](https://doi.org/10.5281/zenodo.23759152) and the [Internet Archive](https://web.archive.org/web/20261029083353/https://mithuncyriac.github.io/dubai-lead-desk/), both 2026-10-29.

## Licence

Code: MIT. The DLD files in `data/dld/` are Dubai Land Department open data, republished with attribution under its own terms.

Independent analysis by Mithun Cyriac, made possible by the Dubai Land Department's open data. Built with Python, statsmodels, n8n and an AI model. Not financial advice.
