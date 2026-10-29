# Optional: one agent, 20 real enquiries, sorted blind

The question this answers: does the desk sort real enquiries the way a working agent would?

## You need
- One agent who handles Dubai residential enquiries.
- 20 real enquiries from their inbox, WhatsApp or portal leads. Remove names, phone numbers and anything else that identifies a person before they reach you.

## Steps
1. The agent copies each anonymised message into `agent_sheet.csv` (column `enquiry`) and, without seeing the desk's answer, puts Hot, Warm or Cold in `agent_tier`. Agree the meaning first:
   - **Hot**: budget fits the area, wants to move within about 3 months, cash or mortgage pre-approved.
   - **Cold**: just browsing, budget well under what that home sells for, or more than a year away.
   - **Warm**: everything else.
2. Only then run the desk on the same sheet (needs Node.js, free):
   ```bash
   node desk/tier_csv.js proof/agent_sheet.csv
   ```
   It fills `desk_tier` and `agree`, and prints how many matched.
3. Write down the disagreements and, for each one, who you think was right and why.

## How to read the result
This is agreement, not accuracy: there is no answer key for real enquiries, and agents differ too. The rules-only desk got 77 of 90 on written test messages; real messages are messier, so expect lower. The interesting part is the list of disagreements, not the score.
