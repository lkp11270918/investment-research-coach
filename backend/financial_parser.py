from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .models import Confidence, EvidenceCategory, EvidenceItem, SourceDocument, SourceRef, SourceType, VerificationStatus


@dataclass(frozen=True)
class FinancialMetricSpec:
    metric_name: str
    aliases: tuple[str, ...]
    default_unit: str | None = None


FINANCIAL_METRICS: tuple[FinancialMetricSpec, ...] = (
    FinancialMetricSpec("revenue", ("营收", "营业收入", "收入合计", "revenue", "sales"), "元"),
    FinancialMetricSpec("net_profit", ("净利润", "归母净利润", "母公司股东的净利润", "net profit"), "元"),
    FinancialMetricSpec("operating_cash_flow", ("经营现金流", "经营活动现金流", "经营活动产生的现金流量净额", "cfo"), "元"),
    FinancialMetricSpec("free_cash_flow", ("自由现金流", "fcf", "free cash flow"), "元"),
    FinancialMetricSpec("dividend_per_share", ("每股股利", "每股分红", "dividend per share"), "元/股"),
    FinancialMetricSpec("dividend", ("现金分红", "分红总额", "股利总额", "dividend"), "元"),
    FinancialMetricSpec("debt_to_asset_ratio", ("资产负债率", "debt to asset", "liability ratio"), "%"),
    FinancialMetricSpec("interest_bearing_debt", ("有息负债", "带息负债", "interest-bearing debt"), "元"),
    FinancialMetricSpec("roe", ("roe", "净资产收益率", "加权平均净资产收益率"), "%"),
    FinancialMetricSpec("non_recurring_pnl", ("非经常性损益", "非经损益", "non-recurring"), "元"),
    FinancialMetricSpec("accounts_receivable", ("应收账款", "应收款项", "accounts receivable"), "元"),
    FinancialMetricSpec("inventory", ("存货", "inventory"), "元"),
    FinancialMetricSpec("capital_expenditure", ("资本开支", "资本性支出", "购建固定资产、无形资产和其他长期资产支付的现金", "capex"), "元"),
    FinancialMetricSpec("total_assets", ("资产总计", "总资产", "total assets"), "元"),
    FinancialMetricSpec("total_liabilities", ("负债合计", "总负债", "total liabilities"), "元"),
    FinancialMetricSpec("shareholders_equity", ("股东权益合计", "所有者权益合计", "净资产", "shareholders equity"), "元"),
    FinancialMetricSpec("market_cap", ("总市值", "市值", "market cap"), "元"),
    FinancialMetricSpec("share_price", ("股价", "收盘价", "share price"), "元/股"),
    FinancialMetricSpec("eps", ("每股收益", "基本每股收益", "稀释每股收益", "eps", "earnings per share"), "元/股"),
    FinancialMetricSpec("book_value_per_share", ("每股净资产", "每股账面价值", "book value per share", "bvps"), "元/股"),
    FinancialMetricSpec("shares_outstanding", ("总股本", "期末股份总数", "已发行股份", "shares outstanding"), "股"),
    FinancialMetricSpec("gross_profit", ("毛利润", "毛利", "gross profit"), "元"),
    FinancialMetricSpec("selling_expense", ("销售费用", "selling expense"), "元"),
)


_PERIOD_RE = re.compile(r"(?<!\d)(20\d{2}(?:\s*[年/-]\s*(?:Q[1-4]|[一二三四]季度|H[12]|半年度|年度|年报|[01]?\d月)?)?|FY\s*20\d{2}|20\d{2}\s*Q[1-4])(?!\d)", re.I)
_NUMBER_RE = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?")


def extract_structured_financial_evidence(documents: Iterable[SourceDocument]) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for doc in documents:
        if not _looks_like_financial_document(doc):
            continue
        header_periods: list[str | None] = []
        for row_index, row in enumerate(_iter_table_rows(doc.content), start=1):
            row_periods = [_normalize_period(cell) for cell in _split_cells(row)]
            metric = _match_metric(row)
            if metric is None:
                if any(row_periods):
                    header_periods = row_periods
                continue
            coordinate = _source_coordinate(doc, row, row_index)
            for period, raw_value, unit in _extract_values_from_row(row, metric, header_periods):
                evidence.append(
                    EvidenceItem(
                        category=EvidenceCategory.FINANCIAL_FACT,
                        statement=_statement(metric.metric_name, period, raw_value, unit, doc.title),
                        source_refs=[
                            SourceRef(
                                source_id=doc.source_id,
                                excerpt=row[:500],
                                page=coordinate["page"],
                                paragraph_id=coordinate["paragraph_id"],
                                sheet=coordinate["sheet"],
                                row_id=coordinate["row_id"],
                                url=doc.url,
                            )
                        ],
                        period=period,
                        metric_name=metric.metric_name,
                        metric_value=_coerce_number(raw_value),
                        unit=unit or metric.default_unit,
                        confidence=Confidence.HIGH,
                        verification_status=VerificationStatus.VERIFIED,
                        notes="由财务表结构化解析器从 Excel/CSV 表格行抽取。",
                    )
                )
    return _dedupe_evidence(evidence)


