from __future__ import annotations

import json
from pathlib import Path

from backend.financial_parser import extract_structured_financial_evidence
from backend.models import SourceDocument, SourceType


LABELS = {"revenue": "营业收入", "net_profit": "净利润", "operating_cash_flow": "经营现金流", "total_assets": "总资产", "total_liabilities": "总负债"}


def run(source_dir: Path = Path("evals/real_cases/official_extracts"), gold_path: Path = Path("evals/real_cases/gold/sec_financial_gold.json")) -> dict:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    results = []
    for path in sorted(source_dir.glob("*-official-facts.json")):
        slug = path.name.split("-", 1)[0].upper()
        expected = {case_id: value for case_id, value in gold.items() if case_id.startswith(f"SEC-{slug}-")}
        rows = ["指标 | 年度 | 数值"]
        for case_id, item in expected.items():
            rows.append(f"{LABELS[item['metric_name']]} | {item['period']}年 | {item['value']}USD")
        evidence = extract_structured_financial_evidence([SourceDocument(title=path.name, source_type=SourceType.FINANCIAL_TABLE, content="\n".join(rows))])
        actual = {(item.metric_name, str(item.period or "")[:4]): (item.metric_value, item.unit) for item in evidence}
        for case_id, item in expected.items():
            found = actual.get((item["metric_name"], item["period"]))
            results.append({"case_id": case_id, "passed": bool(found and float(found[0]) == float(item["value"]) and found[1] == item["unit"]), "expected": item, "actual": found})
    score = round(sum(item["passed"] for item in results) / max(len(results), 1) * 100, 1)
    return {"suite": "sec_official_financial_facts", "evidence_level": "real_public_filing", "passed": len(results) >= 20 and score >= 95, "case_count": len(results), "score": score, "results": results}


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
