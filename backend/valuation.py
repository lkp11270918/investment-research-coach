from __future__ import annotations

import math
from collections import defaultdict

from .models import EvidenceItem, ValuationAnalysis, ValuationAssumptions, ValuationScenarioResult, ValuationSensitivityPoint, VerificationStatus

SCALE = {"元":1,"千元":1_000,"万元":10_000,"百万元":1_000_000,"亿元":100_000_000,"股":1,"万股":10_000,"百万股":1_000_000,"亿股":100_000_000,"元/股":1,"倍":1,"%":1}
FINANCIAL_INDUSTRIES = ("银行", "保险", "证券", "金融", "信托")


def analyze_valuation(items: list[EvidenceItem], industry: str = "", assumptions: ValuationAssumptions | None = None) -> ValuationAnalysis:
    assumptions = assumptions or ValuationAssumptions()
    series, evidence_ids, unverified_metrics, conflicts = _series(items)
    latest = {metric: values[-1][1] for metric, values in series.items() if values}
    price, shares = latest.get("share_price"), latest.get("shares_outstanding")
    eps, bvps = latest.get("eps"), latest.get("book_value_per_share")
    debt = latest.get("interest_bearing_debt", 0.0)
    cash = latest.get("cash_and_equivalents", 0.0)
    minority = latest.get("minority_interest", 0.0)
    non_operating = latest.get("non_operating_assets", 0.0)
    net_debt = debt - cash
    multiples: dict[str, float] = {}
    if price and eps and eps > 0: multiples["pe"] = round(price / eps, 2)
    if price and bvps and bvps > 0: multiples["pb"] = round(price / bvps, 2)
    if latest.get("market_cap") and latest.get("ebitda", 0) > 0:
        multiples["ev_ebitda"] = round((latest["market_cap"] + net_debt + minority - non_operating) / latest["ebitda"], 2)

    historical = _ranges(series, ("historical_pe", "historical_pb"))
    peers = _ranges(series, ("peer_pe", "peer_pb", "peer_ev_ebitda"))
    method, reason = _select_method(industry, assumptions, latest)
    scenarios: list[ValuationScenarioResult] = []
    sensitivity: list[ValuationSensitivityPoint] = []
    missing: list[str] = []
    warnings: list[str] = []
    bridge = {"interest_bearing_debt":debt,"cash_and_equivalents":cash,"net_debt":net_debt,"minority_interest":minority,"non_operating_assets":non_operating}
    required_metrics = _required_metrics(method, latest)
    for metric in sorted(required_metrics & unverified_metrics):
        warnings.append(f"{_metric_label(metric)}尚未核验，只能用于训练草案")
    for metric in sorted(required_metrics & conflicts):
        warnings.append(f"{_metric_label(metric)}同一期间存在冲突值，确认前不能形成正式结论")

    if price is None: missing.append("当前股价")
    if method == "fcff":
        flow = latest.get("free_cash_flow_to_firm")
        if flow is None: missing.append("明确口径的企业自由现金流FCFF")
        if not shares: missing.append("总股本")
        if "interest_bearing_debt" not in latest: missing.append("有息负债")
        if "cash_and_equivalents" not in latest: missing.append("现金及现金等价物")
        if flow is not None and shares:
            scenarios = _cashflow_scenarios("fcff", flow, shares, price, assumptions, bridge)
            sensitivity = _sensitivity("fcff", flow, shares, assumptions, bridge)
    elif method == "fcfe":
        flow = latest.get("free_cash_flow_to_equity")
        if flow is None: missing.append("明确口径的股权自由现金流FCFE")
        if not shares: missing.append("总股本")
        if flow is not None and shares:
            scenarios = _cashflow_scenarios("fcfe", flow, shares, price, assumptions, bridge)
            sensitivity = _sensitivity("fcfe", flow, shares, assumptions, bridge)
    elif method == "ddm":
        dividend = latest.get("dividend_per_share")
        if dividend is None: missing.append("每股股利")
        if dividend is not None:
            scenarios = _ddm_scenarios(dividend, price, assumptions)
            sensitivity = _ddm_sensitivity(dividend, assumptions)
    elif method == "relative":
        if not multiples: missing.append("每股收益、每股净资产或EBITDA")
        if not peers and not historical: missing.append("历史估值或可比公司估值")
        scenarios = _relative_scenarios(price, eps, bvps, peers, historical, assumptions.margin_of_safety_required)

    if latest.get("free_cash_flow") is not None and not latest.get("free_cash_flow_to_firm") and not latest.get("free_cash_flow_to_equity"):
        warnings.append("普通自由现金流未标明FCFF或FCFE口径，未用于内在价值计算")
    if assumptions.terminal_growth >= min(assumptions.wacc, assumptions.cost_of_equity):
        warnings.append("永续增长率必须低于折现率")
        scenarios = []; sensitivity = []
    for scenario in scenarios:
        if scenario.margin_of_safety_percent is not None:
            scenario.meets_required_margin = scenario.margin_of_safety_percent >= assumptions.margin_of_safety_required * 100
    reverse = _reverse_assumptions(method, price, latest, shares, assumptions, bridge)
    complete = bool(scenarios) and not missing and not warnings
    formal = complete and assumptions.confirmed
    status = "formal" if formal else "draft" if scenarios else "insufficient_data"
    if formal:
        base = next((item for item in scenarios if item.name == "base"), scenarios[0])
        conclusion = f"用户已确认估值假设；基准情景每股价值 {base.estimated_value_per_share}，安全边际 {base.margin_of_safety_percent}%"
    elif scenarios:
        conclusion = "估值结果仅为训练草案；用户确认现金流口径、折现率、增长率及股权价值桥接后才能形成正式安全边际判断"
    else:
        conclusion = "资料或口径不足，不能形成安全边际判断"
    return ValuationAnalysis(status=status, method=method, method_reason=reason, assumptions_confirmed=assumptions.confirmed, formal_conclusion_allowed=formal, market_price=price, required_margin_percent=round(assumptions.margin_of_safety_required*100,1), multiples=multiples, historical_ranges=historical, peer_ranges=peers, equity_bridge=bridge, reverse_assumptions=reverse, scenarios=scenarios, sensitivity=sensitivity, missing_inputs=list(dict.fromkeys(missing)), warnings=warnings, evidence_ids=list(evidence_ids), conclusion=conclusion)


