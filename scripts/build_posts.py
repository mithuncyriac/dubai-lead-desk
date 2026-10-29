"""Writes the LinkedIn post, its first comment and the Medium explainer into posts/. Every number comes from site/facts.json
(and dash_data/validation.csv for the checks), so a data refresh rewrites them too."""
import csv, json
from datetime import date
from pathlib import Path

F = json.loads(Path("site/facts.json").read_text(encoding="utf-8"))
V = list(csv.DictReader(open("dash_data/validation.csv", encoding="utf-8")))
FC, P, M = F["forecast"], F["pace"], F["market"]
OUT = Path("posts")
OUT.mkdir(exist_ok=True)
PAGES, REPO = "https://mithuncyriac.github.io/dubai-lead-desk/", "https://github.com/mithuncyriac/dubai-lead-desk"
REL = json.loads(Path("site/release.json").read_text(encoding="utf-8"))

a = lambda v: abs(round(v))                       # -7.9 -> 8
n = lambda v: f"{int(v):,}"
d = lambda iso: f"{date.fromisoformat(iso).day} {date.fromisoformat(iso):%B %Y}"
verdicts = {k: sum(r["verdict"] == k for r in V) for k in ("match", "close", "miss")}
rules_right = round(F["rules_only_pass_pct"] * 0.9)
months = round(F["jvc_pipeline_months"])
per_month = n(round(M["sales_per_month_mar_sep"], -2))
yield_jvc = round(M["jvc_yield_low_pct"])

linkedin = f"""Since 28 February, Dubai home sales have run at about {P['overall_pct']}% of their usual pace (likely {P['low_pct']}–{P['high_pct']}%). "Usual" means what past years' patterns predict. That is still about {per_month} homes a month.

The pace held best at the lower end. Homes under AED 1M kept about {P['under1m_pct']}% of their usual pace; above AED 5M, about {P['over5m_pct']}%. In the same buildings, JVC ready flats are about {a(F['jvc_ready_price_change_pct'])}% below January. Asking prices sit about {round(F['jvc_asking_premium_pct'])}% above recent sales.

All of it comes from the Dubai Land Department's open data: {n(F['sales_read'])} sales records, to {F['data_to_label']}.

For a brokerage, {M['under2m_share_pct']}% of sales were under AED 2M, so a fast first reply matters. I built a small, free tool in n8n for that. It reads each buyer enquiry, checks the budget against what homes sold for, and drafts a reply an agent approves.

My November forecast: {n(FC['forecast_low'])} to {n(FC['forecast_high'])} sales, against a usual November of about {n(round(FC['expected_without_war'], -2))}. First check on {date.fromisoformat(FC['check_on']).day} December.

Dashboard, code and method in the first comment.

#Dubai #RealEstate #DataAnalysis #n8n #Automation
"""

comment = f"""Dashboard (one page, works on a phone): {PAGES}
Code, data and every check: {REPO}
The longer write-up on Medium: [paste the Medium link here]

About the slides: eight pages of charts from DLD data. They show the pace of sales by month and by price, and prices in the same buildings. Then new homes to come in JVC, the lead desk and the November forecast.

Source: Dubai Land Department open data, to {F['data_to_label']}. Independent analysis, not financial advice.
"""

