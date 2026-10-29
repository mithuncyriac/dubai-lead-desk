"""LinkedIn carousel: 8 slides at 1080x1350, in Banner 1's navy and gold, numbers from site/facts.json and chart_data.json.
Writes posts/carousel.html, posts/Dubai-Lead-Desk-carousel.pdf (upload this as a LinkedIn document) and posts/slides/slide-N.png."""
import json, subprocess
from pathlib import Path
import pymupdf as fitz

F = json.loads(Path("site/facts.json").read_text(encoding="utf-8"))
C = json.loads(Path("site/chart_data.json").read_text(encoding="utf-8"))
FC, P, MK = F["forecast"], F["pace"], F["market"]
OUT = Path("posts").resolve()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
T = json.loads(Path("site/design_tokens.json").read_text(encoding="utf-8")); DK = T["dark"]
NAVY, GOLD, CREAM, MUTED, LINE = T["brand"]["navy"], T["brand"]["gold"], DK["ink"], DK["muted"], DK["line"]
BLUE, HL, REF, GHOST = DK["chart"], DK["highlight"], DK["reference"], DK["line"]
SANS, SERIF = T["font"]["sans"], T["font"]["serif"]
a = lambda v: abs(round(v))
n = lambda v: f"{int(v):,}"
TOTAL = 8


def slide(i, kicker, title, body, foot=True):
    return f"""<section class="s"><div class="top"><span class="k">{kicker}</span><span class="pg">{i} / {TOTAL}</span></div>
<h2>{title}</h2><div class="body">{body}</div>
{'<div class="foot">Dubai Land Department open data · data to ' + F['data_to_label'] + '</div>' if foot else ''}</section>"""


def monthly_svg():
    rows = [r for r in C["monthly"] if r["area"] == "All"]
    W, H, l, b, t = 920, 560, 70, 60, 30
    mx = max(max(r["actual"], r["expected"]) for r in rows) * 1.1
    y = lambda v: t + (H - t - b) * (1 - v / mx)
    bw = (W - l) / len(rows)
    s = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    for v in range(0, int(mx), 5000):
        s.append(f'<line x1="{l}" x2="{W}" y1="{y(v):.0f}" y2="{y(v):.0f}" stroke="{LINE}"/><text x="{l - 12}" y="{y(v) + 8:.0f}" text-anchor="end" class="ax">{f"{v // 1000}k" if v else "0"}</text>')
    for i, r in enumerate(rows):
        x = l + i * bw
        s.append(f'<rect x="{x + bw * .18:.0f}" y="{y(r["actual"]):.0f}" width="{bw * .64:.0f}" height="{y(0) - y(r["actual"]):.0f}" rx="6" fill="{BLUE}"/>')
        s.append(f'<line x1="{x + bw * .06:.0f}" x2="{x + bw * .94:.0f}" y1="{y(r["expected"]):.0f}" y2="{y(r["expected"]):.0f}" stroke="{REF}" stroke-width="5" stroke-linecap="round"/>')
        mon = r["month"][5:]
        lab = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(mon)] + ("*" if r["month"] == F["data_to"][:7] else "")
        s.append(f'<text x="{x + bw / 2:.0f}" y="{H - 18}" text-anchor="middle" class="ax">{lab}</text>')
        if r["month"] in ("2026-03", "2026-09"):
            g = round(100 * r["actual"] / r["expected"])
            s.append(f'<text x="{x + bw / 2:.0f}" y="{y(r["expected"]) - 16:.0f}" text-anchor="middle" class="lb">{g}%</text>')
    s.append("</svg>")
    return "".join(s)


def bars(rows, color, maxv=100, unit="%", ref=None, first=None):
    out = []
    for k, (label, v, note) in enumerate(rows):
        col = first if first and k == 0 else color
        out.append(f'<div class="bar"><div class="bl">{label}</div><div class="bt"><div class="bf" style="width:{100 * v / maxv:.1f}%;background:{col}"></div>'
                   + (f'<div class="ref" style="left:{100 * ref / maxv:.1f}%"></div>' if ref else '') + f'</div><div class="bv">{v:g}{unit}</div></div>'
                   + (f'<div class="bn">{note}</div>' if note else ''))
    return "".join(out)


