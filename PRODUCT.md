---
title: Deals and savings Data Product Charter
status: local-source-pilot
created: 2026-08-08
updated: 2026-10-22
tags: [template, data-engineering, data-product, governance]
description: Outcome, consumers, ownership, contract, quality, privacy, and operating boundary for a data product.
---

# Data Product Charter

## Document control

| Field | Value |
|---|---|
| Data product ID/version | book-deal-data / deal.v1 |
| Product owner | bookchaowalit |
| Data owner/steward | bookchaowalit |
| Producer team | Domain repository |
| Status/review date | Local source pilot / 2026-09-08 |
| Evidence boundary | schema.json, source policy, capture adapter, fixtures and tests in this repository |

## Runtime status (verified 2026-10-22)

| What | Status |
|---|---|
| Capture entry point | `python -m book_deal_data.capture acquire|records|status` (needs `SOLO_DATA_LAKE_ROOT`, the shared `discovery.capture_runtime` v1 in data-lake-pipelines) |
| Who calls it | data-lake-pipelines `infra/scripts/discovery/portfolio.py acquire` for the 6 enabled source IDs in `systems/architecture/discovery-portfolio-v1.json`; that portfolio is wired to a 6-hourly Windows task (`setup_windows_task.ps1`). Whether the task is installed and running is **not verified** from this repo (owner decision D6 on the schedule host is open) [ต้องยืนยัน] |
| Hosted deployment | None. No port, no API, no cloud job |
| Error reporting | Sentry, opt-in: install the `sentry` extra and set `SENTRY_DSN`; a capture run that exits non-zero sends one event tagged `source_id` (no payload, no PII). No DSN is configured for this product yet [ต้องยืนยัน] |
| Contract | `book_deal_data` `schema.json` (v1 demo) and `schema-v2.json` (captured records); domain-owned, not part of the frozen `data-product-contracts-v2.yaml` port map (the old `opportunity.v1` synthesis is retired, BOO-248) |
| Quality gates in CI | ruff, ruff format, mypy (gradual, see pyproject), offline pytest with coverage ≥ 92%, CLI smoke on Python 3.10 and 3.13, shared security scan |

## Product contract

- Decision or user outcome: Compare conditional savings against required spending and renewal.
- Consumers and use cases: Discovery applications; integration planned.
- Source systems and lake layers: Six reviewed public offer pages (Apple education, Microsoft Education, Rakuten, ENERGY STAR Rebate Finder, Steam bundles, Dropbox referral) → immutable landing → Bronze through the shared local runtime.
- In scope/out of scope: Offers requiring purchase or a commercial condition; zero-price claims belong to freebie.
- Freshness, availability, and volume expectation: Target source review every 24h; open filter rejects checks older than 72h; no live SLA.
- Data classification, residency, retention, and access: Public program metadata only; no user profile; raw retention is private local operational storage.
- Quality thresholds and incident route: Contract, source-drift and replay tests pass; owner handles source failures and parser drift.
- Cost/capacity guardrail: Manual capture only; max 10,000 records per envelope.
- Versioning, deprecation, and migration policy: Draft v1; breaking changes version separately; no legacy migration or live consumer yet.

## Acceptance and ownership

| Gate | Evidence | Owner | Result/status |
|---|---|---|---|
| Contract | Versioned schema and compatibility rules | bookchaowalit | pass (local) |
| Quality | Checks and threshold report | bookchaowalit | pass (fixtures; live monitoring pending) |
| Lineage | Source-to-consumer map | bookchaowalit | pass (local capture) |
| Access/privacy | Classification and access review | bookchaowalit | pass (public metadata only) |
| Operations | Runbook, alert, replay, and recovery | bookchaowalit | partial (manual capture; no scheduler) |

## Approval

| Role | Name/date | Decision |
|---|---|---|
| Product/data owner |  | Approve charter / revise |
| Producer owner |  | Accept delivery boundary |
| Consumer representative |  | Accept use and SLA |
