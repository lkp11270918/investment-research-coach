from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


COMPANIES = {
    "aapl": {"company": "Apple Inc.", "industry": "technology", "cik": "0000320193"},
    "wmt": {"company": "Walmart Inc.", "industry": "retail", "cik": "0000104169"},
    "jpm": {"company": "JPMorgan Chase & Co.", "industry": "banking", "cik": "0000019617"},
    "pfe": {"company": "Pfizer Inc.", "industry": "pharmaceuticals", "cik": "0000078003"},
    "xom": {"company": "Exxon Mobil Corporation", "industry": "energy", "cik": "0000034088"},
}

METRICS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "net_profit": ("NetIncomeLoss", "ProfitLoss"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
}


def build(source_dir: Path, output_dir: Path, manifest_path: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases, gold = [], {}
    for slug, company in COMPANIES.items():
        source_path = source_dir / f"{slug}-companyfacts.json"
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        compact = {"entityName": payload.get("entityName"), "cik": payload.get("cik"), "facts": []}
        for metric_name, tags in METRICS.items():
            fact = _latest_annual_fact(payload, tags)
            if fact is None:
                continue
            tag, unit, row = fact
            source_record = {"tag": tag, "unit": unit, **{key: row.get(key) for key in ("fy", "fp", "form", "filed", "start", "end", "val", "accn", "frame")}}
            compact["facts"].append(source_record)
            case_id = f"SEC-{slug.upper()}-{metric_name}"
            gold[case_id] = {"metric_name": metric_name, "period": str(row.get("fy") or row.get("end", ""))[:4], "value": row["val"], "unit": unit, "form": row.get("form"), "accession": row.get("accn")}
        compact_path = output_dir / f"{slug}-official-facts.json"
        compact_bytes = json.dumps(compact, ensure_ascii=False, indent=2).encode()
        compact_path.write_bytes(compact_bytes)
        digest = hashlib.sha256(compact_bytes).hexdigest()
        for item in compact["facts"]:
            metric_name = next(name for name, tags in METRICS.items() if item["tag"] in tags)
            case_id = f"SEC-{slug.upper()}-{metric_name}"
            cases.append({"case_id": case_id, "split": "validation" if slug in {"aapl", "jpm", "xom"} else "holdout", "metric": "financial_fact_accuracy", "industry": company["industry"], "company": company["company"], "modality": "structured_xbrl", "source": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json", "publisher": "U.S. Securities and Exchange Commission", "published_at": item.get("filed"), "usage_rights": "public_government_filing", "content_sha256": digest, "gold_label_path": "evals/real_cases/gold/sec_financial_gold.json", "local_source_path": str(compact_path)})
    gold_dir = output_dir.parent / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)
    (gold_dir / "sec_financial_gold.json").write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"] = [case for case in manifest.get("cases", []) if not str(case.get("case_id", "")).startswith("SEC-")] + cases
    manifest["status"] = "partial_real_corpus"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"companies": len(COMPANIES), "industries": len({item["industry"] for item in COMPANIES.values()}), "cases": len(cases)}


def _latest_annual_fact(payload: dict, tags: tuple[str, ...]):
    us_gaap = payload.get("facts", {}).get("us-gaap", {})
    candidates = []
    for tag in tags:
        concept = us_gaap.get(tag)
        if not concept: continue
        for unit, rows in concept.get("units", {}).items():
            if unit not in {"USD", "USD/shares", "pure"}: continue
            for row in rows:
                if row.get("form") == "10-K" and row.get("fp") == "FY" and isinstance(row.get("val"), (int, float)):
                    candidates.append((str(row.get("filed", "")), tag, unit, row))
    if not candidates: return None
    _, tag, unit, row = max(candidates, key=lambda item: (item[0], str(item[3].get("end", ""))))
    return tag, unit, row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("evals/real_cases/sources"))
    parser.add_argument("--output-dir", type=Path, default=Path("evals/real_cases/official_extracts"))
    parser.add_argument("--manifest", type=Path, default=Path("evals/real_cases/manifest.json"))
    args = parser.parse_args()
    print(json.dumps(build(args.source_dir, args.output_dir, args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
