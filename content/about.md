---
title: "About"
description: "What Goldirham Whisper tracks, where the dates come from, and how to read an entry."
layout: "about"
---

Goldirham Whisper is a calendar of the dates that headline economic calendars leave out:
exchange maintenance windows, trading-system releases, market holidays, expiry and roll dates,
index reviews, and statistical releases below the headline tier.

## What is tracked

- **Exchange operations.** Maintenance windows, system releases, test and failover days, holiday
  closures and early closes, quarterly expiries and rolls, and changes to auction or price-band
  parameters.
- **Second-tier statistics.** Releases that rarely lead the news: services price indices,
  business surveys, trade and capital-flow tables, central-bank publications, and the
  supplementary tables that accompany bigger releases.

The best-known releases, such as consumer prices, payrolls and most rate decisions, are largely
left out. They are covered well elsewhere.

## Why

A maintenance window, a parameter change or a holiday closure seldom makes the news, but it
changes how a market behaves on that day. The dates are public. They are scattered across
exchange notices and release calendars, and this site collects them in one list.

## Where the dates come from

A script runs every six hours on GitHub Actions. It reads public calendars and RSS feeds that
need no API key: the Japan Exchange Group holiday calendar, the ONS release calendar, and feeds
from the Bank of England, the Bank of Canada, the ECB and the SEC. The central-bank and SEC feeds
are filtered by keyword so that only statistical and market-structure items remain. Exchange
notices without a usable feed are added by hand.

Everything is merged into one file, which is also published as it is:

- [/events.json](/events.json): every event, as JSON
- [/index.xml](/index.xml): upcoming dates, as RSS
- [/digest.xml](/digest.xml): a weekly digest, as RSS

<p data-sources></p>

## Reading an entry

Each entry is an all-day date in the home time zone of the exchange or issuer. Exchange dates
are marked with a filled dot and economic releases with an open ring. The two-letter code is the
country or region of the source; INTL marks sources without a country assigned. Every entry links
to the notice it came from and can be added to Google Calendar or downloaded as an .ics file.

Issuers move and cancel dates, and this list can lag behind them. Check the source notice before
relying on a date.

## Not investment advice

This is a reference calendar compiled from public information. It is not investment advice.