def _series(items):
    series=defaultdict(list); ids=set(); unverified=set(); values_by_period=defaultdict(set)
    for item in items:
        if item.metric_name and isinstance(item.metric_value,(int,float)):
            value=float(item.metric_value)*SCALE.get(item.unit or "",1)
            series[item.metric_name].append((item.period or "",value)); ids.add(item.evidence_id)
            values_by_period[(item.metric_name,item.period or "")].add(value)
            if item.verification_status != VerificationStatus.VERIFIED: unverified.add(item.metric_name)
    for values in series.values(): values.sort(key=lambda item:item[0])
    conflicts={metric for (metric,_),values in values_by_period.items() if len(values)>1}
    return series,ids,unverified,conflicts


def _required_metrics(method, latest):
    common={"share_price"}
    if method=="fcff": return common|{"free_cash_flow_to_firm","shares_outstanding","interest_bearing_debt","cash_and_equivalents"}
    if method=="fcfe": return common|{"free_cash_flow_to_equity","shares_outstanding"}
    if method=="ddm": return common|{"dividend_per_share"}
    metrics=common.copy()
    if latest.get("eps") is not None: metrics.add("eps")
    if latest.get("book_value_per_share") is not None: metrics.add("book_value_per_share")
    metrics.update(name for name in ("peer_pe","peer_pb","historical_pe","historical_pb") if latest.get(name) is not None)
    return metrics


def _metric_label(metric):
    return {"share_price":"当前股价","shares_outstanding":"总股本","free_cash_flow_to_firm":"企业自由现金流FCFF","free_cash_flow_to_equity":"股权自由现金流FCFE","interest_bearing_debt":"有息负债","cash_and_equivalents":"现金及现金等价物","dividend_per_share":"每股股利","eps":"每股收益","book_value_per_share":"每股净资产","peer_pe":"可比公司PE","peer_pb":"可比公司PB","historical_pe":"历史PE","historical_pb":"历史PB"}.get(metric,metric)


def _select_method(industry, assumptions, latest):
    if assumptions.method != "auto": return assumptions.method, "用户指定估值方法"
    if any(token in industry for token in FINANCIAL_INDUSTRIES):
        return ("ddm","金融行业优先使用股利折现，避免将存贷款负债机械视为工业企业净负债") if latest.get("dividend_per_share") is not None else ("relative","金融行业缺少稳定股利，使用PB/PE相对估值")
    if latest.get("free_cash_flow_to_firm") is not None: return "fcff","存在明确FCFF口径，使用企业自由现金流估值并桥接至股权价值"
    if latest.get("free_cash_flow_to_equity") is not None: return "fcfe","存在明确FCFE口径，直接估计股权价值"
    return "relative","缺少明确FCFF/FCFE口径，禁止用普通FCF冒充，退回相对估值"


