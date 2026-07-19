from __future__ import annotations
from collections import defaultdict
from .models import EvidenceGraph, EvidenceGraphQuality, EvidenceItem, FinancialAnomaly, VerificationStatus

def detect_financial_anomalies(items: list[EvidenceItem]) -> list[FinancialAnomaly]:
    by_period=defaultdict(dict); ids=defaultdict(dict)
    for item in items:
        if item.period and item.metric_name and isinstance(item.metric_value,(int,float)):
            by_period[item.period][item.metric_name]=float(item.metric_value); ids[item.period][item.metric_name]=item.evidence_id
    out=[]
    def add(period, kind, severity, text, metrics, question):
        out.append(FinancialAnomaly(anomaly_type=kind,severity=severity,period=period,description=text,evidence_ids=[ids[period][m] for m in metrics if m in ids[period]],verification_question=question))
    for period,v in by_period.items():
        np=v.get("net_profit"); ocf=v.get("operating_cash_flow"); ar=v.get("accounts_receivable"); rev=v.get("revenue"); inv=v.get("inventory"); debt=v.get("interest_bearing_debt"); assets=v.get("total_assets"); nonrec=v.get("non_recurring_pnl"); equity=v.get("shareholders_equity"); gross=v.get("gross_profit"); selling=v.get("selling_expense")
        if np and np>0 and ocf is not None and ocf/np<.7: add(period,"cash_profit_divergence","high",f"经营现金流仅为净利润的 {ocf/np:.1%}",["operating_cash_flow","net_profit"],"利润为何没有转化为现金？")
        if rev and ar and ar/rev>.35: add(period,"receivable_pressure","medium",f"应收账款占收入 {ar/rev:.1%}",["accounts_receivable","revenue"],"回款周期和坏账准备是否恶化？")
        if rev and inv and inv/rev>.4: add(period,"inventory_pressure","medium",f"存货占收入 {inv/rev:.1%}",["inventory","revenue"],"库存增长来自备货还是滞销？")
        if assets and debt and debt/assets>.5: add(period,"leverage_pressure","high",f"有息负债占资产 {debt/assets:.1%}",["interest_bearing_debt","total_assets"],"债务到期和利息覆盖是否可承受？")
        if np and nonrec and abs(nonrec/np)>.3: add(period,"non_recurring_profit","high",f"非经常性损益占净利润 {nonrec/np:.1%}",["non_recurring_pnl","net_profit"],"剔除一次性损益后主业盈利能力如何？")
        if np and equity and assets and equity>0 and assets/equity>3: add(period,"leverage_driven_roe","medium",f"权益乘数达到 {assets/equity:.1f} 倍，ROE可能主要由杠杆驱动",["net_profit","shareholders_equity","total_assets"],"ROE来自利润率、周转率还是杠杆？")
        if rev and gross is not None and gross/rev<.15: add(period,"low_gross_margin","medium",f"毛利率仅 {gross/rev:.1%}",["gross_profit","revenue"],"低毛利是否反映竞争恶化或成本转嫁能力不足？")
        if rev and selling is not None and selling/rev>.25: add(period,"selling_expense_pressure","medium",f"销售费用率达到 {selling/rev:.1%}",["selling_expense","revenue"],"增长是否依赖不可持续的获客投入？")
    ordered=sorted(by_period)
    for previous,current in zip(ordered,ordered[1:]):
        before,after=by_period[previous],by_period[current]
        for metric,label in (("revenue","收入"),("net_profit","净利润"),("operating_cash_flow","经营现金流"),("accounts_receivable","应收账款"),("inventory","存货")):
            if before.get(metric) and metric in after:
                growth=(after[metric]-before[metric])/abs(before[metric])
                if abs(growth)>=.3: add(current,"trend_break","high" if abs(growth)>=.5 else "medium",f"{label}较{previous}变动 {growth:.1%}",[metric],f"{label}大幅变化是周期、口径还是经营拐点？")
        if before.get("revenue") and after.get("revenue") and before.get("accounts_receivable") is not None and after.get("accounts_receivable") is not None:
            rev_growth=(after["revenue"]-before["revenue"])/abs(before["revenue"]); ar_growth=(after["accounts_receivable"]-before["accounts_receivable"])/max(abs(before["accounts_receivable"]),1)
            if ar_growth-rev_growth>.2: add(current,"receivable_revenue_divergence","high",f"应收增速 {ar_growth:.1%} 显著高于收入增速 {rev_growth:.1%}",["accounts_receivable","revenue"],"是否通过放宽信用政策推动收入？")
    return out

def assess_graph_quality(graph: EvidenceGraph) -> EvidenceGraphQuality:
    evidence=[n for n in graph.nodes if n.evidence_id]
    trace=sum(bool(n.source_id or n.metadata.get("source_refs")) for n in evidence)/max(len(evidence),1)*100
    verified=sum(n.verification_status==VerificationStatus.VERIFIED for n in evidence)/max(len(evidence),1)*100
    related={e.from_node_id for e in graph.edges}|{e.to_node_id for e in graph.edges}
    coverage=sum(n.node_id in related for n in evidence)/max(len(evidence),1)*100
    issues=[]
    if trace<100: issues.append("部分证据缺少可追溯来源")
    if verified<70: issues.append("已确认事实比例不足70%")
    if coverage<70: issues.append("部分证据尚未建立支持、反证或依赖关系")
    if graph.conflicts: issues.append(f"仍有{len(graph.conflicts)}项未解决冲突")
    return EvidenceGraphQuality(score=round(trace*.35+verified*.35+coverage*.3,1),traceability_rate=round(trace,1),verified_rate=round(verified,1),relation_coverage=round(coverage,1),unresolved_conflicts=len(graph.conflicts),issues=issues)
