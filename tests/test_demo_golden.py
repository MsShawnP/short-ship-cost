"""Demo golden lock — short-ship-cost.

The deployed dashboard renders committed JSON in web/public/data/. This locks the
cost JSON content (canonical-serialized SHA-256, stable across line endings) so
the client-mode conversion — purely additive (a new client_mode.py; nothing here
regenerates the JSON) — cannot drift the published site or its numbers.

If a SHA moves, STOP: a demo golden moved. Do not re-baseline without a logged
approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "web" / "public" / "data"

GOLDEN = {
    "cost_summary": "67ad75dd5aa7a1b2143040e58b09e277a8de841ff28aa3aad8bcd4167b0d61fb",
    "cost_by_retailer": "2857cf784fea4985a30ecb208a90b5325ad1277f5958f65e46759b8068dc6bb7",
    "meta": "8f70393bd091d97837a33f815a0d64a8dc0a95ad608aa2e9e73ec89261cf03f7",
}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_demo_json_content_unchanged(name):
    data = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
    blob = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == GOLDEN[name], (
        f"{name}.json content changed (sha256 {digest} != golden {GOLDEN[name]}). "
        "A demo golden moved — STOP and report before re-baselining."
    )


def test_forgone_revenue_headline_is_pinned():
    summary = json.loads((DATA / "cost_summary.json").read_text(encoding="utf-8"))
    by_dim = {row["dimension"]: row for row in summary}
    assert by_dim["forgone_revenue"]["total_cost"] == 523326.17
