---
title: "About"
description: "The methodology behind the Goldirham Whisper — what it tracks, why it exists, and who it is for."
---

Every matching engine goes down. Every settlement system gets patched. Every national statistical
office has a quiet release nobody screenshotted. Goldirham Whisper logs those dates —
and only those dates.

The mainstream calendar is a theatre of the obvious. CPI, payrolls, FOMC — by the time a release
has a countdown app, its alpha is spent. The dates that actually force desks to reprice are the
ones that happen *inside* the plumbing:

{{< terminal >}}
$ watch --feed live --type infrastructure
  2026-08-22  NYSE            Pillar core maintenance window
  2026-08-24  CME             Globex quarterly roll — Sep list
  2026-08-28  Nasdaq Nordic   ITCH protocol header migration v3.1
  2026-09-18  Eurex           Quarterly futures expiry — Sep fixings
  2026-09-18  LSE             FTSE Russell quarterly rebalance
  2026-10-01  Bank of Japan   Tankan — Q3 survey release
{{< /terminal >}}

Settlement batches, matching-engine releases, index rebalance effective dates, failover drills,
expiry rotations, second-tier statistics. The infrastructure of price discovery, logged daily.

## What gets tracked

- **Exchange infrastructure** — maintenance windows, system releases, test/drill days, holiday
  and early-close schedules, quarter-end expiry and roll cycles, auction parameter changes.
- **Second-tier economics** — the releases consensus desks skim past: TIC flows, regional Fed
  surveys, factory orders, trade balances, purchasing-manager indices from secondary issuers.

We deliberately skip the usual suspects. If Bloomberg runs a countdown ticker on it, we don't.

## How the data gets here

A Python aggregator (`scripts/aggregator.py`) runs every six hours via GitHub Actions and pulls
public, keyless iCal/RSS feeds straight from the venues and statistical agencies. Everything is
normalised into a single `data/events.json` that this site renders with zero servers. The same
file is published raw at `/events.json` and as RSS at `/index.xml`.

Which means: no paywalls, no API keys, no corporate sponsors, no latency. And no excuses for the
desk to say they never saw the maintenance window.

## Who this is for

Traders whose P&L eats the spread between news and reaction. Ops teams that have ever widened
their gloves around a known 03:00 UTC window. Anyone who has ever watched a mispriced fill arrive
because an exchange moved its auction parameters while the street slept.

This is not investment advice. It is a log of when the machinery is scheduled to move.

— *The Goldirham Whisper*