bands = [(b["band"], round(100 + b["gap"]), "") for b in C["bands"]]
slides = [
    f"""<section class="s cover"><div class="top"><span class="k">Dubai Lead Desk</span><span class="pg">1 / {TOTAL}</span></div>
<h1>Who kept buying homes in Dubai since late February?</h1>
<div class="hero"><div><div class="big">{P['overall_pct']}%</div><p>of the usual pace of home sales across Dubai since late February (likely {P['low_pct']}–{P['high_pct']}%)</p></div>
<div><div class="big">{P['under1m_pct']}%</div><p>of the usual pace for homes under AED 1M, the part that held up best</p></div></div>
<p class="lede">From {n(F['sales_read'])} Dubai Land Department sales records. Swipe for what it means.</p>
<div class="foot">Independent analysis by Mithun Cyriac · not financial advice</div></section>""",
    slide(2, "The pace of sales", "Homes kept selling every month, at about two-thirds of the usual pace",
          f'<div class="legend"><span><i style="background:{BLUE}"></i>sales registered</span><span><i style="background:{REF}"></i>usual pattern</span></div>{monthly_svg()}'
          f'<p class="note">Sales ran at {P["march_pct"]}% of the usual pace in March and {P["september_pct"]}% in September. *October covers 1–19 Oct.</p>'),
    slide(3, "Who kept buying", "Homes under AED 1M were the steadiest part of the market",
          '<p class="sub">Sales since late February as a share of the usual pace</p>' + bars(bands, BLUE, ref=100, first=HL) +
          f'<p class="note">Under AED 1M, homes still sell at about {P["under1m_pct"]}% of the usual pace. Above AED 5M, buyers have more time: about {P["over5m_pct"]}%.</p>'),
    slide(4, "Prices", "Same-building prices are 5–8% below January",
          f'<div class="pair"><div><div class="big">{a(F["jvc_ready_price_change_pct"])}%</div><p>below January for JVC ready flats, same buildings</p></div>'
          f'<div><div class="big">{a(F["marina_ready_price_change_pct"])}%</div><p>below January for Dubai Marina ready flats</p></div></div>'
          f'<p class="note">Asking prices sit about {round(F["jvc_asking_premium_pct"])}% above recent sales in JVC and {round(F["marina_asking_premium_pct"])}% in Dubai Marina. Start from sold prices. A JVC flat still earns about {round(MK["jvc_yield_low_pct"])}% a year in gross rent.</p>'),
    slide(5, "Supply", f"JVC has about {round(F['jvc_pipeline_months'])} months of off-plan supply to come",
          f'<div class="pair"><div><div class="big">{n(F["jvc_pipeline_units"])}</div><p>flats sold off-plan since 2024, not yet handed over</p></div>'
          f'<div><div class="big">{n(F["jvc_sales_per_month"])}</div><p>JVC sales a month since late February</p></div></div>'
          '<p class="note">That is a lot of new supply, so there is time to compare ready and off-plan.</p>'),
    slide(6, "The lead desk", "A free lead desk for the everyday enquiries",
          '<ol class="steps"><li>An enquiry arrives by form or message</li><li>It reads area, bedrooms, budget, timing and payment</li>'
          '<li>It checks the budget against DLD sale prices</li><li>It sorts the lead: Hot, Warm or Cold</li><li>It drafts a reply an agent approves</li></ol>'
          f'<p class="note">{MK["under2m_share_pct"]}% of sales were under AED 2M, so speed matters. Tested blind on 90 written enquiries: free rules version {round(F["rules_only_pass_pct"] * 0.9)}/90, AI model {F["desk_postwar_pass"]}.</p>'),
    slide(7, "Check me", "A forecast you can check",
          f'<div class="big xl">{n(FC["forecast_low"])}–{n(FC["forecast_high"])}</div><p class="sub">Expected Dubai home sales in November 2026. The usual pattern alone would expect about {n(round(FC["expected_without_war"], -2))}.</p>'
          f'<p class="note">First check on {int(FC["check_on"][8:])} December, and again on {int(FC["recheck_on"][8:])} January as late registrations arrive. If the real number lands outside this range, the model needs another look.</p>'),
    f"""<section class="s cover"><div class="top"><span class="k">See it, rerun it</span><span class="pg">8 / {TOTAL}</span></div>
<h1>The dashboard, the code and every check are public</h1>
<div class="links"><p><b>Dashboard</b><br>mithuncyriac.github.io/dubai-lead-desk</p><p><b>Code and data</b><br>github.com/mithuncyriac/dubai-lead-desk</p></div>
<p class="lede">Every number reruns from one command. Links in the first comment.</p>
<div class="foot">Made possible by the Dubai Land Department's open data, to {F['data_to_label']} · not financial advice</div></section>""",
]

