from __future__ import annotations

from collections.abc import Iterable

from .financial_parser import expected_financial_metric_names, extract_structured_financial_evidence
from .value_investing_doctrine import doctrine_findings
from .models import (
    AgentFinding,
    AgentOutput,
    AgentStatus,
    ComplianceGateOutput,
    Confidence,
    DowngradedClaim,
    EvidenceCategory,
    EvidenceItem,
    MemoSection,
    ResearchMemo,
    SourceDocument,
    SourceRef,
    SourceType,
    UserMode,
    VerificationStatus,
    WorkflowState,
)


DISCLAIMER_ZH = (
    "本报告仅用于研究训练与内部分析参考，不构成任何投资建议、交易指令或收益承诺。"
    "所有结论均依赖当前用户提供资料，资料不足部分已标注为待验证。"
)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _first_excerpt(content: str, limit: int = 180) -> str:
    cleaned = " ".join(content.split())
    return cleaned[:limit]


def run_firm_doctrine_case_retrieval(state: WorkflowState) -> AgentOutput:
    if state.company_profile.user_mode == UserMode.TO_C:
        summary = "To C 模式使用通用价值投资 Doctrine，不启用机构专属评级。"
        warnings = ["当前使用通用价值投资准则；To B 阶段可接入机构成功报告、失败案例、细分理念和内部评级。"]
        missing_materials = []
    else:
        summary = "To B 模式使用通用价值投资 Doctrine 作为底座，并预留机构理念与案例召回接口。"
        warnings = ["机构理念、历史优秀案例、失败案例和内部评级规则尚未导入；当前先使用通用价值投资底座。"]
        missing_materials = ["机构投资理念文档", "历史优秀 Memo", "失败案例库", "内部评级规则"]

    return AgentOutput(
        agent_name="Doctrine & Case Context Skill",
        status=AgentStatus.PARTIAL,
        summary=summary,
        findings=[
            AgentFinding(
                title=title,
                detail=detail,
                classification="ai_reasoning",
                confidence=Confidence.MEDIUM,
            )
            for title, detail in doctrine_findings()
        ],
        missing_materials=missing_materials,
        confidence=Confidence.MEDIUM if state.company_profile.user_mode == UserMode.TO_C else Confidence.LOW,
        warnings=warnings,
    )


def run_material_organizer(state: WorkflowState) -> AgentOutput:
    documents: list[SourceDocument] = []
    for raw in state.raw_materials:
        documents.append(
            SourceDocument(
                title=raw.title,
                source_type=raw.source_type,
                file_name=raw.file_name,
                url=raw.url,
                usage_rights_confirmed=raw.usage_rights_confirmed,
                period_covered=raw.period_covered,
                modality=raw.modality,
                blocks=raw.blocks,
                parse_warnings=raw.parse_warnings,
                reliability_note="用户提供资料，需以后续证据抽取和交叉验证为准。",
                content=raw.content,
            )
        )
    state.source_documents = documents

    present_types = {doc.source_type for doc in documents}
    missing: list[str] = []
    expected = {
        SourceType.FINANCIAL_TABLE: "财务数据表",
        SourceType.ANNUAL_REPORT_SUMMARY: "年报或定期报告摘要",
        SourceType.MANAGEMENT_NOTE: "管理层交流纪要",
        SourceType.SELL_SIDE_SUMMARY: "卖方观点摘要",
        SourceType.NEWS_SUMMARY: "新闻或行业资料",
    }
    for source_type, label in expected.items():
        if source_type not in present_types:
            missing.append(label)

    return AgentOutput(
        agent_name="Material Organization Skill",
        status=AgentStatus.PASS if documents else AgentStatus.FAIL,
        summary=f"已整理 {len(documents)} 份用户资料。" if documents else "未收到可分析资料。",
        findings=[
            AgentFinding(
                title="资料覆盖检查",
                detail=f"当前资料类型包括：{', '.join(sorted(t.value for t in present_types)) or '无'}。",
                classification="fact_based" if documents else "missing_data",
                confidence=Confidence.MEDIUM if documents else Confidence.LOW,
            )
        ],
        missing_materials=missing,
        confidence=Confidence.MEDIUM if documents else Confidence.LOW,
        warnings=[] if documents else ["V1 是资料包驱动流程，缺少资料时不得强行判断。"],
    )


