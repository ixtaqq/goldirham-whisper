# Goldirham Whisper

Under-the-radar economic releases and exchange infrastructure dates that move
markets first. No paywalls, no API keys, no servers — a static Hugo site
backed by a Python aggregator and GitHub Actions.

## What it tracks

- **Exchange infrastructure** — maintenance windows, system releases, test/drill
  days, holiday and early-close schedules, quarter-end expiry and roll cycles,
  auction parameter changes.
- **Second-tier economics** — the releases consensus desks skim past: TIC flows,
  regional Fed surveys, factory orders, obscure national-statistics tables.

## How it works

```
scripts/config.yaml ──┐
                       ├─▶ scripts/aggregator.py ──▶ data/events.json
data/manual_events.json┘         │                        │
(curated exchange/economics)     │                        ▼
                                  └──▶ static/data/events-data.js
                                       static/data/flags-data.js
                                       (what the frontend actually imports)
```

- `scripts/aggregator.py` pulls live, keyless sources (JPX's holiday-calendar
  HTML, ONS UK's release-calendar RSS, plus BoE/BoC/ECB/SEC RSS with a
  keyword relevance filter to cut HR/PR noise) and merges them with hand
  curated entries in `data/manual_events.json` (and, optionally, a published
  Google Sheet CSV for community submissions).
- The frontend (`layouts/index.html`) is a single-page app built on a small
  custom component runtime (`static/support.js`) — not a JS framework — that
  imports the generated `static/data/*.js` modules directly.
- `scripts/digest.py` picks the most obscure upcoming events each week and
  writes `static/digest.xml`, meant to be piped through a free
  Mailchimp RSS-to-email campaign.

Two GitHub Actions keep it fresh with zero servers:

| Workflow | Schedule | Does |
|---|---|---|
| `update-events.yml` | every 6 hours | runs the aggregator, commits `data/events.json` + the generated SPA data files |
| `send-digest.yml` | Sundays | runs the digest generator, commits `static/digest.xml` |

## Local development

```bash
pip install -r scripts/requirements.txt
python scripts/aggregator.py      # fetch live sources + merge curated data
hugo server                       # http://localhost:1313
```

Curate exchange/economics events by hand in `data/manual_events.json`
(`status: "pending"` to stage an entry out without deleting it).

## Site structure

- `/` — calendar, filterable by type/date/keyword
- `/exchanges/`, `/economics/` — per-category views
- `/search/` — full-text search across all events
- `/event/` — single-event detail (query/hash driven, fully static)
- `/events.json`, `/index.xml`, `/digest.xml` — raw feeds

## Deployment

Static output (`hugo --gc --minify` → `public/`) is meant for Cloudflare
Pages or GitHub Pages — not yet wired up.