css = f"""
@page {{ size: 1080px 1350px; margin: 0; }}
* {{ box-sizing: border-box; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ margin: 0; background: {NAVY}; font-family: {SANS}; color: {CREAM}; }}
.s {{ width: 1080px; height: 1350px; padding: 80px 80px 70px; display: flex; flex-direction: column; break-after: page; overflow: hidden; position: relative; background: {NAVY}; }}
.s:last-child {{ break-after: auto; }}
.top {{ display: flex; justify-content: space-between; font-size: 28px; letter-spacing: .14em; text-transform: uppercase; }}
.k {{ color: {GOLD}; font-weight: 600; }} .pg {{ color: {MUTED}; }}
h1 {{ font-family: {SERIF}; font-weight: 400; font-size: 92px; line-height: 1.08; margin: 70px 0 50px; }}
h2 {{ font-family: {SERIF}; font-weight: 400; font-size: 64px; line-height: 1.15; margin: 56px 0 36px; }}
.body {{ flex: 1; display: flex; flex-direction: column; gap: 26px; }}
.big {{ font-family: {SERIF}; font-size: 112px; line-height: 1; }} .big small {{ font-size: 50px; color: {MUTED}; }} .big.xl {{ font-size: 140px; color: {GOLD}; }}
.hero {{ display: flex; flex-direction: column; gap: 46px; border-top: 3px solid {GOLD}; padding-top: 40px; }}
.hero p, .pair p {{ font-size: 32px; color: {MUTED}; margin: 12px 0 0; line-height: 1.35; }}
.pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 50px; border-top: 3px solid {GOLD}; padding-top: 60px; margin-top: 30px; }}
.pair .big {{ font-size: 160px; }} .pair p {{ font-size: 38px; margin-top: 22px; }}
.lede {{ font-size: 38px; line-height: 1.4; color: #DCD6CA; margin-top: auto; }}
.sub {{ font-size: 32px; color: {MUTED}; margin: 0; line-height: 1.4; }}
.note {{ font-size: 34px; line-height: 1.45; color: #DCD6CA; margin: auto 0 0; border-left: 5px solid {GOLD}; padding-left: 26px; }}
.foot {{ font-size: 28px; color: {MUTED}; margin-top: 34px; padding-top: 22px; border-top: 1px solid {LINE}; }}
.legend {{ display: flex; gap: 36px; font-size: 28px; color: {MUTED}; }} .legend i {{ display: inline-block; width: 24px; height: 24px; border-radius: 5px; margin-right: 12px; vertical-align: -3px; }}
svg .ax {{ fill: {MUTED}; font-size: 28px; }} svg .lb {{ fill: {CREAM}; font-size: 32px; font-weight: 700; }}
.bar {{ display: grid; grid-template-columns: 240px 1fr 110px; align-items: center; gap: 22px; }}
.bl {{ font-size: 32px; font-weight: 600; text-align: right; }} .bv {{ font-size: 40px; font-weight: 700; }}
.bt {{ height: 56px; background: {GHOST}; border-radius: 4px; position: relative; }} .bf {{ height: 100%; border-radius: 4px; }}
.ref {{ position: absolute; top: -12px; bottom: -12px; border-left: 4px dashed {MUTED}; }}
.steps {{ font-size: 46px; line-height: 1.3; padding-left: 60px; margin: 20px 0 0; }} .steps li {{ margin: 0 0 40px; padding-left: 12px; }} .steps li::marker {{ color: {GOLD}; font-weight: 700; }}
.links p {{ font-size: 40px; line-height: 1.4; margin: 0 0 40px; color: #DCD6CA; }} .links b {{ color: {GOLD}; font-weight: 600; font-size: 30px; letter-spacing: .1em; text-transform: uppercase; }}
"""
html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Dubai Lead Desk carousel</title><style>{css}</style></head><body>{"".join(slides)}</body></html>'
(OUT / "carousel.html").write_text(html, encoding="utf-8")
pdf = OUT / "Dubai-Lead-Desk-carousel.pdf"
subprocess.run([CHROME, "--headless=new", f"--user-data-dir={Path('.chrome-print-profile').resolve()}", "--no-first-run", "--no-pdf-header-footer",
                "--virtual-time-budget=4000", f"--print-to-pdf={pdf}", (OUT / "carousel.html").as_uri()], check=True, capture_output=True, timeout=180)
doc = fitz.open(pdf)
(OUT / "slides").mkdir(exist_ok=True)
for i, pg in enumerate(doc, 1):
    pg.get_pixmap(dpi=72).save(OUT / "slides" / f"slide-{i}.png")
print("pages", doc.page_count, "size", [round(x) for x in doc[0].rect[2:]], "pt")
