"""Writes the LinkedIn post, its first comment and the Medium explainer into posts/. Every number comes from site/facts.json
(and dash_data/validation.csv for the checks), so a data refresh rewrites them too."""
import csv, json
from datetime import date
from pathlib import Path

F = json.loads(Path("site/facts.json").read_text(encoding="utf-8"))
V = list(csv.DictReader(open("dash_data/validation.csv", encoding="utf-8")))
FC = F["forecast"]
OUT = Path("posts")
OUT.mkdir(exist_ok=True)
PAGES, REPO = "https://mithuncyriac.github.io/dubai-lead-desk/", "https://github.com/mithuncyriac/dubai-lead-desk"

a = lambda v: abs(round(v))                       # 36.6 -> 37
n = lambda v: f"{int(v):,}"
share = lambda gap: round(100 + gap)
d = lambda iso: f"{date.fromisoformat(iso).day} {date.fromisoformat(iso):%B %Y}"
verdicts = {k: sum(r["verdict"] == k for r in V) for k in ("match", "close", "miss")}
rules_right = round(F["rules_only_pass_pct"] * 0.9)
months = round(F["jvc_pipeline_months"])
B = json.loads(Path("site/chart_data.json").read_text(encoding="utf-8"))["bands"]
under2m = round(100 * sum(b["sales"] for b in B[:2]) / sum(b["sales"] for b in B))   # share of post-war sales under AED 2M

linkedin = f"""Since 28 February, Dubai home sales have run about {a(F['war_gap_pct'])}% below their usual pattern. That comes from the Dubai Land Department's own records: {n(F['sales_read'])} sales, data to {F['data_to_label']}.

The drop isn't even. Homes under AED 1M still sell at about {share(F['band_under1m_pct'])}% of the usual pace. Above AED 5M it's closer to half.

If you're buying your first home, good cheaper flats still go quickly, and bigger budgets have more room to negotiate. If you run a brokerage, {under2m}% of sales since February were under AED 2M, so how fast you answer those buyers matters.

So I built a small lead desk in n8n. It reads each enquiry, checks the budget against what homes actually sold for, and drafts a reply an agent approves. It costs nothing to run.

I've also written down a forecast for November, so you can check me: {n(FC['forecast_low'])} to {n(FC['forecast_high'])} sales.

Dashboard, code and method in the first comment.

#Dubai #RealEstate #DataAnalysis #n8n #Automation
"""

comment = f"""Dashboard (one page, works on a phone): {PAGES}
Code, data and how every number was checked: {REPO}
The longer write-up on Medium: [paste the Medium link here]

Source: Dubai Land Department open data, to {F['data_to_label']}. Independent analysis, not financial advice.
"""

rows = "\n".join(f"| {r['check']} | {r['ours']} | {r['published']} | {r['source']} | {r['verdict']} |" for r in V)

