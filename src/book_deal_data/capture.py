"""Capture one reviewed public discount page through the shared lake runtime."""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

from .cli import resource, timestamp, validate
from .observability import init_sentry, report_exit

MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        1,
    )
}


def english_date(value):
    """'September 24, 2026' -> midnight UTC of that calendar day.

    Month names are matched explicitly so the host locale (which drives strptime
    %B) cannot change or break the parse.
    """
    match = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", value)
    if not match or match.group(1).casefold() not in MONTHS:
        raise ValueError("unsupported English date")
    return datetime(int(match.group(3)), MONTHS[match.group(1).casefold()], int(match.group(2)), tzinfo=timezone.utc)


class Text(HTMLParser):
    """Extract visible text while ignoring executable page content."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


REQUIRED_MARKERS = (
    "education",
    "apple gift card",
    "qualified purchasers",
    "eligible mac or ipad",
)


def _normalize_generic(raw, source, checked_at):
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    text = " ".join(" ".join(parser.parts).split())
    folded = text.casefold()
    markers = source.get("required_markers") or [source["title"]]
    if not all(marker.casefold() in folded for marker in markers):
        raise ValueError("generic deal source drift or challenge page")
    record_id = source["id"]
    item = {
        "id": record_id,
        "title": source["title"],
        "category": source["category"],
        "source_url": source["source_url"],
        "provider": source["provider"],
        "status": source.get("status", "unknown"),
        "deadline": {"kind": source.get("deadline_kind", "unknown"), "at": None},
        "eligible_countries": source.get("eligible_countries", ["GLOBAL"]),
        "eligibility_text": source["eligibility_text"],
        "value": {
            "kind": source.get("value_kind", "discount"),
            "amount": source.get("value_amount"),
            "currency": source.get("value_currency"),
            "guaranteed": source.get("value_guaranteed"),
        },
        "cost": {"fee_amount": None, "currency": None, "auto_renewal": None, "notes": source["cost_notes"]},
        "terms": {
            "minimum_spend": None,
            "discount_basis": source.get("discount_basis", "unknown"),
            "redemption_limit": "Not extracted; review the current official offer terms.",
            "purchase_required": source.get("purchase_required", True),
            **source.get("normalized_terms", {}),
        },
        "related_records": [],
        "provenance": {
            "evidence_kind": "captured",
            "source_id": source["id"],
            "source_record_id": record_id,
            "checked_at": checked_at,
            "raw_object_key": None,
            "bronze_manifest_key": None,
        },
    }
    return {
        "schema_version": source["schema_version"],
        "source": source["product"],
        "retrieved_at": checked_at,
        "data_status": "live",
        "items": [item],
    }


def normalize(raw, source, checked_at):
    """Turn one reviewed public offer page into one conservative record."""
    if source.get("generic_html"):
        return _normalize_generic(raw, source, checked_at)
    if source["id"] != "apple-education-college-offer-2026":
        raise ValueError("unknown deal source")
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    text = " ".join(" ".join(parser.parts).split())
    folded = text.casefold()
    if not all(marker.casefold() in folded for marker in REQUIRED_MARKERS):
        raise ValueError("Apple education source drift or challenge page")
    deadline = {"kind": "unknown", "at": None}
    status = "unknown"
    match = re.search(r"through ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if match:
        end_day = english_date(match.group(1))
        # The page gives a date without a cutoff time or zone. That day has ended
        # in every zone (UTC-12..UTC+14) by 00:00 UTC two days later, so only then
        # is "closed" certain; before that the status stays unknown.
        if timestamp(checked_at) >= end_day + timedelta(days=2):
            status = "closed"
    item = {
        "id": source["id"],
        "title": source["title"],
        "category": source["category"],
        "source_url": source["source_url"],
        "provider": source["provider"],
        "status": status,
        "deadline": deadline,
        "eligible_countries": ["US"],
        "eligibility_text": source["eligibility_text"],
        "value": {
            "kind": "discount",
            "amount": None,
            "currency": None,
            "guaranteed": False,
        },
        "cost": {
            "fee_amount": None,
            "currency": None,
            "auto_renewal": None,
            "notes": source["cost_notes"],
        },
        "terms": {
            "minimum_spend": None,
            "discount_basis": "percentage",
            "redemption_limit": (
                "Select products and education discount terms apply; review exclusions before purchase. "
                f"Published end date: {match.group(1) if match else 'not found'}. "
                "The source does not specify a cutoff time or time zone."
            ),
            "purchase_required": True,
        },
        "related_records": [],
        "provenance": {
            "evidence_kind": "captured",
            "source_id": source["id"],
            "source_record_id": source["id"],
            "checked_at": checked_at,
            "raw_object_key": None,
            "bronze_manifest_key": None,
        },
    }
    return {
        "schema_version": source["schema_version"],
        "source": source["product"],
        "retrieved_at": checked_at,
        "data_status": "live",
        "items": [item],
    }


def source_config(source_id=None):
    if source_id is None:
        return resource("source.json")
    if not re.fullmatch(r"[a-z0-9-]+", source_id):
        raise ValueError("invalid source id")
    base = resource("source.json")
    if base["id"] == source_id:
        return base
    try:
        return resource("source-" + source_id + ".json")
    except FileNotFoundError:
        raise ValueError("unknown source id") from None


def main(argv=None):
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--source-id")
    selected, remaining = selector.parse_known_args(argv)
    root = os.environ.get("SOLO_DATA_LAKE_ROOT")
    if not root:
        print("Set SOLO_DATA_LAKE_ROOT to the local shared capture/lake runtime.", file=sys.stderr)
        return 2
    runtime = Path(root).resolve() / "infra/scripts"
    if not (runtime / "discovery/capture_runtime.py").is_file():
        print("Shared discovery runtime is unavailable.", file=sys.stderr)
        return 2
    sys.path.insert(0, str(runtime))
    from discovery.capture_runtime import VERSION, run

    if VERSION != 1:
        raise RuntimeError("unsupported shared capture runtime")
    source = source_config(selected.source_id)
    sentry = init_sentry(source["id"])
    return report_exit(sentry, source["id"], run(source, normalize, validate, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
