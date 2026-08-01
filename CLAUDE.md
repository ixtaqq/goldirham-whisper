# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Goldirham Whisper — a static Hugo site tracking obscure economic releases and
exchange infrastructure dates ("dates that move markets first"). No build
tooling beyond Hugo itself: Tailwind and Alpine.js are loaded from CDN, there
is no `package.json`, and there are no automated tests.

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
- `GW_FLAGS` (source-name substring → flag emoji) exists in **three**
  independent places that must be kept in sync by hand: `aggregator.py`,
  `layouts/partials/store.html`, and the generated
  `static/data/flags-data.js`. There is no shared source of truth for this
  mapping.

## Two parallel frontend implementations — know which one you're editing

This is the single most important architectural fact in the repo. The site
was rebuilt once but the old implementation was never deleted, and both are
live in production simultaneously on different routes:

1. **`layouts/index.html`** — the one actually used when navigating the site
   normally. A fully self-contained HTML document (bypasses
   `_default/baseof.html` entirely) built on a small custom component runtime
   in `static/support.js` (custom elements `<x-dc>`, `<sc-if>`, `<sc-for>`,
   `<dc-import>`, a `DCLogic`/`Component` base class). It owns **every**
   view — calendar, exchanges, economics, search, about — as client-side
   state (`view: 'calendar' | 'exchanges' | ...`) on a single page at `/`.
   Clicking nav links here never changes the URL. `static/EventRow.dc.html`
   is a shared row component imported via `<dc-import>`.
2. **`layouts/_default/baseof.html`** + partials (`head`, `ticker`, `header`,
   `footer`, `data`, `store`) + per-section templates
   (`layouts/economics/list.html`, `exchanges/list.html`, `event/list.html`,
   `search/list.html`, `_default/single.html`) — an older Alpine.js +
   Tailwind (CDN) implementation, internally called "GW" (`$store.gw`,
   `gwEconomics()`, `gwTicker()`, etc. in `layouts/partials/store.html`).
   This is what actually renders if you (or a search engine, or a shared
   link) hit `/economics/`, `/exchanges/`, `/event/`, `/search/`, or
   `/about/` **directly** — verified by curling those routes; they contain
   `x-data="gwEconomics()"` etc., not the DC runtime.

Both read from the same `data/events.json` (the Alpine version embeds it
inline via `layouts/partials/data.html`; the SPA imports
`static/data/events-data.js`), but the markup, styling, and JS are entirely
separate codebases implementing the same features twice. Before "fixing a
bug on the economics page," check which implementation the user actually
means — a fix in one will not affect the other. `_default/list.html` is an
unused fallback (comment in the file says so).

`hugo.toml` sets `[minify] disableHTML = true` specifically because
`layouts/index.html` uses literal `{{ }}` as its own template syntax (the DC
runtime's binding syntax, e.g. `onClick="{{ event.onClick }}"` inside
`EventRow.dc.html`), which Hugo's HTML-aware minifier would otherwise try to
parse as Go template actions.

## Other things worth knowing

- `static/app.html` is an orphaned draft landing page under old branding
  ("HIDDEN HAND — Market Ops Sync") with a completely different visual
  design. Nothing links to it; it's not part of either frontend above.
- `scripts/digest.py` is a separate pipeline from the aggregator: it reads
  `data/events.json` and writes `static/digest.xml`, meant to be piped
  through a free Mailchimp RSS-to-email campaign. Its `SITE_URL` is still a
  placeholder domain.
- No git identity, hosting (Cloudflare Pages / GitHub Pages), or Mailchimp
  connection is configured yet — the repo builds and runs locally but isn't
  deployed anywhere.