medium = f"""# Who kept buying homes in Dubai after 28 February?

*What {n(F['sales_read'])} Dubai Land Department sales records show, and the small tool I built from it. Data to {F['data_to_label']}.*

[Image: carousel slide 1, "Who kept buying homes in Dubai after 28 February?"]

When the war began on 28 February, I wanted a straight answer to a simple question. Were people in Dubai still buying homes, and if so, which ones?

Market reports give you a headline number, usually a quarter late. I wanted to see it month by month, split by price, from the records themselves. So I went to the source: the Dubai Land Department's open data. Every registered home sale since January 2024, {n(F['sales_read'])} of them, plus {n(F['leases_read'])} Ejari rental contracts and DLD's lists of projects and valuations.

Here's what I found, and what I'd do with it.

## Sales are about a third below normal, and the gap is widening

You can't just compare this year with last year. Dubai sales move with the seasons, with Ramadan and Eid, and with the day of the week, and 2026 had its own trend before February. So I fitted a model to the pattern from January 2024 up to the war, then asked it what each month since March "should" have looked like.

The answer: {n(F['sales_actual_post'])} sales were registered between 28 February and {F['data_to_label']}, against about {n(F['sales_expected_post'])} the usual pattern would have predicted. That's {a(F['war_gap_pct'])}% below. The honest range is wide, somewhere between {a(F['war_gap_high_pct'])}% and {a(F['war_gap_low_pct'])}%, but both versions of the model I tried point the same way.

What surprised me more was the direction of travel. In March the gap was {a(F['gap_march_pct'])}%. By September it was {a(F['gap_september_pct'])}%. So far this doesn't look like a dip the market is climbing out of.

[Image: carousel slide 2, monthly sales against the usual pattern]

## The cheaper the home, the smaller the drop

This is the part I think matters most. Split the same sales by price and the picture changes completely.

- Under AED 1M: about {share(F['band_under1m_pct'])}% of the usual pace
- AED 1M to 2M: about {share(F['band_1to2m_pct'])}%
- AED 2M to 5M: about {share(F['band_2to5m_pct'])}%
- Above AED 5M: about {share(F['band_over5m_pct'])}%

The smaller homes held up best. At the top end, sales have roughly halved.

[Image: carousel slide 3, sales by price band]

## Prices have moved much less than sales

A crude average price can mislead you here, because if fewer big apartments sell, the average falls even when nothing got cheaper. So I compared sales within the same buildings over time. On that basis, ready flats in JVC are about {a(F['jvc_ready_price_change_pct'])}% cheaper than in January, and in Dubai Marina about {a(F['marina_ready_price_change_pct'])}%.

Asking prices haven't fully caught up. The listings I checked on Bayut and Property Finder asked about {round(F['jvc_asking_premium_pct'])}% more than recent DLD sales in JVC, and about {round(F['marina_asking_premium_pct'])}% more in Dubai Marina.

## There is a lot of supply still to come

JVC has {n(F['jvc_pipeline_units'])} flats that were sold off-plan since 2024 and haven't been handed over yet. At the post-war pace of {n(F['jvc_sales_per_month'])} sales a month, that's about {months} months' worth of sales. In other words, there is no shortage of new stock on the way.

## What this means if you're buying your first home

This is my reading, not advice, but here's what I'd take from it:

1. Start from what homes actually sold for, not from the asking price. DLD's records are public.
2. Under AED 1M, expect competition. Those homes are still selling at about {share(F['band_under1m_pct'])}% of the usual pace.
3. With a bigger budget, you probably have more room to negotiate than you'd think.
4. Prices have moved less than the headlines about sales might suggest.
5. There's no need to rush into an off-plan deal in JVC with that much supply coming.

## What it means for a brokerage, and the tool I built

If I ran a brokerage, I'd notice that {under2m}% of sales since February were under AED 2M, while the rare big ones are worth a senior agent's time from the first message. That's a recommendation, not a measured result. Whether faster replies actually win more deals is something a brokerage would have to test.

So I built a small lead desk to try the idea. It runs in n8n, on my laptop, for free. An enquiry comes in by web form or message. The desk reads the area, bedrooms, budget, timing and how they're paying, checks the budget against DLD's recent sale prices for that kind of home, sorts the lead into Hot, Warm or Cold, and drafts a first reply. An agent approves the reply before anything goes out. If the same person writes in again from a slightly different number format, it merges the two.

Then I tested it on 90 enquiries written for the test, including 30 built to trip it up, with the right answers hidden from the desk. The free version, which reads enquiries with plain rules, got {rules_right} of 90 right. It stumbles on wording it has no rule for: numbers written as words, abbreviations like "mtg", or "a year and a half". An AI model reading the same messages blind got {F['desk_postwar_pass']}, but that version needs a paid API key. I'd rather show the free one honestly than oversell the paid one.

One detail I liked: checking budgets against post-war prices instead of pre-war averages changed the tier of {F['tier_changes']} of the 90 test leads. Small, but those are exactly the leads an agent would otherwise misjudge.

[Image: screenshot of the n8n lead desk]

## A forecast you can check

Hindsight is easy, so here's something that can be wrong. For November 2026, I expect Dubai home sales to land between {n(FC['forecast_low'])} and {n(FC['forecast_high'])}. The usual pattern alone would expect about {n(round(FC['expected_without_war'], -2))}. The low end assumes the gap of the latest weeks holds ({a(FC['recent_gap_pct'])}%), the high end that it goes back to the average since February ({a(FC['whole_period_gap_pct'])}%).

DLD's November records should be out by {d(FC['check_on'])}. I'll check then. If the real number lands outside the range, the model is missing something, and I'll say so.

> **Method, briefly**
>
> - **Data:** Dubai Land Department open data. {n(F['sales_read'])} residential sales from {d(F['sales_read_from'])} to {F['data_to_label']}, {n(F['leases_read'])} Ejari flat leases, plus DLD projects and valuations. {F['listings_checked']} portal listings, checked on one day, for asking prices (only totals are published).
> - **The "usual pattern":** a regression on daily sales with weekday, month, year, Ramadan and Eid effects, and a single step from 28 February (Python, statsmodels, with errors that allow for day-to-day correlation). The same model is run separately for each price band and area.
> - **Prices:** a same-building index of price per square foot for ready flats, January 2026 = 100.
> - **Checks:** my totals against figures others published from the same DLD records ({verdicts['match']} match, {verdicts['close']} close, {verdicts['miss']} miss, all listed in the repo with reasons). Every number reruns from one command, and GitHub reruns it on each change.
> - **Lead desk:** n8n 2.42.5, self-hosted; rules-only reading; tested blind on 90 written enquiries.

## Limitations

The model can't separate the war from anything else that changed after 28 February, so the honest phrase is "below the usual pattern", not "caused by". The range around the main number is wide, and a simpler trend model gives {a(F['war_gap_trend_model_pct'])}% instead of {a(F['war_gap_pct'])}%. DLD records a sale when it's registered, which can be weeks after the deal, so the latest months may still rise a little, and October only runs to the 19th. Asking prices come from one day's listings. And the desk's test messages were written for the test, not sent by real buyers.

Three published figures don't match mine. Goldman Sachs's early March number covers the whole UAE. One quarterly sales total includes property types I left out. And one price index reacts faster because it's based on valuations rather than registered sales. I've kept those misses in the comparison instead of quietly dropping them.

## See it, rerun it

- The dashboard, written for first-time buyers: {PAGES}
- The code, the data and every check: {REPO}

If you work in Dubai property and something here doesn't match what you're seeing, I'd like to hear it.

*Independent analysis by Mithun Cyriac. Built with Python, statsmodels, n8n and an AI model. Source: Dubai Land Department open data, to {F['data_to_label']}. Not financial advice.*
"""

(OUT / "linkedin_post.txt").write_text(linkedin, encoding="utf-8")
(OUT / "linkedin_first_comment.txt").write_text(comment, encoding="utf-8")
(OUT / "medium_explainer.md").write_text(medium, encoding="utf-8")
body = lambda t: [w for w in t.split() if not w.startswith("#")]
med_words = len(" ".join(l for l in medium.splitlines() if not l.startswith("[Image")).split())
print(f"linkedin {len(body(linkedin))} words | comment {len(comment)} chars | medium {med_words} words")
