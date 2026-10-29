"""The Medium explainer as a plain web page (public/story/index.html, served at <pages>/story/), so Medium's
"Import a story" can bring it in with its images and a canonical link back. Images are the carousel slides.
Reads posts/medium_explainer.md and posts/Dubai-Lead-Desk-carousel.pdf."""
import html, json, re
from pathlib import Path
import pymupdf as fitz

OUT = Path("public/story")
OUT.mkdir(parents=True, exist_ok=True)
PAGES = "https://mithuncyriac.github.io/dubai-lead-desk/"
T = json.loads(Path("site/design_tokens.json").read_text(encoding="utf-8")); L, DK = T["light"], T["dark"]
IMAGES = {  # [Image: ...] marker -> carousel slide number
    "carousel slide 1": 1, "carousel slide 2": 2, "carousel slide 3": 3, "screenshot of the n8n lead desk": 6,
}

doc = fitz.open("posts/Dubai-Lead-Desk-carousel.pdf")
for n in sorted(set(IMAGES.values())):
    doc[n - 1].get_pixmap(dpi=96).save(OUT / f"slide-{n}.png")        # 1080 x 1350


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"(?<![\"'>])(https?://[^\s<,)]+[^\s<,).])", r'<a href="\1">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)


md = Path("posts/medium_explainer.md").read_text(encoding="utf-8")
title = md.splitlines()[0].lstrip("# ").strip()
out, lst, quote = [], None, []


def close_list():
    global lst
    if lst:
        out.append(f"</{lst}>")
        lst = None


for line in md.splitlines()[1:] + [""]:
    if line.startswith(">"):
        quote.append(line[1:].strip())
        continue
    if quote:                                   # the method box: a blockquote that may hold a list
        inner, ql = [], False
        for q in quote:
            if q.startswith("- "):
                inner.append(("<ul>" if not ql else "") + f"<li>{inline(q[2:])}</li>"); ql = True
            elif q:
                inner.append(("</ul>" if ql else "") + f"<p>{inline(q)}</p>"); ql = False
        out.append("<blockquote>" + "".join(inner) + ("</ul>" if ql else "") + "</blockquote>")
        quote = []
    m = re.match(r"\[Image: ([^,\]]+)", line)
    if m:
        close_list()
        key = next(k for k in IMAGES if line.startswith(f"[Image: {k}"))
        alt = line[len("[Image: "):-1]
        out.append(f'<figure><img src="slide-{IMAGES[key]}.png" alt="{html.escape(alt)}" width="1080" height="1350"></figure>')
    elif line.startswith("## "):
        close_list(); out.append(f"<h2>{inline(line[3:])}</h2>")
    elif re.match(r"^- ", line):
        if lst != "ul": close_list(); out.append("<ul>"); lst = "ul"
        out.append(f"<li>{inline(line[2:])}</li>")
    elif re.match(r"^\d+\. ", line):
        if lst != "ol": close_list(); out.append("<ol>"); lst = "ol"
        out.append(f"<li>{inline(line.split('. ', 1)[1])}</li>")
    elif line.strip():
        close_list(); out.append(f"<p>{inline(line)}</p>")
    else:
        close_list()

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="canonical" href="{PAGES}story/">
<meta name="description" content="What Dubai Land Department sales records show about who kept buying homes after 28 February 2026.">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:image" content="{PAGES}story/slide-1.png">
<meta name="author" content="Mithun Cyriac">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%230F1B2D'/%3E%3Cpath d='M8 22V12m6 10V8m6 14v-7m6 7V10' stroke='%23C9A45C' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
<script data-goatcounter="https://dubai-lead-desk.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
<style>
body {{ margin: 0; background: {L['bg']}; color: {L['ink']}; font: 19px/1.7 {T['font']['serif']}; }}
main {{ max-width: {T['measure']}; margin: 0 auto; padding: 48px 20px 96px; }}
h1 {{ font-weight: 400; font-size: {T['type']['h1']}; line-height: 1.15; margin: 0 0 16px; }}
h2 {{ font: 600 22px/1.3 {T['font']['sans']}; margin: 56px 0 12px; }}
a {{ color: inherit; text-decoration-color: {L['highlight']}; text-underline-offset: 3px; }}
figure {{ margin: 36px 0; }} img {{ width: 100%; height: auto; border-radius: {T['radius']}px; }}
blockquote {{ margin: 36px 0; padding: 4px 0 4px 20px; border-left: 2px solid {L['highlight']}; font: 16px/1.6 {T['font']['sans']}; color: {L['muted']}; }}
blockquote strong {{ color: {L['ink']}; }}
@media (prefers-color-scheme: dark) {{ body {{ background: {DK['bg']}; color: {DK['ink']}; }} a {{ text-decoration-color: {DK['highlight']}; }}
  blockquote {{ border-left-color: {DK['highlight']}; color: {DK['muted']}; }} blockquote strong {{ color: {DK['ink']}; }} }}
</style></head>
<body><main><article>
<h1>{html.escape(title)}</h1>
{chr(10).join(out)}
</article></main></body></html>
"""
(OUT / "index.html").write_text(page, encoding="utf-8")
print("story:", OUT / "index.html", "|", len(re.sub("<[^>]+>", " ", page).split()), "words incl. markup text |", len(list(OUT.glob("*.png"))), "images")
