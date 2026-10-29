# Running the lead desk in n8n (free, about 15 minutes)

Five workflows, all in `desk/workflows/`:

| | Workflow | What it does |
|---|---|---|
| A | Lead desk | Webhook in. Reads the enquiry, checks the budget against DLD's post-war median price, sets Hot/Warm/Cold, drafts a reply, logs the lead to `desk/runtime/leads.csv` and saves the draft in `desk/runtime/drafts/` for an agent to approve. Repeat enquiries from the same phone within 30 days are merged. |
| F | Enquiry form | A web form at `/form/lead-form` that hands each submission to A. |
| B | Test harness | Sends the 90 test enquiries in `desk/test_set.json` through A and scores the tiers against answers A never sees. Writes `desk/runtime/harness_report.json`. |
| C | Weekly refresh | Every Monday 07:00 Dubai time, or on demand: asks the pipeline service to pick up a new DLD export, rerun every number, run the tests and commit. |
| E | Errors | Any failure in A, B, C or F is written to `desk/runtime/errors.log`. |

Nothing here costs money. The reading is rules-only (`desk/desk_logic.js`, an exact port of `scripts/rule_parser.py`).
Telegram alerts are built in but switched off.

## Option 1: Node.js, no Docker (what was tested)

Needs Node.js 22 or newer and Python 3.14 with `pip install -r requirements.txt`. In Git Bash:

```bash
python desk/build_workflows.py
export N8N_USER_FOLDER="$PWD/.n8n-local"
npx --yes n8n@2.42.5 import:workflow --separate --input=desk/workflows
for id in DLDeskErrors0001 DLDeskLeadDesk01 DLDeskHarness001 DLDeskRefresh001 DLDeskForm000001; do npx --yes n8n@2.42.5 publish:workflow --id=$id; done
python desk/pipeline_server.py &      # the refresh service on 127.0.0.1:8765
./desk/start-n8n.sh                    # n8n on http://localhost:5678
```

The first `npx` run downloads n8n (a few minutes). Open http://localhost:5678 once to create your own owner login if you
want to see the workflows in the editor; the webhooks and the form work without it.

## Option 2: Docker Desktop

```bash
docker compose up -d
```

Then import and publish the workflows inside the container (`docker compose exec n8n n8n import:workflow --separate --input=/desk/workflows`,
then `publish:workflow` for each ID as above) and restart: `docker compose restart n8n`.

If Docker Desktop stops at start-up with "initializing Inference manager ... dockerInference: The file cannot be accessed
by the system", quit Docker Desktop, delete the file `%LOCALAPPDATA%\Docker\run\dockerInference`, and start it again
(or restart Windows).

## Try it

```bash
# one enquiry (use test details)
curl -X POST http://localhost:5678/webhook/lead-desk -H "Content-Type: application/json" \
  -d '{"name":"Test Buyer","phone":"050 111 2233","message":"1 bed in JVC, pre-approved for 950k, moving in 2 months"}'
# the 90-case test
curl -X POST http://localhost:5678/webhook/desk-test
# refresh the numbers now
curl -X POST http://localhost:5678/webhook/desk-refresh
```

The form: http://localhost:5678/form/lead-form

## Turning on Telegram (optional, free)

1. Create a bot with @BotFather and copy its token. Send it one message, then get your chat ID.
2. In n8n, add a Telegram credential with the token, and set `TELEGRAM_CHAT_ID` in `desk/start-n8n.sh` (or `docker-compose.yml`).
3. Open workflows A, C and E, pick the credential on the Telegram node and enable it.

## A new DLD export

Download the full Transactions history from DLD open data, put the CSV part(s) in `desk/inbox/`, and either wait for
Monday or run the refresh now. If a headline number moves, the new value becomes the locked one in
`tests/locked_headlines.json`, and the commit message lists every change.
