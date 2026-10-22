# book-deal-data

Compare conditional savings against required spending and renewal.

Status: **local source pilot**, version 0.1.0. Six manually invoked official
public sources now run through the shared bounded capture and lake replay lane.
There is no published remote, scheduler, hosted API, or consumer integration.
The CLI provides a machine-readable JSON contract, validates an explicit export,
and searches synthetic examples. It never falls back from live data to fixtures.

## Users and boundary

For people and small teams discovering deals and savings.
Offers requiring purchase or a commercial condition; zero-price claims belong to freebie.

Subcategories: coupon, cashback, rebate, discount, bundle, referral-promotion.

Domain-specific terms: `minimum_spend`, `discount_basis`, `redemption_limit`, `purchase_required`.
Each record represents one program/offer intake window. A repeat intake receives
a distinct source record ID. Cross-domain packages use `related_records` rather
than copying the same award into several products.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
book-deal-data contract
book-deal-data demo --open-only
book-deal-data demo --query "coupon"
book-deal-data validate src/book_deal_data/demo.json
python -m unittest discover -s tests -v
python -m pip install -e ".[dev]"  # pytest + pinned ruff
ruff check . && python -m pytest -q
uv sync --frozen --all-extras && uv run mypy  # locked env (uv.lock) as CI installs it
```

CI (`.github/workflows/ci.yml`) runs `ruff check`, the offline test suite and a
CLI smoke test on Python 3.10 and 3.13. `tests/test_registry.py` keeps
`sources.json`, the packaged `source*.json` configs and the contract in sync.

With dependencies already available, use `PYTHONPATH=src python3 -m book_deal_data`.
`demo` uses the fixed synthetic clock 2026-09-07T00:00:00Z unless `--as-of` is
provided. `--open-only` excludes closed, unknown-deadline, expired, stale (72h
default), and future-checked records. This is an availability filter; it does
not assert personal eligibility, selection probability, or a guaranteed payout.

Contract: `src/book_deal_data/schema.json` (`deal.v1`).
Unknown amounts, currencies, eligibility and deadlines remain unknown. Cash,
credit, discount, in-kind benefits and access are different value kinds. Never
sum them as cash income. Queries and validation are read-only and do not persist
provided files. The `live` label requires captured lineage, but validation alone
does not verify that referenced lake objects exist or prove source truth.

## Data ownership and source policy

Owner: bookchaowalit. Public program metadata only; no applications, personal
screening answers, financial credentials, cookies, or private transcripts.
See `sources.json` and the source policy under `src/`: Apple's public education
offer page is enabled for public metadata only. Its "through <date>" end date is
date-only (no time or zone), so the record keeps `deadline.kind = unknown` and
reports `status: closed` only from 00:00 UTC two days after that date, when the
day has ended in every time zone; before then status stays `unknown`. Exact source
permission and retention remain reviewed per source. No spending, account
creation or messaging.

Implemented flow: approved source pull → immutable landing bytes
and checksum → Bronze Parquet and manifest through the shared lake runtime →
versioned read-only contract → consumer pull. Each product owns its source
adapters and lake prefix. Producers never write into another app's database,
CRM, tasks, application tracker, or notification system.

## Official source pilots

The six enabled sources are listed in `sources.json` and `src/book_deal_data/source*.json`: [Apple education offer](https://www.apple.com/us-edu/store), [Microsoft Education](https://www.microsoft.com/en-us/education), [Rakuten](https://www.rakuten.com/), [ENERGY STAR Rebate Finder](https://www.energystar.gov/rebate-finder), [Steam bundles](https://store.steampowered.com/), and [Dropbox referral program](https://www.dropbox.com/refer).

## Remaining implementation gates

1. Keep the six source adapters fresh and add sanitized fixtures when a provider changes its public contract.
2. Expand field extraction and live quality monitoring without inferring a
   guaranteed saving, eligibility or redemption outcome.
3. Install independent deployment and retention/access controls; verify
   idempotent raw capture,
   Bronze lineage, quarantine and replay before serving real records.
4. Add live source tests and runtime monitoring.
5. Connect a read-only consumer. Personal eligibility, ranking, deadlines and
   application workflow belong to consumers with separate private storage.

No runtime port is reserved. The former `opportunity.v1` is archival; `job.v1` remains a separate job-data contract.
Breaking contract changes require a new version and a consumer migration.
There is no production deployment to roll back; discard demo output or restore
the previous contract version locally. Source permission, live availability,
lake replay and real eligibility are **unverified**, not passing gates.