def run_evidence_extractor(state: WorkflowState) -> AgentOutput:
    evidence: list[EvidenceItem] = extract_structured_financial_evidence(state.source_documents)
    for doc in state.source_documents:
        content = doc.content.strip()
        if not content:
            continue
        ref = SourceRef(source_id=doc.source_id, excerpt=_first_excerpt(content), url=doc.url)
        if doc.source_type == SourceType.FINANCIAL_TABLE or _contains_any(content, ["经营现金流", "自由现金流", "roe", "资产负债率", "分红", "股息"]):
            category = EvidenceCategory.FINANCIAL_FACT
        elif doc.source_type == SourceType.MANAGEMENT_NOTE:
            category = EvidenceCategory.MANAGEMENT_OPINION
        elif doc.source_type == SourceType.SELL_SIDE_SUMMARY:
            category = EvidenceCategory.SELL_SIDE_OPINION
        elif doc.source_type in {SourceType.NEWS_SUMMARY, SourceType.INDUSTRY_MATERIAL}:
            category = EvidenceCategory.NEWS_OR_MARKET_OPINION
        elif doc.source_type == SourceType.USER_NOTE:
            category = EvidenceCategory.USER_OPINION
        else:
            category = EvidenceCategory.FACT

        if category != EvidenceCategory.FINANCIAL_FACT or not any(item.source_refs and item.source_refs[0].source_id == doc.source_id for item in evidence):
            evidence.append(
                EvidenceItem(
                    category=category,
                    statement=f"来自《{doc.title}》的资料片段：{_first_excerpt(content, 120)}",
                    source_refs=[ref],
                    confidence=Confidence.MEDIUM,
                    verification_status=VerificationStatus.PARTIALLY_SUPPORTED,
                    notes="当前为骨架抽取结果；后续 LLM 可补充更细粒度事实和观点。",
                )
            )

        for block in doc.blocks:
            if block.modality.value not in {"image", "audio"} or block.review_status == "rejected":
                continue
            category = EvidenceCategory.MANAGEMENT_OPINION if block.modality.value == "audio" else EvidenceCategory.FACT
            evidence.append(EvidenceItem(category=category, statement=block.content, source_refs=[SourceRef(source_id=doc.source_id, excerpt=block.content, url=doc.url, block_id=block.block_id, region=block.region, start_seconds=block.start_seconds, end_seconds=block.end_seconds, extraction_method=block.extraction_method, requires_confirmation=block.review_status != "confirmed")], confidence=Confidence.MEDIUM if block.review_status == "confirmed" else Confidence.LOW, verification_status=VerificationStatus.VERIFIED if block.review_status == "confirmed" else VerificationStatus.TO_BE_VERIFIED, notes="多模态内容需用户确认。"))

    state.evidence_items = evidence
    missing = []
    if not any(item.category == EvidenceCategory.FINANCIAL_FACT for item in evidence):
        missing.append("可回溯财务字段")
    if not any(item.category == EvidenceCategory.MANAGEMENT_OPINION for item in evidence):
        missing.append("管理层观点")
    if not any(item.category == EvidenceCategory.SELL_SIDE_OPINION for item in evidence):
        missing.append("卖方观点")
    extracted_metric_names = {item.metric_name for item in evidence if item.category == EvidenceCategory.FINANCIAL_FACT}
    for metric_name in expected_financial_metric_names():
        if metric_name not in extracted_metric_names:
            missing.append(f"财务字段：{metric_name}")

    return AgentOutput(
        agent_name="Evidence Extraction Skill",
        status=AgentStatus.PASS if evidence else AgentStatus.FAIL,
        summary=f"抽取 {len(evidence)} 条初始证据项，其中结构化财务字段 {len(extracted_metric_names)} 类。",
        findings=[
            AgentFinding(
                title="事实/观点/推理分区",
                detail="已按资料类型初步区分事实、财务事实、管理层观点、卖方观点、新闻观点和用户观点。",
                classification="fact_based" if evidence else "missing_data",
                evidence_ids=[item.evidence_id for item in evidence],
                confidence=Confidence.LOW,
            )
        ],
        evidence_ids=[item.evidence_id for item in evidence],
        missing_materials=missing,
        confidence=Confidence.LOW,
        warnings=[] if extracted_metric_names else ["未从财务表中解析出结构化财务字段。"],
    )


