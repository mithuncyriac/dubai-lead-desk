// Fills desk_tier and agree in a CSV with columns id, enquiry, agent_tier (see proof/agent_blind_test.md).
// Usage: node desk/tier_csv.js proof/agent_sheet.csv
const fs = require('fs'), path = require('path');
const DESK = require('./desk_logic.js');
const { prices } = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'site', 'desk_prices.json'), 'utf8'));
const file = process.argv[2];
if (!file) { console.error('usage: node desk/tier_csv.js <sheet.csv>'); process.exit(1); }

function parseCSV(text) {          // small RFC 4180 reader: quoted fields, commas and newlines inside quotes
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') q = false; else cell += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}
const esc = v => /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;

const [head, ...body] = parseCSV(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const col = n => head.indexOf(n);
const now = new Date(), asOf = { y: now.getFullYear(), m: now.getMonth() + 1 };
let n = 0, same = 0;
for (const r of body) {
  const text = (r[col('enquiry')] || '').trim();
  if (!text) continue;
  const tier = DESK.tier(DESK.parse(text, asOf), prices).tier;
  r[col('desk_tier')] = tier;
  const agent = (r[col('agent_tier')] || '').trim();
  r[col('agree')] = agent ? String(agent.toLowerCase() === tier.toLowerCase()) : '';
  if (agent) { n++; if (agent.toLowerCase() === tier.toLowerCase()) same++; }
}
fs.writeFileSync(file, [head, ...body].map(r => r.map(c => esc(c ?? '')).join(',')).join('\n') + '\n');
console.log(n ? `agreement: ${same}/${n}` : 'desk tiers filled; add agent_tier to compare');