def _cashflow_scenarios(method, flow, shares, price, a, bridge):
    rates=(("bear",a.bear_growth,a.wacc+.02 if method=="fcff" else a.cost_of_equity+.02,0.0),("base",a.base_growth,a.wacc if method=="fcff" else a.cost_of_equity,a.terminal_growth),("bull",a.bull_growth,max(.01,(a.wacc if method=="fcff" else a.cost_of_equity)-.01),min(a.terminal_growth+.01,.05)))
    return [_discounted(name,method,flow,shares,price,growth,discount,terminal,a.forecast_years,bridge) for name,growth,discount,terminal in rates if discount>terminal]


def _discounted(name,method,flow,shares,price,growth,discount,terminal,years,bridge):
    current=flow; pv=0.0
    for year in range(1,years+1): current*=1+growth; pv+=current/(1+discount)**year
    terminal_value=current*(1+terminal)/(discount-terminal)/(1+discount)**years
    enterprise=pv+terminal_value
    equity=enterprise if method=="fcfe" else enterprise-bridge["net_debt"]-bridge["minority_interest"]+bridge["non_operating_assets"]
    per_share=round(equity/shares,2); margin=round((per_share-price)/price*100,1) if price else None
    return ValuationScenarioResult(name=name,method=method,assumptions={"cash_flow_growth":growth,"discount_rate":discount,"terminal_growth":terminal,"forecast_years":years},enterprise_value=round(enterprise,2) if method=="fcff" else None,equity_value=round(equity,2),estimated_value_per_share=per_share,margin_of_safety_percent=margin)


def _sensitivity(method,flow,shares,a,bridge):
    base_discount=a.wacc if method=="fcff" else a.cost_of_equity; out=[]
    for growth in (a.base_growth-.02,a.base_growth,a.base_growth+.02):
        for discount in (base_discount-.01,base_discount,base_discount+.01):
            if discount<=a.terminal_growth: continue
            result=_discounted("sensitivity",method,flow,shares,None,growth,discount,a.terminal_growth,a.forecast_years,bridge)
            out.append(ValuationSensitivityPoint(growth_rate=growth,discount_rate=discount,value_per_share=result.estimated_value_per_share))
    return out


def _ddm_scenarios(dividend,price,a):
    out=[]
    for name,growth,discount in (("bear",max(-.1,a.bear_growth),a.cost_of_equity+.02),("base",a.base_growth,a.cost_of_equity),("bull",a.bull_growth,max(.01,a.cost_of_equity-.01))):
        if discount<=growth: continue
        value=round(dividend*(1+growth)/(discount-growth),2)
        out.append(ValuationScenarioResult(name=name,method="ddm",assumptions={"dividend_growth":growth,"cost_of_equity":discount},equity_value=None,estimated_value_per_share=value,margin_of_safety_percent=round((value-price)/price*100,1) if price else None))
    return out


def _ddm_sensitivity(dividend,a):
    return [ValuationSensitivityPoint(growth_rate=g,discount_rate=d,value_per_share=round(dividend*(1+g)/(d-g),2)) for g in (a.base_growth-.02,a.base_growth,a.base_growth+.02) for d in (a.cost_of_equity-.01,a.cost_of_equity,a.cost_of_equity+.01) if d>g]


def _relative_scenarios(price,eps,bvps,peers,historical,required_margin=0.25):
    values=[]
    pe_range=peers.get("peer_pe") or historical.get("historical_pe")
    pb_range=peers.get("peer_pb") or historical.get("historical_pb")
    for name,key in (("bear","min"),("base","median"),("bull","max")):
        candidates=[]
        if eps and pe_range: candidates.append(eps*pe_range[key])
        if bvps and pb_range: candidates.append(bvps*pb_range[key])
        if candidates:
            value=round(sum(candidates)/len(candidates),2); values.append(ValuationScenarioResult(name=name,method="relative",assumptions={},estimated_value_per_share=value,margin_of_safety_percent=round((value-price)/price*100,1) if price else None))
    return values


def _ranges(series,names):
    result={}
    for name in names:
        values=sorted(value for _,value in series.get(name,[]))
        if values: result[name]={"min":round(values[0],2),"median":round(values[len(values)//2],2),"max":round(values[-1],2)}
    return result


def _reverse_assumptions(method,price,latest,shares,a,bridge):
    if not price or not shares or method not in {"fcff","fcfe"}: return []
    flow=latest.get("free_cash_flow_to_firm" if method=="fcff" else "free_cash_flow_to_equity")
    if not flow: return []
    low,high=-.3,.3
    for _ in range(50):
        mid=(low+high)/2
        value=_discounted("reverse",method,flow,shares,None,mid,a.wacc if method=="fcff" else a.cost_of_equity,a.terminal_growth,a.forecast_years,bridge).estimated_value_per_share or 0
        if value<price: low=mid
        else: high=mid
    return [f"在当前折现率与终值假设下，当前价格隐含未来{a.forecast_years}年现金流年增长约 {(low+high)/2:.1%}"]