def run_financial_quality_dividend(state: WorkflowState) -> AgentOutput:
    financial = state.evidence_by_category(EvidenceCategory.FINANCIAL_FACT)
    missing = []
    joined = " ".join(item.statement for item in financial)
    for keyword, label in [
        ("经营现金流", "经营现金流数据"),
        ("自由现金流", "自由现金流数据"),
        ("分红", "分红历史与分红率"),
        ("资产负债率", "资产负债表安全数据"),
        ("ROE", "ROE 及杠杆拆解"),
    ]:
        if keyword.lower() not in joined.lower():
            missing.append(label)

    return AgentOutput(
        agent_name="Financial Quality & Dividend Skill",
        status=AgentStatus.PARTIAL if financial else AgentStatus.FAIL,
        summary="已基于当前财务证据进行保守的财务质量检查。" if financial else "缺少财务证据，无法判断现金流质量和分红可持续性。",
        findings=[
            AgentFinding(
                title="现金流与分红不可跳过",
                detail="当前阶段仅确认需要检查经营现金流、自由现金流覆盖分红、资产负债表安全和 ROE 杠杆依赖；缺失字段必须进入待验证。",
                classification="ai_reasoning" if financial else "missing_data",
                evidence_ids=[item.evidence_id for item in financial],
                confidence=Confidence.LOW,
            )
        ],
        evidence_ids=[item.evidence_id for item in financial],
        missing_materials=missing,
        confidence=Confidence.LOW,
        warnings=["不得将高股息直接等同于安全；必须验证自由现金流覆盖能力。"],
    )


def run_business_model_moat(state: WorkflowState) -> AgentOutput:
    usable = [
        item
        for item in state.evidence_items
        if item.category
        in {
            EvidenceCategory.FACT,
            EvidenceCategory.NEWS_OR_MARKET_OPINION,
            EvidenceCategory.USER_OPINION,
            EvidenceCategory.MANAGEMENT_OPINION,
        }
    ]
    return AgentOutput(
        agent_name="Business Model & Moat Skill",
        status=AgentStatus.PARTIAL if usable else AgentStatus.FAIL,
        summary="已建立商业模式分析占位，后续需抽取收入来源、利润来源、周期性和竞争优势。",
        findings=[
            AgentFinding(
                title="商业模式稳定性待验证",
                detail="当前骨架不直接判断护城河强弱；必须由收入来源、利润来源、行业需求和竞争格局证据支持。",
                classification="ai_reasoning",
                evidence_ids=[item.evidence_id for item in usable],
                confidence=Confidence.LOW,
            )
        ],
        evidence_ids=[item.evidence_id for item in usable],
        missing_materials=["收入结构", "利润来源", "竞争格局", "资本开支需求"],
        confidence=Confidence.LOW,
        warnings=["不得用管理层叙事替代商业模式证据。"],
    )


def run_management_view_comparison(state: WorkflowState) -> AgentOutput:
    management = state.evidence_by_category(EvidenceCategory.MANAGEMENT_OPINION)
    sell_side = state.evidence_by_category(EvidenceCategory.SELL_SIDE_OPINION)
    financial = state.evidence_by_category(EvidenceCategory.FINANCIAL_FACT)
    sell_side_documents = [doc for doc in state.source_documents if doc.source_type == SourceType.SELL_SIDE_SUMMARY]
    evidence_ids = [item.evidence_id for item in [*management, *sell_side, *financial]]
    missing = []
    if not management:
        missing.append("管理层观点")
    if not sell_side:
        missing.append("卖方观点摘要")
    if not financial:
        missing.append("可用于对照叙事的财务证据")

    return AgentOutput(
        agent_name="Management & View Comparison Skill",
        status=AgentStatus.PARTIAL if evidence_ids else AgentStatus.FAIL,
        summary=(
            f"已检查管理层、卖方与财务现实对比所需资料；当前识别 {len(sell_side_documents)} 份卖方来源。"
        ),
        findings=[
            AgentFinding(
                title="卖方观点不得直接变成买方结论",
                detail="卖方共识和分歧只能作为输入，最终判断必须经过证据、反证和价值陷阱检查。",
                classification="ai_reasoning",
                evidence_ids=evidence_ids,
                confidence=Confidence.LOW,
            ),
            AgentFinding(
                title="多卖方观点横向比较要求",
                detail="如果上传多份卖方研报，必须比较共同点、分歧点、分歧来源、核心假设差异，并标出买方需独立验证的问题。",
                classification="ai_reasoning",
                evidence_ids=[item.evidence_id for item in sell_side],
                confidence=Confidence.LOW,
            )
        ],
        evidence_ids=evidence_ids,
        missing_materials=missing,
        confidence=Confidence.LOW,
        warnings=[] if management and sell_side and financial else ["观点比较资料不完整，结论应降级。"],
    )


