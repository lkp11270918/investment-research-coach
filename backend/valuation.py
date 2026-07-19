from __future__ import annotations
from .models import EvidenceItem, ValuationAnalysis, ValuationScenarioResult

SCALE={"元":1,"千元":1_000,"万元":10_000,"百万元":1_000_000,"亿元":100_000_000,"股":1,"万股":10_000,"百万股":1_000_000,"亿股":100_000_000,"元/股":1}

def analyze_valuation(items: list[EvidenceItem]) -> ValuationAnalysis:
    values: dict[str, tuple[float, str]] = {}
    ids: dict[str, str] = {}
    for item in items:
        if item.metric_name and isinstance(item.metric_value, (int, float)):
            values[item.metric_name] = (float(item.metric_value)*SCALE.get(item.unit or "",1), item.unit or "")
            ids[item.metric_name] = item.evidence_id
    price = _value(values, "share_price")
    eps = _value(values, "eps", "earnings_per_share")
    bvps = _value(values, "book_value_per_share")
    fcf = _value(values, "free_cash_flow_calculated", "free_cash_flow")
    shares = _value(values, "shares_outstanding")
    multiples = {}
    if price and eps and eps > 0: multiples["pe"] = round(price / eps, 2)
    if price and bvps and bvps > 0: multiples["pb"] = round(price / bvps, 2)
    missing = [name for name, value in (("当前股价", price), ("每股收益", eps), ("自由现金流", fcf), ("总股本", shares)) if value is None]
    scenarios = []
    if price and fcf is not None and shares and shares > 0:
        base_fcf = fcf / shares
        for name, growth, discount, terminal in (("bear", -0.05, .13, .0), ("base", .03, .10, .02), ("bull", .08, .09, .03)):
            cashflows=[]; current=base_fcf
            for year in range(1, 6):
                current *= 1 + growth; cashflows.append(current / ((1 + discount) ** year))
            terminal_value = current * (1 + terminal) / max(discount-terminal, .01) / ((1+discount)**5)
            value = round(sum(cashflows)+terminal_value, 2)
            scenarios.append(ValuationScenarioResult(name=name, assumptions={"fcf_growth":growth,"discount_rate":discount,"terminal_growth":terminal}, estimated_value_per_share=value, margin_of_safety_percent=round((value-price)/price*100,1)))
    reverse=[]
    if price and "base_fcf" in locals() and base_fcf:
        reverse.append(f"当前价格约为每股自由现金流的 {price/base_fcf:.1f} 倍，市场隐含持续增长或较低风险要求")
    status = "completed" if scenarios else "partial" if multiples else "insufficient_data"
    conclusion = "已形成三情景估值，安全边际必须结合反证与数据质量判断" if scenarios else "仅能观察估值倍数，资料不足以判断真实安全边际" if multiples else "资料不足，不能形成安全边际判断"
    return ValuationAnalysis(status=status, market_price=price, multiples=multiples, reverse_assumptions=reverse, scenarios=scenarios, missing_inputs=missing, evidence_ids=list({ids[k] for k in ids if k in {"share_price","eps","earnings_per_share","book_value_per_share","free_cash_flow_calculated","free_cash_flow","shares_outstanding"}}), conclusion=conclusion)

def _value(values, *names):
    for name in names:
        if name in values: return values[name][0]
    return None
