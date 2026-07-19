from __future__ import annotations

import math
import re
from collections import defaultdict

from .models import Confidence, EvidenceCategory, EvidenceItem, FinancialCalculationRecord, SourceRef, VerificationStatus


UNIT_SCALE = {"元": 1.0, "千元": 1_000.0, "万元": 10_000.0, "百万元": 1_000_000.0, "亿元": 100_000_000.0, "元/股": 1.0, "USD": 1.0, "USD/shares": 1.0, "%": 1.0}


def calculate_financial_metrics(evidence: list[EvidenceItem]) -> tuple[list[FinancialCalculationRecord], list[EvidenceItem]]:
    indexed: dict[tuple[str, str], EvidenceItem] = {}
    series: dict[str, list[tuple[int, EvidenceItem, float]]] = defaultdict(list)
    for item in evidence:
        if not item.metric_name or not item.period or not isinstance(item.metric_value, (int, float)):
            continue
        value = _base_value(float(item.metric_value), item.unit)
        indexed.setdefault((item.metric_name, item.period), item)
        year = _year(item.period)
        if year is not None:
            series[item.metric_name].append((year, item, value))

    records: list[FinancialCalculationRecord] = []
    derived: list[EvidenceItem] = []
    for period in sorted({period for _, period in indexed}):
        _binary(records, derived, indexed, period, "free_cash_flow_calculated", "operating_cash_flow", "capital_expenditure", lambda left, right: left - right, "operating_cash_flow - capital_expenditure", "元")
        _binary(records, derived, indexed, period, "dividend_payout_ratio", "dividend", "net_profit", _safe_div_percent, "dividend / net_profit * 100", "%")
        _binary(records, derived, indexed, period, "cash_conversion_ratio", "operating_cash_flow", "net_profit", _safe_div_percent, "operating_cash_flow / net_profit * 100", "%")
        _binary(records, derived, indexed, period, "debt_to_asset_ratio_calculated", "total_liabilities", "total_assets", _safe_div_percent, "total_liabilities / total_assets * 100", "%")
        _binary(records, derived, indexed, period, "roe_calculated", "net_profit", "shareholders_equity", _safe_div_percent, "net_profit / shareholders_equity * 100", "%")
        _binary(records, derived, indexed, period, "dividend_yield", "dividend", "market_cap", _safe_div_percent, "dividend / market_cap * 100", "%")
        _binary(records, derived, indexed, period, "dividend_yield_per_share", "dividend_per_share", "share_price", _safe_div_percent, "dividend_per_share / share_price * 100", "%")

    for metric, points in series.items():
        ordered = sorted({year: (item, value) for year, item, value in points}.items())
        for (previous_year, (previous_item, previous_value)), (year, (item, value)) in zip(ordered, ordered[1:]):
            if previous_value == 0:
                records.append(_failed(f"{metric}_yoy", str(year), "(current - previous) / abs(previous) * 100", [previous_item.evidence_id, item.evidence_id], "previous value is zero"))
                continue
            result = (value - previous_value) / abs(previous_value) * 100
            _append(records, derived, f"{metric}_yoy", str(year), result, "%", f"({metric}_{year} - {metric}_{previous_year}) / abs({metric}_{previous_year}) * 100", [previous_item, item])
        if len(ordered) >= 2:
            first_year, (first_item, first_value) = ordered[0]
            last_year, (last_item, last_value) = ordered[-1]
            years = last_year - first_year
            if years > 0 and first_value > 0 and last_value >= 0:
                cagr = (math.pow(last_value / first_value, 1 / years) - 1) * 100
                _append(records, derived, f"{metric}_cagr", f"{first_year}-{last_year}", cagr, "%", f"({metric}_{last_year} / {metric}_{first_year}) ^ (1 / {years}) - 1", [first_item, last_item])
    return records, derived


def _binary(records, derived, indexed, period, output, left_name, right_name, function, formula, unit) -> None:
    left, right = indexed.get((left_name, period)), indexed.get((right_name, period))
    if not left or not right:
        return
    try:
        value = function(_base_value(float(left.metric_value), left.unit), _base_value(float(right.metric_value), right.unit))
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        records.append(_failed(output, period, formula, [left.evidence_id, right.evidence_id], str(exc)))
        return
    _append(records, derived, output, period, value, unit, formula, [left, right])


def _append(records, derived, metric, period, value, unit, formula, inputs) -> None:
    rounded = round(value, 6)
    input_ids = [item.evidence_id for item in inputs]
    records.append(FinancialCalculationRecord(metric_name=metric, period=period, value=rounded, unit=unit, formula=formula, input_evidence_ids=input_ids))
    refs: list[SourceRef] = []
    for item in inputs:
        refs.extend(item.source_refs)
    derived.append(EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement=f"确定性计算：{period} {metric} = {rounded}{unit}", source_refs=_dedupe_refs(refs), period=period, metric_name=metric, metric_value=rounded, unit=unit, confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED, notes=f"公式：{formula}；输入证据：{', '.join(input_ids)}"))


def _failed(metric, period, formula, input_ids, error) -> FinancialCalculationRecord:
    return FinancialCalculationRecord(metric_name=metric, period=period, formula=formula, input_evidence_ids=input_ids, status="failed", error=error)


def _base_value(value: float, unit: str | None) -> float:
    return value * UNIT_SCALE.get(unit or "元", 1.0)


def _safe_div_percent(left: float, right: float) -> float:
    if right == 0:
        raise ZeroDivisionError("denominator is zero")
    return left / right * 100


def _year(period: str) -> int | None:
    match = re.search(r"20\d{2}", period)
    return int(match.group()) if match else None


def _dedupe_refs(refs: list[SourceRef]) -> list[SourceRef]:
    seen: set[tuple] = set()
    result: list[SourceRef] = []
    for ref in refs:
        key = (ref.source_id, ref.page, ref.sheet, ref.row_id, ref.cell_range, ref.excerpt)
        if key not in seen:
            seen.add(key)
            result.append(ref)
    return result