def run_value_trap_contradiction(state: WorkflowState) -> AgentOutput:
    evidence_ids = [item.evidence_id for item in state.evidence_items]
    checks = [
        "高股息是否由自由现金流覆盖",
        "低估值是否来自主业衰退",
        "利润是否依赖非经常性损益",
        "ROE 是否依赖高杠杆",
        "行业需求是否长期下行",
        "应收账款和存货是否恶化",
        "管理层叙事是否与财务现实冲突",
    ]
    return AgentOutput(
        agent_name="Value Trap & Contradiction Skill",
        status=AgentStatus.PARTIAL if evidence_ids else AgentStatus.FAIL,
        summary="已生成强制价值陷阱检查清单；真实判断需依赖后续细粒度证据。",
        findings=[
            AgentFinding(
                title=check,
                detail="当前材料需进一步验证该反证变量，不能因资料不足而跳过。",
                classification="risk",
                evidence_ids=evidence_ids,
                confidence=Confidence.LOW,
            )
            for check in checks
        ],
        evidence_ids=evidence_ids,
        missing_materials=["完整财务字段", "分红覆盖数据", "行业长期需求证据"],
        confidence=Confidence.LOW,
        warnings=["价值陷阱检查为强制模块，不能被前序乐观结论覆盖。"],
    )


def run_compliance_gate(state: WorkflowState, gate_name: str, draft_memo: ResearchMemo | None = None) -> ComplianceGateOutput:
    unsupported: list[str] = []
    evidence_issues: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    downgraded: list[DowngradedClaim] = []

    if not state.evidence_items:
        evidence_issues.append("没有可回溯证据项，不能生成高置信 Memo。")
        suggestions.append("请补充至少一份公司资料、财务数据或研究笔记。")

    for item in state.evidence_items:
        if item.category in {EvidenceCategory.FACT, EvidenceCategory.FINANCIAL_FACT} and not item.source_refs:
            unsupported.append(item.statement)
        if item.verification_status in {VerificationStatus.UNSUPPORTED, VerificationStatus.TO_BE_VERIFIED} and item.category in {EvidenceCategory.FACT, EvidenceCategory.FINANCIAL_FACT}:
            evidence_issues.append(f"关键事实尚未验证：{item.statement}")

    if state.evidence_graph.conflicts:
        evidence_issues.extend(f"跨来源数据冲突：{item}" for item in state.evidence_graph.conflicts)

    review_outputs = state.skill_outputs or state.agent_outputs
    for key, output in review_outputs.items():
        for finding in output.findings:
            if finding.classification in {"fact_based", "unsupported_claim"} and not finding.evidence_ids:
                unsupported.append(f"{key}：{finding.title} - {finding.detail}")

    trap_output = state.output_for("value_trap_contradiction")
    if not trap_output or not trap_output.findings:
        evidence_issues.append("价值陷阱与反证检查未完成，不能进入 Memo。")
    if state.research_judgment.unresolved_critical_count:
        evidence_issues.append(f"仍有 {state.research_judgment.unresolved_critical_count} 个关键反证缺少证据，不能进入正式 Memo。")

    support_ids = {evidence_id for output in review_outputs.values() for finding in output.findings for evidence_id in finding.evidence_ids}
    if support_ids:
        categories = {item.category for item in state.evidence_items if item.evidence_id in support_ids}
        if categories and categories.issubset({EvidenceCategory.SELL_SIDE_OPINION, EvidenceCategory.MANAGEMENT_OPINION, EvidenceCategory.NEWS_OR_MARKET_OPINION}):
            evidence_issues.append("当前分析只引用观点类材料，缺少独立事实证据，存在复读风险。")

    if state.company_profile.user_mode == UserMode.TO_C and draft_memo and draft_memo.markdown:
        forbidden = ["买入", "卖出", "增持", "减持", "强烈推荐", "立即买"]
        for word in forbidden:
            if word in draft_memo.markdown:
                warnings.append(f"To C 输出包含禁止评级或交易表达：{word}")

    if draft_memo:
        valid_ids = {item.evidence_id for item in state.evidence_items}
        for section in draft_memo.sections:
            unknown_ids = [item for item in section.evidence_ids if item not in valid_ids]
            if unknown_ids:
                evidence_issues.append(f"Memo章节《{section.title}》引用不存在的证据：{', '.join(unknown_ids)}")

    if any(output.status == AgentStatus.FAIL for output in review_outputs.values()):
        downgraded.append(
            DowngradedClaim(
                original_claim="生成高置信研究观点",
                downgraded_expression="当前资料不足，暂不支持高置信研究观点标签。",
                reason="至少一个前序 Agent 未通过。",
            )
        )

    status = "fail" if unsupported or evidence_issues or warnings else "pass"
    return ComplianceGateOutput(
        gate_name=gate_name,
        status=status,
        unsupported_claims=unsupported,
        evidence_issues=evidence_issues,
        downgraded_claims=downgraded,
        compliance_warnings=warnings,
        rewrite_suggestions=suggestions,
    )


