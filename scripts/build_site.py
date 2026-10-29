"""Builds the standalone dashboard: site/index.html, one file with the data and the desk logic built in.
No server, no login, no external requests (except optional GoatCounter analytics).
  GOATCOUNTER=<code> python scripts/build_site.py   adds free, cookie-free page-view counting
  REPO_URL=<url>                                    links the footer to the public repo
  PAGES_URL=<url/>                                  absolute address for link previews (LinkedIn, WhatsApp)"""
import html, json, os
from pathlib import Path

S = Path("site")
facts = json.loads((S / "facts.json").read_text(encoding="utf-8"))
page = (S / "template.html").read_text(encoding="utf-8")
gc = os.environ.get("GOATCOUNTER", "").strip()
repo = os.environ.get("REPO_URL", "https://github.com/mithuncyriac/dubai-lead-desk").strip()
safe = lambda o: json.dumps(o, ensure_ascii=False).replace("</", r"<\/")
for key, val in {
    "__FACTS__": safe(facts),
    "__CHARTS__": safe(json.loads((S / "chart_data.json").read_text(encoding="utf-8"))),
    "__PRICES__": safe(json.loads((S / "desk_prices.json").read_text(encoding="utf-8"))),
    "__DESK__": Path("desk/desk_logic.js").read_text(encoding="utf-8").replace("</script", r"<\/script"),
    "__ANALYTICS__": f'<script data-goatcounter="https://{html.escape(gc)}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>' if gc else "",
    "__REPO_LINK__": f'<a href="{html.escape(repo)}">{html.escape(repo.replace("https://", ""))}</a>' if repo else "the public repository",
    "__DATA_TO__": facts["data_to_label"],
    "__BUILT__": facts["built"],
    "__LISTINGS__": str(facts["listings_checked"]),
    "__PAGES__": os.environ.get("PAGES_URL", "https://mithuncyriac.github.io/dubai-lead-desk/").strip(),
}.items():
    page = page.replace(key, val)
assert "__" not in "".join(t for t in page.split("<script>")[0].split() if t.startswith("__")), "unfilled placeholder"
(S / "index.html").write_text(page, encoding="utf-8")
print("site/index.html", len(page) // 1024, "KB", "| analytics:", gc or "off")
