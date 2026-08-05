"""Client-mode CLI for Short-Ship Cost.

Prices a client's fulfillment shortfall from their own shipment lines: units
ordered vs shipped, the fill rate, and the forgone value of what wasn't shipped —
valued at the client's chosen **basis** (wholesale revenue or contribution
margin). Runs locally via the shared ``lailara_engagement`` scaffold.

This is a money tool: the forgone-value basis (revenue vs margin) is a REQUIRED
config declaration and is printed next to every figure, so a revenue number can
never be read as margin. Not POS-shaped (shipment lines, not weekly scans), so it
uses the generic column specs.

Required input: a **shipment-line ledger** — one row per (order line) with units
ordered/shipped and the unit price (and unit margin if the basis is margin). A
missing required column blocks with a branded Data Readiness Report; a clean run
writes a draft-watermarked, provenance-footed **Short-Ship Cost Summary** (HTML)
+ a per-retailer CSV to ``client-output/``.

Usage:
    python client_mode.py --config engagement.yml --input client-data/shipments.csv \
        [--out client-output] [--final]
"""

from __future__ import annotations

import argparse
import csv as _csv
import html
from pathlib import Path

import pandas as pd

from lailara_engagement import (
    ColumnSpec,
    ConfigError,
    PreflightSpec,
    build_provenance,
    load_config,
    read_table,
    run_preflight,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.pos import to_frame
from lailara_engagement.provenance import Provenance

TOOL = "short-ship-cost"
TOOL_VERSION = "1.0"
FORGONE_BASES = {"revenue": "wholesale revenue", "margin": "contribution margin"}


def resolve_forgone_basis(config) -> str:
    name = (config.basis or {}).get("forgone_basis") or config.raw.get("forgone_basis")
    if not name:
        raise ConfigError(["`basis.forgone_basis` is required — set 'revenue' (wholesale "
                           "price) or 'margin' (contribution margin) so the forgone value "
                           "prints its basis"])
    if name not in FORGONE_BASES:
        raise ConfigError([f"`basis.forgone_basis` {name!r} must be one of {sorted(FORGONE_BASES)}"])
    return name


def _ledger_spec(basis: str) -> PreflightSpec:
    cols = [
        ColumnSpec(name="line_id", dtype="identifier", required=True, unique=True,
                   description="unique order-line id", spec_ref="INPUT-SPEC §Shipments"),
        ColumnSpec(name="retailer", dtype="string", required=True, spec_ref="INPUT-SPEC §Shipments"),
        ColumnSpec(name="sku", dtype="identifier", required=True, spec_ref="INPUT-SPEC §Shipments"),
        ColumnSpec(name="ship_date", dtype="date", required=True,
                   description="ship date; drives the window", spec_ref="INPUT-SPEC §Shipments"),
        ColumnSpec(name="units_ordered", dtype="number", required=True, not_negative=True,
                   spec_ref="INPUT-SPEC §Shipments"),
        ColumnSpec(name="units_shipped", dtype="number", required=True, not_negative=True,
                   spec_ref="INPUT-SPEC §Shipments"),
        # unit_price required always (revenue basis); unit_margin required only when
        # the basis is margin — so a margin engagement can't silently value at revenue.
        ColumnSpec(name="unit_price", dtype="number", required=True, not_negative=True,
                   description="wholesale price per unit", spec_ref="INPUT-SPEC §Shipments"),
        ColumnSpec(name="unit_margin", dtype="number", required=(basis == "margin"),
                   allow_blank=(basis != "margin"), not_negative=True,
                   description="contribution margin per unit (required when basis=margin)",
                   spec_ref="INPUT-SPEC §Shipments"),
    ]
    return PreflightSpec(tool=TOOL, version=TOOL_VERSION, columns=cols)


def compute_shortship(frame: pd.DataFrame, basis: str):
    val_col = "unit_price" if basis == "revenue" else "unit_margin"
    shorted = (frame["units_ordered"] - frame["units_shipped"]).clip(lower=0)
    frame = frame.assign(shorted_units=shorted,
                         forgone=(shorted * frame[val_col]).round(2))
    total_ordered = float(frame["units_ordered"].sum())
    total_shipped = float(frame["units_shipped"].sum())
    rows = []
    for retailer, g in frame.groupby(frame["retailer"].fillna("(unspecified)")):
        ordv, shipv = float(g["units_ordered"].sum()), float(g["units_shipped"].sum())
        rows.append({"retailer": str(retailer),
                     "units_ordered": int(ordv), "units_shipped": int(shipv),
                     "shorted_units": int(g["shorted_units"].sum()),
                     "fill_rate_pct": round(shipv / ordv * 100, 2) if ordv else 100.0,
                     "forgone": round(float(g["forgone"].sum()), 2)})
    rows.sort(key=lambda r: r["forgone"], reverse=True)
    summary = {
        "total_forgone": round(float(frame["forgone"].sum()), 2),
        "total_shorted_units": int(frame["shorted_units"].sum()),
        "fill_rate_pct": round(total_shipped / total_ordered * 100, 2) if total_ordered else 100.0,
        "n_lines": len(frame), "basis": basis,
    }
    return summary, rows


def _fmt_dollars(v):
    return "—" if v is None else f"${v:,.0f}"


def _deliverable_html(config, summary, retailers, basis, window_label, limitations,
                      provenance: Provenance, *, draft: bool) -> str:
    esc = html.escape
    draft_class = " ll-draft" if draft else ""
    basis_word = FORGONE_BASES[basis]
    rows = "".join(
        f"<tr><td>{esc(r['retailer'])}</td><td class=num>{r['units_ordered']:,}</td>"
        f"<td class=num>{r['units_shipped']:,}</td><td class=num>{r['fill_rate_pct']:.2f}%</td>"
        f"<td class=num>{_fmt_dollars(r['forgone'])}</td></tr>"
        for r in retailers
    )
    lim = "".join(f"<li>{esc(x)}</li>" for x in limitations)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Short-Ship Cost Summary — {esc(config.client_name)}</title><style>{_css(draft)}</style></head>
<body class="{draft_class.strip()}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · Short-Ship Cost</div>
  <h1 class=ll-title>Short-Ship Cost Summary</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>As of</span> {esc(config.as_of_date.isoformat())}</div>
    <div><span class=ll-k>Prepared by</span> {esc(config.prepared_by)}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{_fmt_dollars(summary['total_forgone'])} forgone ({esc(basis_word)})</div>
  <div>{summary['fill_rate_pct']:.2f}% fill rate · {summary['total_shorted_units']:,} units short
       across {summary['n_lines']:,} order lines</div>
  <div class=ll-basis>Basis: forgone value at <strong>{esc(basis_word)}</strong>
       (shorted units × unit {basis}) · Window: {esc(window_label)}</div>
</section>
<section class=ll-section>
  <h2 class=ll-h2>By retailer</h2>
  <table class=ll-table><thead><tr><th>Retailer</th><th>Ordered</th><th>Shipped</th>
  <th>Fill rate</th><th>Forgone ({esc(basis_word)})</th></tr></thead><tbody>{rows}</tbody></table>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Data limitations</h2>
  <ul class=ll-limitations>{lim}</ul>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}