medium = f"""# Who kept buying homes in Dubai since late February?

*What {n(F['sales_read'])} Dubai Land Department sales records show, and the small tool I built from them. Data to {F['data_to_label']}.*

[Image: carousel slide 1, "Who kept buying homes in Dubai since late February?"]

Dubai publishes its property records openly. Every registered sale, every Ejari rental contract, every project. Few cities make that possible. I wanted to use it to answer one plain question. Since late February, who has kept buying homes, and at what pace?

Market reports give you a headline number, usually a quarter late. I wanted it month by month and split by price, straight from the records. So I took every registered home sale since January 2024: {n(F['sales_read'])} of them. I added {n(F['leases_read'])} Ejari rental contracts and DLD's lists of projects and valuations.

Here's what I found, and what I'd do with it.

## About two-thirds of the usual pace

From March to September, about {per_month} homes sold in Dubai each month. In the third quarter alone there were {n(M['q3_sales'])} sales worth AED {M['q3_value_aed_bn']} billion.

To judge the pace fairly, you can't just compare this year with last. Sales move with the seasons, with Ramadan and Eid, and with the day of the week. So I fitted a model to the usual pattern, from January 2024 to February 2026. Then I compared each month since with what that pattern would expect.

Since 28 February, {n(F['sales_actual_post'])} sales were registered, against about {n(F['sales_expected_post'])} in the usual pattern. That's about two-thirds of the usual pace, likely somewhere between {P['low_pct']}% and {P['high_pct']}%. The pace was {P['march_pct']}% in March and {P['september_pct']}% in September.

[Image: carousel slide 2, monthly sales against the usual pattern]

## Everyday buyers were the steadiest

Split the same sales by price and the picture gets clearer:

- Under AED 1M: about {P['under1m_pct']}% of the usual pace
- AED 1M to 2M: about {P['1to2m_pct']}%
- AED 2M to 5M: about {P['2to5m_pct']}%
- Above AED 5M: about {P['over5m_pct']}%

Homes under AED 1M, the ones most first-time buyers look at, held their pace best. Larger purchases are taking longer.

[Image: carousel slide 3, sales by price band]

## Prices moved less than sales

A simple average price can mislead. If fewer large apartments sell, the average goes down even when nothing got cheaper. So I compared sales within the same buildings over time. On that basis, ready flats in JVC are about {a(F['jvc_ready_price_change_pct'])}% below their January level, and in Dubai Marina about {a(F['marina_ready_price_change_pct'])}%.

Asking prices haven't fully caught up. The listings I checked on Bayut and Property Finder asked about {round(F['jvc_asking_premium_pct'])}% more than recent DLD sales in JVC. In Dubai Marina it was about {round(F['marina_asking_premium_pct'])}%.

## Renting out still pays

I matched Ejari leases with DLD sale prices since 28 February. A JVC flat earns a gross rental yield of about {yield_jvc}% a year. In Dubai Marina it's between {round(M['marina_yield_low_pct'])}% and {round(M['marina_yield_high_pct'])}%.

## A lot of new supply is on the way

JVC has {n(F['jvc_pipeline_units'])} flats that were sold off-plan since 2024 and haven't been handed over yet. At the current pace of {n(F['jvc_sales_per_month'])} sales a month, that's about {months} months of sales. Buyers can take their time.

## What this means if you're buying your first home

This is my reading, not advice, but here's what I'd take from it:

1. Start from what homes actually sold for, not the asking price. DLD's records are public.
2. Under AED 1M, expect competition. Those homes still sell at about {P['under1m_pct']}% of their usual pace.
3. With a bigger budget, you probably have more room to negotiate than you'd think.
4. Prices have moved less than sales, so there's time to compare.
5. In JVC, a lot of new supply is on the way, so compare ready and off-plan before you commit.

## What it means for a brokerage, and the tool I built

If I ran a brokerage, I'd notice that {M['under2m_share_pct']}% of sales since February were under AED 2M. Those buyers expect a quick answer. The rarer large purchases deserve a senior agent from the first message. That's a recommendation, not a measured result. Whether faster replies win more deals is something a brokerage would have to test.

So I built a small lead desk to try the idea. It runs in n8n, on my laptop, for free. An enquiry comes in by web form or message. The desk reads the area, bedrooms, budget, timing and how they're paying. It checks the budget against DLD's recent sale prices for that kind of home. Then it sorts the lead into Hot, Warm or Cold and drafts a first reply. An agent approves the reply before anything goes out. If the same person writes in again with their number written differently, it merges the two.

I tested it on 90 enquiries written for the test. Thirty were built to trip it up, and the answers were hidden from the desk. The free version, which reads enquiries with plain rules, got {rules_right} of 90 right. It stumbles on wording it has no rule for, like numbers written as words. An AI model reading the same messages blind got {F['desk_postwar_pass']}, but that version needs a paid API key. I'd rather show the free one honestly than oversell the paid one.

One detail I liked. Checking budgets against current prices, not older averages, changed the tier of {F['tier_changes']} of the 90 test leads. Those are exactly the leads an agent might otherwise misjudge.

[Image: screenshot of the n8n lead desk]

## A forecast you can check

Hindsight is easy, so here's something that can be wrong. For November 2026, I expect between {n(FC['forecast_low'])} and {n(FC['forecast_high'])} home sales in Dubai. The usual pattern alone would expect about {n(round(FC['expected_without_war'], -2))}. The low end assumes the pace of recent weeks continues ({round(100 + FC['recent_gap_pct'])}% of usual). The high end assumes the average pace since February ({round(100 + FC['whole_period_gap_pct'])}%).

DLD's November records should be out by {d(FC['check_on'])}. I'll check then, and again on {d(FC['recheck_on'])}, because DLD can still add late registrations. If the real number lands outside the range, the model needs another look, and I'll say so. So nobody has to take my word for the timing, the forecast is archived with a DOI: https://doi.org/{REL['doi_version']}.

> **Method, briefly**
>
> - **Data:** Dubai Land Department open data. {n(F['sales_read'])} residential sales from {d(F['sales_read_from'])} to {F['data_to_label']}, {n(F['leases_read'])} Ejari flat leases, plus DLD projects and valuations. {F['listings_checked']} portal listings, checked on one day, for asking prices (only totals are published).
> - **The usual pattern:** a regression on daily sales (Python, statsmodels). It allows for weekday, month, year, Ramadan and Eid, with one step from 28 February. The same model is run for each price band and area.
> - **Prices:** a same-building index of price per square foot for ready flats, January 2026 = 100.
> - **Checks:** my totals against figures others published from the same DLD records. {verdicts['match']} match, {verdicts['close']} close and {verdicts['miss']} miss, all listed in the repo with reasons. Every number reruns from one command, and GitHub reruns it on each change.
> - **Lead desk:** n8n 2.42.5, self-hosted; rules-only reading; tested blind on 90 written enquiries.

## Limitations

The model describes what happened after 28 February, not why. The likely range around the overall pace is wide, and a simpler trend model gives {round(100 + F['war_gap_trend_model_pct'])}% instead of {P['overall_pct']}%. DLD records a sale when it's registered, which can be weeks after the deal. So the latest months may still rise a little. October only runs to the 19th. Asking prices come from one day's listings. And the desk's test messages were written for the test, not sent by real buyers.

Three published figures don't match mine. One covers the whole UAE. One quarterly total includes property types I left out. And one price index moves sooner because it's based on valuations rather than registered sales. I've kept those in the comparison instead of quietly dropping them.

## See it, rerun it

- The dashboard, written for first-time buyers: {PAGES}
- The code, the data and every check: {REPO}

If you work in Dubai property and something here doesn't match what you're seeing, I'd like to hear it.

*Independent analysis by Mithun Cyriac, made possible by the Dubai Land Department's open data. Built with Python, statsmodels, n8n and an AI model. Data to {F['data_to_label']}. Not financial advice.*
"""

(OUT / "linkedin_post.txt").write_text(linkedin, encoding="utf-8")
(OUT / "linkedin_first_comment.txt").write_text(comment, encoding="utf-8")
(OUT / "medium_explainer.md").write_text(medium, encoding="utf-8")
body = lambda t: [w for w in t.split() if not w.startswith("#")]
med_words = len(" ".join(l for l in medium.splitlines() if not l.startswith("[Image")).split())
print(f"linkedin {len(body(linkedin))} words | comment {len(comment)} chars | medium {med_words} words")