def expected_financial_metric_names() -> list[str]:
    return [metric.metric_name for metric in FINANCIAL_METRICS]


def _looks_like_financial_document(doc: SourceDocument) -> bool:
    if doc.source_type == SourceType.FINANCIAL_TABLE:
        return True
    text = doc.content.lower()
    hits = sum(1 for metric in FINANCIAL_METRICS if any(alias.lower() in text for alias in metric.aliases))
    return hits >= 2


def _iter_table_rows(content: str) -> Iterable[str]:
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("## "):
            continue
        if "|" in line or "\t" in line or ":" in line or "：" in line:
            yield re.sub(r"[ ]+", " ", line)


def _split_cells(row: str) -> list[str]:
    if "|" in row:
        return [cell.strip() for cell in row.split("|")]
    if "\t" in row:
        return [cell.strip() for cell in row.split("\t")]
    if "：" in row:
        return [cell.strip() for cell in row.split("：", 1)]
    if ":" in row:
        return [cell.strip() for cell in row.split(":", 1)]
    return [row.strip()]


def _match_metric(row: str) -> FinancialMetricSpec | None:
    lowered = row.lower()
    for metric in FINANCIAL_METRICS:
        if any(alias.lower() in lowered for alias in metric.aliases):
            return metric
    return None


def _extract_values_from_row(
    row: str,
    metric: FinancialMetricSpec,
    header_periods: list[str | None] | None = None,
) -> list[tuple[str | None, str, str | None]]:
    cells = _split_cells(row)
    if len(cells) < 2:
        return []

    periods = [_normalize_period(cell) for cell in cells]
    values: list[tuple[str | None, str, str | None]] = []
    fallback_period = _normalize_period(row)
    for index, cell in enumerate(cells):
        if any(alias.lower() in cell.lower() for alias in metric.aliases):
            continue
        number = _first_metric_number(cell, metric)
        if number is None:
            continue
        period = _period_at(header_periods or [], index) or _nearest_period(periods, index) or fallback_period
        unit = _infer_unit(cell, row, metric.default_unit)
        values.append((period, number, unit))
    return values


def _period_at(periods: list[str | None], index: int) -> str | None:
    if index < len(periods):
        return periods[index]
    return None


def _nearest_period(periods: list[str | None], index: int) -> str | None:
    if index < len(periods) and periods[index]:
        return periods[index]
    for offset in range(1, max(len(periods), 1)):
        left = index - offset
        right = index + offset
        if left >= 0 and periods[left]:
            return periods[left]
        if right < len(periods) and periods[right]:
            return periods[right]
    return None


def _normalize_period(text: str) -> str | None:
    match = _PERIOD_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1)).replace("/", "-")


def _first_number(text: str) -> str | None:
    match = _NUMBER_RE.search(text.replace("，", ","))
    return match.group(0) if match else None


def _first_metric_number(text: str, metric: FinancialMetricSpec) -> str | None:
    candidates = list(_NUMBER_RE.finditer(text.replace("，", ",")))
    for match in candidates:
        raw = match.group(0)
        suffix = text[match.end():match.end() + 8]
        prefix = text[max(0, match.start() - 4):match.start()]
        if re.fullmatch(r"20\d{2}", raw.replace(",", "")) and ("年" in suffix or metric.default_unit != "元"):
            continue
        if (raw.endswith("%") or "%" in suffix[:2]) and metric.default_unit != "%":
            continue
        if any(word in prefix.lower() for word in ("同比", "增长", "下降", "yoy")):
            continue
        return raw
    return None


def _source_coordinate(doc: SourceDocument, row: str, row_index: int) -> dict[str, str | None]:
    normalized = re.sub(r"\s+", "", row)
    for block in doc.blocks:
        if normalized and normalized in re.sub(r"\s+", "", block.content):
            return {
                "page": str(block.page) if block.page is not None else None,
                "paragraph_id": str(block.paragraph) if block.paragraph is not None else None,
                "sheet": block.sheet,
                "row_id": str(block.row) if block.row is not None else str(row_index),
            }
    return {"page": None, "paragraph_id": None, "sheet": None, "row_id": str(row_index)}


def _infer_unit(cell: str, row: str, default_unit: str | None) -> str | None:
    target = f"{cell} {row}"
    if "%" in cell or default_unit == "%":
        return "%"
    for unit in ("USD/shares", "USD", "元/股", "亿元", "万元", "百万元", "千元", "元"):
        if unit in target:
            return unit
    return default_unit


def _coerce_number(raw_value: str) -> float | str:
    cleaned = raw_value.replace(",", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        return float(cleaned)
    except ValueError:
        return raw_value


def _statement(metric_name: str, period: str | None, raw_value: str, unit: str | None, title: str) -> str:
    period_text = period or "未标明期间"
    unit_text = unit or ""
    return f"《{title}》披露 {period_text} {metric_name} 为 {raw_value}{unit_text}。"


def _dedupe_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[tuple[str | None, str | None, str | float | None, str | None]] = set()
    deduped: list[EvidenceItem] = []
    for item in items:
        key = (item.source_refs[0].source_id if item.source_refs else None, item.metric_name, item.metric_value, item.period)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