def run_research_memo_generator(state: WorkflowState) -> ResearchMemo:
    source_ids = [doc.source_id for doc in state.source_documents]
    outputs = state.skill_outputs or state.agent_outputs

    def body_for(key: str, fallback: str) -> str:
        output = outputs.get(key)
        if not output:
            return fallback
        missing = f"\n\n待补充资料：{'; '.join(output.missing_materials)}" if output.missing_materials else ""
        warnings = f"\n\n注意事项：{'; '.join(output.warnings)}" if output.warnings else ""
        return f"{output.summary}{missing}{warnings}"

    sections = [
        MemoSection(
            section_id="material_scope_confidence",
            title="资料范围与结论置信度",
            body=f"当前基于用户提供的 {len(state.source_documents)} 份资料生成低置信研究训练 Memo。资料不足部分必须继续验证。",
            confidence=Confidence.LOW,
        ),
        MemoSection(
            section_id="company_info",
            title="公司基本信息",
            body=f"公司：{state.company_profile.company_name}；代码：{state.company_profile.ticker or '未提供'}；行业：{state.company_profile.industry}。",
            confidence=Confidence.MEDIUM,
        ),
        MemoSection(
            section_id="doctrine",
            title="研究准则适用说明",
            body=body_for("firm_doctrine_case_retrieval", "使用默认价值投资准则。"),
            confidence=Confidence.LOW,
        ),
        MemoSection(section_id="circle_of_competence", title="能力圈判断", body="当前资料尚不足以形成高置信能力圈判断，应继续补充业务模式、收入结构和行业资料。", confidence=Confidence.LOW),
        MemoSection(section_id="business_model", title="公司靠什么赚钱", body=body_for("business_model_moat", "缺少商业模式证据。"), confidence=Confidence.LOW),
        MemoSection(section_id="cash_flow_quality", title="现金流质量", body=body_for("financial_quality_dividend", "缺少财务质量证据。"), confidence=Confidence.LOW),
        MemoSection(section_id="dividend_quality", title="分红质量与可持续性", body="不得将高股息直接等同于安全；需要验证自由现金流覆盖分红、分红连续性和资产负债表压力。", confidence=Confidence.LOW),
        MemoSection(section_id="balance_sheet", title="资产负债表安全性", body="需要补充资产负债率、有息负债、短债压力、现金储备和 ROE 杠杆拆解。", confidence=Confidence.LOW),
        MemoSection(section_id="moat", title="商业模式稳定性与竞争优势", body=body_for("business_model_moat", "缺少护城河证据。"), confidence=Confidence.LOW),
        MemoSection(section_id="management_capital_allocation", title="管理层资本配置", body=body_for("management_view_comparison", "缺少管理层资本配置证据。"), confidence=Confidence.LOW),
        MemoSection(section_id="narrative_vs_financials", title="管理层叙事 vs 财务现实", body=body_for("management_view_comparison", "缺少管理层叙事和财务现实对照。"), confidence=Confidence.LOW),
        MemoSection(section_id="sell_side_views", title="卖方共识与核心分歧", body="卖方观点只能作为输入材料，不能直接作为买方结论。", confidence=Confidence.LOW),
        MemoSection(section_id="valuation_margin", title="估值与安全边际", body="当前骨架不做估值结论；低估值不能直接等同于安全边际。", confidence=Confidence.LOW),
        MemoSection(section_id="value_trap", title="价值陷阱与反证风险", body=body_for("value_trap_contradiction", "价值陷阱检查不可跳过。"), confidence=Confidence.LOW),
        MemoSection(section_id="verification_questions", title="待验证问题", body="请补充完整财务表、分红历史、管理层交流纪要、卖方观点摘要和行业需求资料。", confidence=Confidence.LOW),
        MemoSection(section_id="research_view", title="研究观点或内部研究标签", body="资料不足暂不评级。该标签仅用于研究训练，不构成投资建议。", confidence=Confidence.LOW),
        MemoSection(section_id="uncertainty", title="不确定性与资料缺口", body="当前输出为工作流骨架结果，所有具体投资判断都需要在细粒度证据抽取后重新生成。", confidence=Confidence.LOW),
        MemoSection(section_id="sources", title="来源列表", body="\n".join(f"- {doc.source_id}: {doc.title}" for doc in state.source_documents) or "无来源资料。", confidence=Confidence.MEDIUM if source_ids else Confidence.LOW),
        MemoSection(section_id="disclaimer", title="不构成投资建议声明", body=DISCLAIMER_ZH, confidence=Confidence.HIGH),
    ]
    memo = ResearchMemo(
        company_profile=state.company_profile,
        user_mode=state.company_profile.user_mode,
        confidence=Confidence.LOW,
        sections=sections,
        source_ids=source_ids,
        disclaimer=DISCLAIMER_ZH,
    )
    memo.markdown = "\n\n".join(f"## {section.title}\n\n{section.body}" for section in sections)
    return memo


