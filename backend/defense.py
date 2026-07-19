from __future__ import annotations

from datetime import datetime, timezone

from .llm_client import LLMError, OpenAIClient
from .models import DefenseRole, DefenseSession, DefenseTurn, EvidenceGraph, ThesisVersion
from .model_pipeline import embed_text


ROLE_ORDER = [DefenseRole.PORTFOLIO_MANAGER, DefenseRole.INVESTMENT_DIRECTOR, DefenseRole.INDUSTRY_RESEARCHER, DefenseRole.RISK_MANAGER]


def start_defense(project_id: str, thesis: ThesisVersion, graph: EvidenceGraph, client: OpenAIClient | None = None, prior_errors: list[str] | None = None) -> DefenseSession:
    client = client or OpenAIClient()
    prior_errors = prior_errors or []
    generated = _generate_questions(thesis, graph, client, prior_errors)
    turns = generated or [_question_for_role(role, thesis, graph) for role in ROLE_ORDER]
    first, queued = turns[0], turns[1:]
    return DefenseSession(project_id=project_id, thesis_id=thesis.thesis_id, turns=[first], question_model=client.settings.openai_model if generated and client.available else "deterministic_company_evidence", targeted_gaps=prior_errors[:5], question_bank=queued)


def answer_defense(session: DefenseSession, thesis: ThesisVersion, graph: EvidenceGraph, answer: str, evidence_ids: list[str], client: OpenAIClient | None = None) -> DefenseSession:
    if session.status != "active" or not session.turns or session.turns[-1].answer is not None:
        raise ValueError("答辩会话当前不能提交回答")
    valid_ids = {node.evidence_id for node in graph.nodes if node.evidence_id}
    cited = [item for item in evidence_ids if item in valid_ids]
    turn = session.turns[-1]
    score, feedback, passed, breakdown = _evaluate_answer(turn, answer, cited, graph, client or OpenAIClient())
    turn.answer = answer
    turn.answer_evidence_ids = cited
    turn.score = score
    turn.feedback = feedback
    turn.passed = passed
    turn.score_breakdown = breakdown
    if not passed and sum(1 for item in session.turns if item.role == turn.role) < 2:
        session.turns.append(DefenseTurn(role=turn.role, question=f"你的回答仍缺少可验证支撑。请直接说明证据、关键假设，以及什么情况会推翻你的判断：{turn.question}", thesis_reference=thesis.draft.core_view))
    else:
        role_index = ROLE_ORDER.index(turn.role)
        if role_index + 1 < len(ROLE_ORDER):
            next_role = ROLE_ORDER[role_index + 1]
            planned = next((item for item in session.question_bank if item.role == next_role), None)
            session.turns.append(planned or _question_for_role(next_role, thesis, graph))
        else:
            session.status = "completed"
            scores = [item.score for item in session.turns if item.score is not None]
            session.overall_score = round(sum(scores) / max(len(scores), 1), 1)
            session.improvement_tasks = _improvement_tasks(session)
    session.updated_at = datetime.now(timezone.utc)
    return session


def _question_for_role(role: DefenseRole, thesis: ThesisVersion, graph: EvidenceGraph) -> DefenseTurn:
    draft = thesis.draft
    questions = {
        DefenseRole.PORTFOLIO_MANAGER: f"你的核心观点是“{draft.core_view}”。其中最关键的可验证假设是什么，为什么？",
        DefenseRole.INVESTMENT_DIRECTOR: "如果只能用三条事实向投委会解释风险收益来源，你会选择什么？估值与安全边际依赖哪些情景？",
        DefenseRole.INDUSTRY_RESEARCHER: "你的判断与行业竞争、需求和公司护城河之间有什么可回溯证据？",
        DefenseRole.FINANCIAL_RESEARCHER: "利润、经营现金流、自由现金流与资本开支之间是否一致？请用证据回答。",
        DefenseRole.RISK_MANAGER: f"请解释最可能推翻观点的条件，以及出现后你如何修正判断。当前条件：{'；'.join(draft.falsification_conditions) or '尚未定义'}",
    }
    risk_nodes = [node for node in graph.nodes if node.evidence_id and node.node_type in {"risk", "financial_fact", "red_team_challenge"}][:5]
    context = "；".join(node.label[:60] for node in risk_nodes[:2])
    question = questions[role] + (f" 请结合当前证据中的“{context}”回答。" if context else "")
    return DefenseTurn(role=role, question=question, thesis_reference=draft.core_view, evidence_ids=[node.evidence_id for node in risk_nodes if node.evidence_id])