*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:34px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_RED_SURFACE};color:{P.LL_RED_DARK}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:22px}}
.ll-basis{{font-size:12px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ll-table th{{text-align:left;background:{P.LL_CHICAGO};color:#fff;padding:8px 12px}}
.ll-table td{{padding:8px 12px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-limitations{{margin:0;padding-left:20px}}.ll-limitations li{{margin-bottom:6px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def run(config_path: str, input_path: str, out_dir: str, *, final: bool = False) -> dict:
    config = load_config(config_path)
    basis = resolve_forgone_basis(config)
    read = read_table(input_path)
    spec = _ledger_spec(basis)
    report = run_preflight(read, spec, config)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION, inputs=[read], config=config,
        validation_status=validation_status_label(report.status, report.n_warnings),
        extra={"Forgone basis": FORGONE_BASES[basis]})
    if not report.passed:
        paths = write_report(report, config, str(out), provenance=provenance, draft=not final,
                             basename="data-readiness-report", title="Short-Ship Data Readiness Report")
        return {"status": "blocked", "readiness_report": paths["html"]}

    frame = to_frame(read, report, spec)
    summary, retailers = compute_shortship(frame, basis)
    first, last = frame["ship_date"].min(), frame["ship_date"].max()
    window_label = f"ship dates {first.strftime('%b %d, %Y')} – {last.strftime('%b %d, %Y')}"

    limitations = [f.message for f in report.findings if f.severity == "warning"]
    if not limitations:
        limitations.append("No warnings — the shipment ledger passed preflight cleanly.")

    csv_path = out / "short-ship-by-retailer.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(retailers[0].keys()) if retailers else ["retailer"])
        w.writeheader(); w.writerows(retailers)
    html_path = out / "short-ship-cost-summary.html"
    html_path.write_text(_deliverable_html(config, summary, retailers, basis, window_label,
                                            limitations, provenance, draft=not final), encoding="utf-8")
    return {"status": "ok", **summary, "report": str(html_path), "csv": str(csv_path),
            "n_warnings": report.n_warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="short-ship-cost client mode")
    ap.add_argument("--config", required=True); ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="client-output"); ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.input, args.out, final=args.final)
    if result["status"] == "blocked":
        print(f"BLOCKED — data not ready. See {result['readiness_report']}")
        return 3
    print(f"{_fmt_dollars(result['total_forgone'])} forgone ({FORGONE_BASES[result['basis']]}) · "
          f"{result['fill_rate_pct']:.2f}% fill across {result['n_lines']:,} lines")
    print(f"report -> {result['report']}\ncsv    -> {result['csv']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