def run_gate_blocked_memo(state: WorkflowState) -> ResearchMemo:
    gate = state.pre_memo_gate
    blockers = [] if gate is None else [*gate.unsupported_claims, *gate.evidence_issues, *gate.compliance_warnings]
    body = "当前研究未通过证据与合规门禁，不能生成正式研究 Memo。"
    if blockers:
        body += "\n\n必须先解决：\n" + "\n".join(f"- {item}" for item in blockers)
    sections = [
        MemoSection(section_id="gate_status", title="证据门禁状态", body=body, confidence=Confidence.LOW),
        MemoSection(section_id="material_scope", title="当前资料范围", body=f"已收到 {len(state.source_documents)} 份资料、抽取 {len(state.evidence_items)} 条证据；资料不足或冲突部分仍待验证。", evidence_ids=[item.evidence_id for item in state.evidence_items], confidence=Confidence.LOW),
    ]
    markdown = "# 待补证据研究草稿\n\n" + "\n\n".join(f"## {section.title}\n\n{section.body}" for section in sections) + f"\n\n## 免责声明\n\n{DISCLAIMER_ZH}"
    return ResearchMemo(company_profile=state.company_profile, user_mode=state.company_profile.user_mode, confidence=Confidence.LOW, sections=sections, source_ids=[doc.source_id for doc in state.source_documents], disclaimer=DISCLAIMER_ZH, markdown=markdown)


def run_research_coach_review(memo_text: str, state: WorkflowState) -> AgentOutput:
    findings: list[AgentFinding] = []
    checks = [
        ("证据来源", ["来源", "source", "出处"]),
        ("反证风险", ["反证", "风险", "价值陷阱"]),
        ("现金流质量", ["经营现金流", "自由现金流", "现金流"]),
        ("分红可持续性", ["分红", "股息"]),
        ("不构成投资建议", ["不构成投资建议", "投资建议"]),
    ]
    for title, keywords in checks:
        if not _contains_any(memo_text, keywords):
            findings.append(
                AgentFinding(
                    title=f"缺少{title}",
                    detail=f"用户 Memo 未明显覆盖「{title}」，应按 PRD 补充。",
                    classification="missing_data",
                    confidence=Confidence.MEDIUM,
                )
            )

    forbidden = ["必涨", "一定上涨", "稳赚", "立即买入", "立即卖出"]
    for word in forbidden:
        if word in memo_text:
            findings.append(
                AgentFinding(
                    title="合规表达风险",
                    detail=f"检测到高风险表达：{word}。",
                    classification="compliance",
                    confidence=Confidence.HIGH,
                )
            )

    return AgentOutput(
        agent_name="Research Coach Review Mode",
        status=AgentStatus.PASS if not findings else AgentStatus.PARTIAL,
        summary="已按证据意识、价值陷阱、现金流/分红检查和合规表达对用户 Memo 做初步批改。",
        findings=findings,
        missing_materials=[],
        confidence=Confidence.LOW,
        warnings=["当前为规则型批改骨架，后续应接入机构 doctrine 和历史优秀案例。"],
    )
