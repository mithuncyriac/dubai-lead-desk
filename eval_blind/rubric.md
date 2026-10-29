# Lead scoring rubric (same text used in the n8n AI model node)

You are triaging an inbound buyer enquiry for a Dubai brokerage. Extract the facts and apply the rule exactly. If the message doesn't state a fact, use "unknown"; never guess.

Reference prices: average DLD sold price over the last 12 months, AED
| area | studio | 1 bed | 2 bed | 3 bed |
|---|---|---|---|---|
| JVC | 698,377 | 1,111,172 | 1,691,084 | 2,311,391 |
| Dubai Marina | 1,239,570 | 1,790,596 | 3,465,088 | 6,120,796 |

Facts to extract:
- area: "JVC" | "Dubai Marina" | "unknown"
- beds: 0 (studio) | 1 | 2 | 3 | "unknown"
- budget_aed: integer | "unknown"
- timeline_months: integer (0 = now / this week) | "unknown"
- finance: "cash" | "mortgage_preapproved" | "mortgage_not_started" | "unknown"
- browsing: true if they say they are only looking or researching with no real intent yet

ratio = budget_aed / reference price for that area and number of beds.

Rule:
- **Cold** if browsing, OR ratio < 0.70, OR timeline_months > 12.
- **Hot** if ratio ≥ 0.85 AND timeline_months ≤ 3 AND finance is "cash" or "mortgage_preapproved".
- **Warm** otherwise, including when a needed fact is unknown.
- unrealistic_budget = ratio < 0.70.

Return strict JSON:
{"id","area","beds","budget_aed","timeline_months","finance","browsing","ratio","tier","unrealistic_budget","confidence" (0–1),"language","reason" (≤15 words)}
