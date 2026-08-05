"""Client-mode tests for Short-Ship Cost (checklist §6).

Skipped unless the shared ``lailara_engagement`` lib is installed. Fixtures
generated on the fly — no client identifiers, no committed data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("lailara_engagement")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import client_mode  # noqa: E402

# L1 Walmart: ordered 100 shipped 90 -> short 10; price 10 margin 4.
# L2 Costco:  ordered 200 shipped 200 -> short 0.
# L3 Walmart: ordered 50  shipped 30 -> short 20; price 20 margin 8.
LEDGER = (
    "line_id,retailer,sku,ship_date,units_ordered,units_shipped,unit_price,unit_margin\n"
    "L1,Walmart,CHP-AS-001,2023-01-07,100,90,10,4\n"
    "L2,Costco,CHP-AS-001,2023-01-14,200,200,10,4\n"
    "L3,Walmart,CHP-PS-002,2023-01-21,50,30,20,8\n"
)


def _write(d: Path, text=LEDGER, name="shipments.csv"):
    p = d / name
    p.write_text(text, encoding="utf-8")
    return p


def _cfg(d: Path, basis="revenue", columns=None):
    import yaml
    p = d / "engagement.demo.yml"
    p.write_text(yaml.safe_dump({
        "client": {"name": "Cinderhaven Provisions (demo)"}, "engagement": {"id": "T-1"},
        "as_of_date": "2026-01-02", "demo": True,
        "basis": {"forgone_basis": basis}, "columns": columns or {}}), encoding="utf-8")
    return p


def test_revenue_basis(tmp_path):
    inp = _write(tmp_path)
    res = client_mode.run(str(_cfg(tmp_path, "revenue")), str(inp), str(tmp_path / "out"))
    assert res["status"] == "ok"
    assert res["total_forgone"] == 500.00        # 10*10 + 0 + 20*20
    assert res["total_shorted_units"] == 30
    assert res["fill_rate_pct"] == 91.43         # 320/350
    assert res["basis"] == "revenue"


def test_margin_basis_values_differently(tmp_path):
    inp = _write(tmp_path)
    res = client_mode.run(str(_cfg(tmp_path, "margin")), str(inp), str(tmp_path / "out"))
    assert res["status"] == "ok"
    assert res["total_forgone"] == 200.00        # 10*4 + 0 + 20*8
    assert res["basis"] == "margin"


def test_deliverable_prints_the_basis_word(tmp_path):
    inp = _write(tmp_path)
    res = client_mode.run(str(_cfg(tmp_path, "margin")), str(inp), str(tmp_path / "out"))
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "forgone (contribution margin)" in html
    assert "Forgone basis" in html and "contribution margin" in html   # provenance
    assert "DRAFT" in html


def test_margin_basis_requires_unit_margin_column(tmp_path):
    import pandas as pd
    inp = tmp_path / "shipments.csv"
    pd.read_csv(_write(tmp_path, name="tmp.csv")).drop(columns=["unit_margin"]).to_csv(inp, index=False)
    res = client_mode.run(str(_cfg(tmp_path, "margin")), str(inp), str(tmp_path / "out"))
    assert res["status"] == "blocked"
    assert "unit_margin" in Path(res["readiness_report"]).read_text(encoding="utf-8")


def test_revenue_basis_tolerates_absent_unit_margin(tmp_path):
    import pandas as pd
    inp = tmp_path / "shipments.csv"
    pd.read_csv(_write(tmp_path, name="tmp.csv")).drop(columns=["unit_margin"]).to_csv(inp, index=False)
    res = client_mode.run(str(_cfg(tmp_path, "revenue")), str(inp), str(tmp_path / "out"))
    assert res["status"] == "ok"
    assert res["total_forgone"] == 500.00


def test_missing_forgone_basis_declaration_errors(tmp_path):
    import yaml
    inp = _write(tmp_path)
    cfg = tmp_path / "engagement.demo.yml"
    cfg.write_text(yaml.safe_dump({
        "client": {"name": "x"}, "engagement": {"id": "y"}, "as_of_date": "2026-01-02",
        "demo": True, "columns": {}}), encoding="utf-8")   # no basis.forgone_basis
    with pytest.raises(Exception):
        client_mode.run(str(cfg), str(inp), str(tmp_path / "out"))


def test_missing_units_shipped_blocks(tmp_path):
    import pandas as pd
    inp = tmp_path / "shipments.csv"
    pd.read_csv(_write(tmp_path, name="tmp.csv")).drop(columns=["units_shipped"]).to_csv(inp, index=False)
    res = client_mode.run(str(_cfg(tmp_path, "revenue")), str(inp), str(tmp_path / "out"))
    assert res["status"] == "blocked"


def test_header_mapping(tmp_path):
    text = (
        "Order Line,retailer,sku,ship_date,Qty Ordered,Qty Shipped,Unit Cost,unit_margin\n"
        "L1,Walmart,CHP-AS-001,2023-01-07,100,90,10,4\n"
    )
    inp = _write(tmp_path, text=text)
    cfg = _cfg(tmp_path, "revenue", columns={"line_id": "Order Line", "units_ordered": "Qty Ordered",
                                             "units_shipped": "Qty Shipped", "unit_price": "Unit Cost"})
    res = client_mode.run(str(cfg), str(inp), str(tmp_path / "out"))
    assert res["status"] == "ok"
    assert res["total_forgone"] == 100.00
