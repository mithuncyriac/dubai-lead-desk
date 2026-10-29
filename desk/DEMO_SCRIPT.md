# 90-second demo recording

Record the screen with Windows' Snipping Tool (Record) or OBS, both free. Before you start, have these open in
separate browser tabs or windows: the dashboard, the n8n editor showing workflow A, the form at
http://localhost:5678/form/lead-form, and File Explorer on `desk/runtime/`.
Use test details only. Speak slowly; the timings leave room for that.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:12 | Dashboard, top of the page | "Since the war began on the 28th of February, Dubai home sales have run about a third below their usual pattern. I worked that out from the Dubai Land Department's own records, about 470,000 sales." |
| 0:12–0:25 | Scroll to "Who kept buying" | "The drop isn't even. Homes under a million dirhams still sell at about 80% of the usual pace. Above five million, it's about half. So most enquiries a brokerage gets now are smaller ones, and speed matters." |
| 0:25–0:35 | n8n editor, workflow A | "So I built a small lead desk in n8n. It runs free on my laptop. An enquiry comes in, it reads it, checks the budget against what homes actually sold for, and sorts it." |
| 0:35–0:52 | The form: type a test enquiry, e.g. "Cash buyer, studio in JVC, around 650k, ready to buy this week", submit | "Here's a buyer enquiry coming in through a web form." |
| 0:52–1:05 | File Explorer: open `leads.csv`, then the new file in `drafts/` | "It's logged, marked Hot because the budget is close to recent sale prices and they're paying cash, and a reply is drafted. An agent approves it before anything goes out." |
| 1:05–1:18 | Terminal: `curl -X POST http://localhost:5678/webhook/desk-test`, show the result | "To check it, I run 90 test enquiries with answers the desk never sees. The free rules version gets 77 right. The misses are things like numbers written as words." |
| 1:18–1:30 | Dashboard, "A forecast you can check" | "And so this isn't just hindsight, there's a forecast for November on the page, with the date I'll check it. Everything reruns from one command, and the code is public." |

If you go over time, cut the 1:05 harness step first; the dashboard covers it.
