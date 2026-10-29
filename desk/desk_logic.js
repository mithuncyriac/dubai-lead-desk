// Dubai Lead Desk: the free, no-AI reading of a buyer enquiry. An exact port of scripts/rule_parser.py
// (tests/test_desk_parity.py checks both give identical output on every test message), plus the tier rule,
// phone clean-up for duplicates and the drafted reply. Used inside the n8n Code nodes and by the dashboard.

const DESK = (() => {
  const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
  const WORDNUM = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, twelve: 12, eighteen: 18 };

  // Python's round(x, -4) rounds halves to even; match it so budgets agree to the dirham
  function roundTo10k(v) {
    const q = v / 1e4, f = Math.floor(q), diff = q - f;
    const r = Math.abs(diff - 0.5) < 1e-9 ? (f % 2 === 0 ? f : f + 1) : Math.round(q);
    return r * 1e4;
  }

  function area(t) {
    if (/\b(jvc|jumeirah village circle|jumeira village)\b/.test(t)) return 'JVC';
    if (/\b(dubai marina|marina|mrna)\b/.test(t)) return 'Dubai Marina';
    return 'unknown';
  }

  function beds(t) {
    const found = [];
    for (const m of t.matchAll(/\bstudio\b/g)) found.push([m.index, 0]);
    for (const m of t.matchAll(/\b(\d)\s*-?\s*(?:br|bhk|bed|beds|bedroom|bedrooms|b\/r)\b/g)) found.push([m.index, +m[1]]);
    if (!found.length) return 'unknown';
    found.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return found[found.length - 1][1];                // last mention wins ("sorry, I meant 2 beds")
  }

  function budget(t) {
    let best = null;
    for (const m of t.matchAll(/(?:aed|dhs|dh)?\s*(\d+(?:[.,]\d+)*)\s*(m|mn|mil|million|k)?\b/g)) {
      const num = m[1], unit = m[2] || '';
      const s = num.includes(',') && unit === '' ? num.replace(/,/g, '') : num.replace(/,/g, '.');
      if (!/^\d+(\.\d+)?$/.test(s)) continue;          // Python's float() rejects "1.500.000"
      let v = parseFloat(s);
      v = ['m', 'mn', 'mil', 'million'].includes(unit) ? v * 1e6 : unit === 'k' ? v * 1e3 : v;
      if (!(v >= 2e5 && v <= 5e7)) continue;
      const ctx = t.slice(Math.max(0, m.index - 40), m.index);
      let score = /budget|max|up to|upto|range|afford|around|spend/.test(ctx) ? 2 : 1;
      if (/listed|saw|asking|another (site|portal)|for \d/.test(ctx)) score = 0;   // decoy prices
      if (best === null || score > best[0]) best = [score, roundTo10k(v)];
    }
    return best && best[0] > 0 ? best[1] : 'unknown';
  }

  function timeline(t, asOf) {
    if (/\b(asap|now|immediately|right away|this week|ready to (buy|move|transfer))\b/.test(t)) return 0;
    let m = t.match(new RegExp('\\b(\\d+|' + Object.keys(WORDNUM).join('|') + ')\\s*(month|months|year|years|yr|yrs)\\b'));
    if (m) {
      const n = /^\d+$/.test(m[1]) ? +m[1] : WORDNUM[m[1]];
      return m[2].startsWith('y') ? n * 12 : n;
    }
    if (/\bwithin a month|next month\b/.test(t)) return 1;
    if (/\b(a|one) year\b|next year/.test(t)) return 12;
    m = t.match(new RegExp('\\b(' + MONTHS.join('|') + ')[a-z]*\\s*(20\\d\\d)?'));
    if (m) {
      const mon = MONTHS.indexOf(m[1]) + 1;
      const y = m[2] ? +m[2] : (mon > asOf.m ? asOf.y : asOf.y + 1);
      return (y - asOf.y) * 12 + mon - asOf.m;
    }
    return 'unknown';
  }

  function finance(t) {
    if (/pre-?approv|approval letter|approved (my )?mortgage/.test(t)) return 'mortgage_preapproved';
    if (/\bcash\b|no loan|without (a )?(loan|mortgage)|from (my )?savings|full payment/.test(t)) return 'cash';
    if (/mortgage|bank|financ|loan/.test(t)) return 'mortgage_not_started';
    return 'unknown';
  }

  // asOf = {y, m}: the month "December" or "next year" is counted from. Tests pin it to Oct 2026.
  function parse(text, asOf) {
    const t = String(text).toLowerCase();
    return { area: area(t), beds: beds(t), budget_aed: budget(t), timeline_months: timeline(t, asOf), finance: finance(t),
             browsing: /just (looking|browsing|researching)|research(ing)?|not serious|getting a feel|curious/.test(t) };
  }

  // prices: {"JVC|1": 1054123, ...} = DLD post-war median sale price by area and bedrooms
  function tier(f, prices) {
    const ref = f.area !== 'unknown' && f.beds !== 'unknown' ? prices[`${f.area}|${f.beds}`] ?? null : null;
    const ratio = ref && f.budget_aed !== 'unknown' ? f.budget_aed / ref : null;
    const tl = f.timeline_months;
    let t = 'Warm';
    if (f.browsing || (ratio !== null && ratio < 0.70) || (tl !== 'unknown' && tl > 12)) t = 'Cold';
    else if (ratio !== null && ratio >= 0.85 && tl !== 'unknown' && tl <= 3 && ['cash', 'mortgage_preapproved'].includes(f.finance)) t = 'Hot';
    return { tier: t, ref, ratio: ratio === null ? null : Math.round(ratio * 1000) / 1000 };
  }

  // same phone written four ways -> one key (UAE numbers)
  function e164(raw) {
    let d = String(raw || '').replace(/\D/g, '');
    if (d.startsWith('00')) d = d.slice(2);
    if (d.startsWith('0')) d = '971' + d.slice(1);
    if (!d.startsWith('971')) d = '971' + d;
    return '+' + d;
  }

  // demo stand-in for an agent's calendar: the next two weekdays after `now`, evening then morning
  function viewingSlots(now) {
    const out = [], d = new Date(now), f = x => x.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short', timeZone: 'Asia/Dubai' });
    while (out.length < 2) { d.setDate(d.getDate() + 1); if (d.getDay() !== 0 && d.getDay() !== 6) out.push(new Date(d)); }
    return [`${f(out[0])} at 6pm`, `${f(out[1])} at 11am`];
  }

  const aed = v => 'AED ' + (v >= 1e6 ? (v / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M' : Math.round(v / 1e3) + 'k');

  function draftReply(f, res, now) {
    const missing = f.budget_aed === 'unknown' ? 'What budget range are you working with?'
      : f.finance === 'unknown' ? 'Will you be buying with cash or a mortgage?'
      : f.timeline_months === 'unknown' ? 'When are you hoping to move or complete?'
      : f.beds === 'unknown' ? 'How many bedrooms do you need?'
      : f.area === 'unknown' ? 'Which areas are you considering?' : null;
    const what = `${f.beds === 'unknown' ? 'a home' : f.beds === 0 ? 'a studio' : 'a ' + f.beds + '-bed'}${f.area === 'unknown' ? '' : ' in ' + f.area}`;
    const reality = res && res.ratio !== null && res.ratio < 0.7 ? `Recent sales for ${what} have been nearer ${aed(res.ref)}, so I can also share options that fit your budget. ` : '';
    const [s1, s2] = viewingSlots(now);
    return `Hi, thanks for your message about ${what}. ${reality}${missing ? missing + ' ' : ''}I can show you two options: would ${s1} or ${s2} suit you?`;
  }

  return { parse, tier, e164, draftReply, viewingSlots, aed };
})();

if (typeof module !== 'undefined') module.exports = DESK;