def _evaluate_answer(turn: DefenseTurn, answer: str, evidence_ids: list[str], graph: EvidenceGraph, client: OpenAIClient) -> tuple[float, str, bool, dict[str, float]]:
    evidence_nodes = {node.evidence_id: node for node in graph.nodes if node.evidence_id}
    if client.available:
        try:
            evidence_context = [{"evidence_id": item, "label": evidence_nodes[item].label, "status": evidence_nodes[item].verification_status.value} for item in evidence_ids if item in evidence_nodes]
            result = client.generate_json(system_prompt="你是严格的买方投委会答辩官。按directness、evidence、assumptions、falsification、uncertainty五项评分，总分100。评价回答是否直接回答、引用的证据是否真的支持、是否说明假设与推翻条件。不得按长度或术语数量加分，不得给投资建议。返回JSON: {\"score\":0-100,\"score_breakdown\":{\"directness\":0,\"evidence\":0,\"assumptions\":0,\"falsification\":0,\"uncertainty\":0},\"feedback\":\"...\",\"passed\":true/false}", user_payload={"role": turn.role.value, "question": turn.question, "answer": answer, "evidence": evidence_context}, temperature=0)
            score = max(0, min(100, float(result.get("score", 0))))
            breakdown = {str(key): float(value) for key, value in result.get("score_breakdown", {}).items() if isinstance(value, (int, float))}
            required = {"directness", "evidence", "assumptions", "falsification", "uncertainty"}
            passed = bool(result.get("passed", False)) and score >= 60 and bool(evidence_context) and required.issubset(breakdown)
            return score, str(result.get("feedback", "")), passed, breakdown
        except (LLMError, TypeError, ValueError):
            pass
    evidence_quality = 0.0
    if evidence_ids:
        relevant = sum(_similarity(answer + turn.question, evidence_nodes[item].label) >= 0.08 for item in evidence_ids if item in evidence_nodes)
        evidence_quality = min(30.0, relevant / max(len(evidence_ids), 1) * 30)
    breakdown = {
        "directness": 25.0 if _similarity(turn.question, answer) >= 0.06 else 8.0,
        "evidence": evidence_quality,
        "assumptions": 20.0 if any(word in answer for word in ("假设", "前提", "依赖")) else 0.0,
        "falsification": 20.0 if any(word in answer for word in ("推翻", "如果", "一旦", "下降", "无法")) else 0.0,
        "uncertainty": 5.0 if any(word in answer for word in ("不确定", "待验证", "未知")) else 0.0,
    }
    score = sum(breakdown.values())
    issues = []
    if not evidence_ids: issues.append("缺少证据引用")
    if breakdown["directness"] < 20: issues.append("没有直接回应问题")
    if evidence_ids and evidence_quality == 0: issues.append("引用证据与回答缺少关联")
    if not any(word in answer for word in ("假设", "如果", "推翻", "不确定", "待验证")): issues.append("没有说明假设或推翻条件")
    passed = score >= 60 and not issues
    return score, "；".join(issues) if issues else "回答直接、包含相关证据并说明了判断边界。", passed, breakdown


def _similarity(left: str, right: str) -> float:
    a, b = embed_text(left), embed_text(right)
    return sum(x * y for x, y in zip(a, b))


def _improvement_tasks(session: DefenseSession) -> list[str]:
    tasks: list[str] = []
    for turn in session.turns:
        if not turn.passed:
            tasks.append(f"补强{turn.role.value}问题：{turn.feedback}")
    return list(dict.fromkeys(tasks)) or ["将答辩中使用的关键证据和推翻条件同步回 Thesis。"]


def _generate_questions(thesis: ThesisVersion, graph: EvidenceGraph, client: OpenAIClient, prior_errors: list[str]) -> list[DefenseTurn]:
    if not client.available:
        return []
    evidence = [{"id": node.evidence_id, "type": node.node_type, "label": node.label, "status": node.verification_status.value} for node in graph.nodes if node.evidence_id][:80]
    try:
        result = client.generate_json(system_prompt="你是买方投委会秘书。分别以portfolio_manager、investment_director、industry_researcher、risk_manager四个角色，针对这家公司的Thesis、证据冲突和用户历史短板各提出一个不可用套话回答的问题。返回JSON：{\"questions\":[{\"role\":\"portfolio_manager\",\"question\":\"...\",\"evidence_ids\":[\"...\"]}]}。", user_payload={"thesis": thesis.draft.model_dump(mode="json"), "evidence": evidence, "prior_errors": prior_errors}, temperature=0)
    except LLMError:
        return []
    allowed = {role.value: role for role in ROLE_ORDER}
    valid_ids = {item["id"] for item in evidence if item["id"]}
    turns = []
    for raw in result.get("questions", []):
        role = allowed.get(str(raw.get("role")))
        if role and str(raw.get("question", "")).strip():
            turns.append(DefenseTurn(role=role, question=str(raw["question"]).strip(), thesis_reference=thesis.draft.core_view, evidence_ids=[item for item in raw.get("evidence_ids", []) if item in valid_ids]))
    by_role = {turn.role: turn for turn in turns}
    return [by_role[role] for role in ROLE_ORDER if role in by_role] if len(by_role) == len(ROLE_ORDER) else []
