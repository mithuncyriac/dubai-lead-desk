"""A non-AI scorer: regular expressions + the same tier rule. English (and Latin-script) text only.
Used as an independent check on the AI model, since no second model family is reachable from this setup."""
import json, re

REF = {tuple([k.split("|")[0], int(k.split("|")[1])]): v for k, v in json.load(open("eval/ref_v2.json")).items()}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
NOW_Y, NOW_M = 2026, 10
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "eighteen": 18}


def area(t):
    if re.search(r"\b(jvc|jumeirah village circle|jumeira village)\b", t):
        return "JVC"
    if re.search(r"\b(dubai marina|marina|mrna)\b", t):
        return "Dubai Marina"
    return "unknown"


def beds(t):
    found = [(m.start(), 0) for m in re.finditer(r"\bstudio\b", t)]
    found += [(m.start(), int(m.group(1))) for m in re.finditer(r"\b(\d)\s*-?\s*(?:br|bhk|bed|beds|bedroom|bedrooms|b/r)\b", t)]
    return sorted(found)[-1][1] if found else "unknown"   # last mention wins (handles "sorry, I meant 2 beds")


def budget(t):
    best = None
    for m in re.finditer(r"(?:aed|dhs|dh)?\s*(\d+(?:[.,]\d+)*)\s*(m|mn|mil|million|k)?\b", t):
        num, unit = m.group(1), (m.group(2) or "")
        try:
            v = float(num.replace(",", "")) if "," in num and unit == "" else float(num.replace(",", "."))
        except ValueError:
            continue
        v = v * 1e6 if unit in ("m", "mn", "mil", "million") else v * 1e3 if unit == "k" else v
        if 2e5 <= v <= 5e7:
            ctx = t[max(0, m.start() - 40):m.start()]
            score = 2 if re.search(r"budget|max|up to|upto|range|afford|around|spend", ctx) else 1
            if re.search(r"listed|saw|asking|another (site|portal)|for \d", ctx):
                score = 0          # decoy prices
            if best is None or score > best[0]:
                best = (score, int(round(v, -4)))
    return best[1] if best and best[0] > 0 else "unknown"


def timeline(t):
    if re.search(r"\b(asap|now|immediately|right away|this week|ready to (buy|move|transfer))\b", t):
        return 0
    m = re.search(r"\b(\d+|" + "|".join(WORDNUM) + r")\s*(month|months|year|years|yr|yrs)\b", t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else WORDNUM[m.group(1)]
        return n * 12 if m.group(2).startswith("y") else n
    if re.search(r"\bwithin a month|next month\b", t):
        return 1
    if re.search(r"\b(a|one) year\b|next year", t):
        return 12
    m = re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]*\s*(20\d\d)?", t)
    if m:
        y = int(m.group(2)) if m.group(2) else (NOW_Y if MONTHS[m.group(1)] > NOW_M else NOW_Y + 1)
        return (y - NOW_Y) * 12 + MONTHS[m.group(1)] - NOW_M
    return "unknown"


def finance(t):
    if re.search(r"pre-?approv|approval letter|approved (my )?mortgage", t):
        return "mortgage_preapproved"
    if re.search(r"\bcash\b|no loan|without (a )?(loan|mortgage)|from (my )?savings|full payment", t):
        return "cash"
    if re.search(r"mortgage|bank|financ|loan", t):
        return "mortgage_not_started"
    return "unknown"


def score(text):
    t = text.lower()
    f = dict(area=area(t), beds=beds(t), budget_aed=budget(t), timeline_months=timeline(t), finance=finance(t),
             browsing=bool(re.search(r"just (looking|browsing|researching)|research(ing)?|not serious|getting a feel|curious", t)))
    ref = REF.get((f["area"], f["beds"])) if f["area"] != "unknown" and f["beds"] != "unknown" else None
    ratio = f["budget_aed"] / ref if ref and f["budget_aed"] != "unknown" else None
    tl = f["timeline_months"]
    if f["browsing"] or (ratio is not None and ratio < 0.70) or (tl != "unknown" and tl > 12):
        tier = "Cold"
    elif ratio is not None and ratio >= 0.85 and tl != "unknown" and tl <= 3 and f["finance"] in ("cash", "mortgage_preapproved"):
        tier = "Hot"
    else:
        tier = "Warm"
    return dict(f, ratio=round(ratio, 3) if ratio else "unknown", tier=tier)
