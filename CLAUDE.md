# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Goldirham Whisper — a static Hugo site tracking obscure economic releases and
exchange infrastructure dates ("dates that move markets first"). No build
tooling beyond Hugo itself: fonts are loaded from a CDN, the main app is
vanilla JS, the not-yet-unified `/event/`/`/search/`/`/about/` pages still
load Tailwind and Alpine.js from CDN — there is no `package.json`, and no
automated tests.

## Commands

```bash
pip install -r scripts/requirements.txt   # Python deps for the aggregator/digest
python scripts/aggregator.py              # fetch live sources + merge manual_events.json -> data/events.json + static/data/*.js
python scripts/aggregator.py --export-only  # regenerate static/data/*.js from the existing data/events.json without re-fetching
python scripts/digest.py                  # build static/digest.xml (weekly "most obscure" RSS digest)
hugo server                               # local dev server, http://localhost:1313
hugo --gc --minify                        # production build -> public/
```

There's no single-test entry point — verify changes by running `hugo server`
and driving the site in a browser (or `hugo --gc --minify` and diffing
`public/`).

## Data pipeline (read this before touching event data)

```
scripts/config.yaml ────────┐
data/manual_events.json ────┼──▶ scripts/aggregator.py ──▶ data/events.json
(Google Sheet CSV, optional)┘         │                          │
                                       └──▶ static/data/events-data.js
                                            static/data/flags-data.js
```

- `data/events.json` is the canonical merged output and is also republished
  verbatim at `/events.json` (custom `EVENTSJSON` output format in
  `hugo.toml`) and as `/index.xml` (`layouts/index.rss.xml`).
- `static/data/events-data.js` / `flags-data.js` are separate generated JS
  modules the SPA frontend (`layouts/index.html`) imports directly — they
  are **not** derived from `data/events.json` at build time, only by
  `aggregator.py`'s `export_spa_data()`. If you hand-edit `data/events.json`
  or `data/manual_events.json`, re-run `aggregator.py --export-only` or the
  SPA will show stale data.
- `.github/workflows/update-events.yml` runs the aggregator every 6 hours and
  commits `data/events.json`, `data/manual_events.json`, and both
  `static/data/*.js` files — all four must stay in the `git add` line or the
  scheduled run silently desyncs the SPA from the raw data.
- Curate exchange/economics events by hand in `data/manual_events.json`.
  Entries take a `status` field: missing/`"approved"` publishes, `"pending"`
  or `"rejected"` stages an entry out without deleting it. Manual entries win
  over auto-fetched ones on key collision (`date` + `title[:100]` + `source`).
- Live source reality check (already done — see `config.yaml` comments): most
  free exchange iCal/RSS calendars are dead, 403'd, or JS-rendered. Only JPX's
  holiday-calendar HTML (bespoke `parse_jpx_holidays()` in `aggregator.py`)
  and ONS UK's release-calendar RSS survived testing. BoE/BoC/ECB/SEC RSS
  work but need the `keywords` relevance filter (per-source in
  `config.yaml`) to strip HR/PR noise from real statistical content. Don't
  re-add a "obviously free" calendar URL without live-testing it first.
- `GW_FLAGS` (source-name substring → flag emoji) exists in **two**
  independent places that must be kept in sync by hand: `aggregator.py` and
  the generated `static/data/flags-data.js`. There is no shared source of
  truth for this mapping.

## Frontend architecture

The main app — calendar, exchanges, economics, search, about — is one
self-contained document, `layouts/partials/app.html` (vanilla JS, no
framework; inline CSS design tokens; ambient canvas background). It's
included from three thin Hugo templates, each passing which view should be
active on load:

- `layouts/index.html` → `{{ partial "app.html" (dict "view" "calendar" "page" .) }}`
- `layouts/economics/list.html` → `... "view" "economics" ...`
- `layouts/exchanges/list.html` → `... "view" "exchanges" ...`

All three render the *identical* app; only the initial `S.view` (and the
server-rendered `<title>`/description/canonical, sourced from `.page.Title`
etc.) differ. Client-side nav clicks (`data-act="nav"`) just flip `S.view`
and re-render `#app` — no URL change, no page reload. Data loads once via a
dynamic `import()` of `static/data/events-data.js` + `flags-data.js`
(deferred into `boot()`), not from any Hugo template variable.

**`/event/`, `/search/`, and `/about/` are not yet unified** — they still
render a separate, older Alpine.js + Tailwind (CDN) implementation via
`layouts/_default/baseof.html` + partials (`head`, `ticker`, `header`,
`footer`, `data`, `store`) + `layouts/event/list.html`, `search/list.html`,
`_default/single.html`. That implementation embeds `data/events.json`
inline (`layouts/partials/data.html`) and uses its own Alpine store
(`$store.gw`, `gwSearch()`, etc. in `layouts/partials/store.html`) —
completely separate code from `app.html`. If asked to unify these too, add
matching one-line wrappers around `app.html` the same way economics/exchanges
were done, then confirm nothing else still depends on `_default/list.html`,
`event/list.html`, or `search/list.html` before deleting them.

`hugo.toml` sets `[minify] disableHTML = true`; the comment there explains
this was needed for the now-deleted DC-runtime SPA and could likely be
re-enabled, just hasn't been tested.

## Other things worth knowing

- `scripts/digest.py` is a separate pipeline from the aggregator: it reads
  `data/events.json` and writes `static/digest.xml`, meant to be piped
  through a free Mailchimp RSS-to-email campaign. Its `SITE_URL` is still a
  placeholder domain.
- No git identity, hosting (Cloudflare Pages / GitHub Pages), or Mailchimp
  connection is configured yet — the repo builds and runs locally but isn't
  deployed anywhere.
