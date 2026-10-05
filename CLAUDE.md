# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Goldirham Whisper — a static Hugo site tracking obscure economic releases and
exchange infrastructure dates ("dates that move markets first"). No build
tooling beyond Hugo itself: fonts and the globe's d3-geo/topojson/world-atlas
dependencies are loaded from jsDelivr, the app is vanilla JS — there is no
`package.json`, and no automated tests.

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

The whole app — calendar, exchanges, economics, search, about, not-found and
the single-event modal — is one self-contained document,
`layouts/partials/app.html` (vanilla JS module, inline CSS design tokens).
It's included from thin Hugo templates, each passing which view should be
active on load:

- `layouts/index.html` → `{{ partial "app.html" (dict "view" "calendar" "page" .) }}`
- `layouts/economics/list.html`, `layouts/exchanges/list.html`,
  `layouts/search/list.html` → their own view
- `layouts/_default/about.html` → `"about"` (selected by `layout: "about"` in
  `content/about.md`)
- `layouts/404.html` → `"notfound"`
- `layouts/event/list.html` → `"calendar"` (a single event is a modal
  overlay, not a route: `boot()` opens the modal for `location.hash`, so
  `/event/#slug` and `/#slug` both work)

Client-side nav (`data-act="nav"`) re-renders `#app` without a reload and
uses `history.pushState`, so each view keeps a real URL and back/forward work
(`popstate` handler). Data loads once via dynamic `import()` of
`static/data/events-data.js` + `flags-data.js`, not from any Hugo template
variable. The About view's prose is `content/about.md`, embedded on every
page as `<template id="about-src">` so client-side nav can render it.

Some generated slugs repeat across years; at load the app appends
`-YYYY-MM-DD` to later duplicates so each row opens its own event. The real
fix belongs in `aggregator.py`.

Flag emoji are never rendered (they show as bare letters on Windows):
`countryCode()` turns `flags-data.js`'s emoji into ISO-2 codes ("US", "EU";
🌐 → "INTL").

Search (`searchResultsHTML()`) is weighted substring matching that requires
every typed term — no fuzzy matching. Good enough for ~100 events.

**Design tokens** (`--paper`, `--paper-2`, `--ink`, `--ink-2`, `--ink-3`,
`--rule`, `--accent`, `--ex`, `--ec`) are defined on `:root` with dark
values under `prefers-color-scheme: dark`. Exchange = filled dot in `--ex`,
economics = hollow ring in `--ec`. Fonts: Newsreader (display), IBM Plex
Sans (UI), IBM Plex Mono (dates/numbers), from jsDelivr @fontsource.

**Globe** (`static/js/globe.js`): `mountGlobe(container, { events,
onSelectPlace })` → `{ update, highlight, destroy }`. Canvas orthographic
globe (d3-geo + topojson-client + world-atlas land-110m from jsDelivr) with
one marker per city. `SOURCE_LOCATIONS` (built from the `CITIES` table) maps
exact `event.source` strings to a city — a third hand-maintained
source-keyed mapping alongside `GW_FLAGS`; a new source isn't plotted until
it's added there. It reads the design tokens from computed style, injects
its own `.gw-globe-*` styles, and renders a visually hidden button list for
keyboard/screen-reader use. `app.html` mounts it only on the calendar view
(`startGlobe()` / `stopGlobe()` around `render()`); selecting a place sets
`S.place` and filters the agenda to that city's sources. If the module or
its CDN imports fail, the slot hides and the agenda still works.

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
