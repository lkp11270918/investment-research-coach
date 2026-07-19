from __future__ import annotations

from collections import Counter, defaultdict

from .models import CapabilityDimension, CapabilityProfile, DefenseSession, ResearchRunDetail, ThesisVersion


DIMENSIONS = ["financial_analysis", "business_model", "valuation", "evidence_awareness", "counter_evidence", "management_analysis", "industry_understanding", "memo_writing", "defense"]

ROLE_DIMENSION = {"portfolio_manager": "valuation", "industry_researcher": "industry_understanding", "financial_researcher": "financial_analysis", "risk_manager": "counter_evidence"}
REVIEW_DIMENSION = {"evidence_gap": "evidence_awareness", "unsupported_claim": "evidence_awareness", "sell_side_repetition": "management_analysis", "value_trap_omission": "counter_evidence", "doctrine_mismatch": "valuation", "rewrite_guidance": "memo_writing"}


def build_capability_profile(user_id: str, runs: list[ResearchRunDetail], theses: list[ThesisVersion], defenses: list[DefenseSession]) -> CapabilityProfile:
    scores: dict[str, list[float]] = defaultdict(list)
    evidence: dict[str, list[str]] = defaultdict(list)
    errors: dict[str, Counter[str]] = defaultdict(Counter)
    for defense in defenses:
        for turn in defense.turns:
            if turn.score is None: continue
            dimension = ROLE_DIMENSION[turn.role.value]
            scores[dimension].append(turn.score)
            evidence[dimension].append(f"答辩 {defense.session_id}：{turn.role.value} {turn.score:.0f}分")
            if not turn.passed and turn.feedback: errors[dimension][turn.feedback] += 1
        if defense.overall_score is not None:
            scores["defense"].append(defense.overall_score)
            evidence["defense"].append(f"答辩 {defense.session_id} 总分 {defense.overall_score:.0f}")
    for thesis in theses:
        score = thesis.assessment.evidence_coverage
        scores["evidence_awareness"].append(score)
        scores["counter_evidence"].append(100 if thesis.draft.counter_evidence_ids else 20)
        evidence["evidence_awareness"].append(f"Thesis v{thesis.version}证据覆盖 {score:.0f}%")
        for issue in thesis.assessment.issues:
            dimension = "counter_evidence" if "反证" in issue or "推翻" in issue else "evidence_awareness"
            errors[dimension][issue] += 1
    for run in runs:
        review = run.state.agent_outputs.get("research_coach_review")
        if not review: continue
        for finding in review.findings:
            dimension = REVIEW_DIMENSION.get(finding.classification)
            if dimension:
                penalty_score = 75 if finding.classification == "strength" else 40
                scores[dimension].append(penalty_score)
                evidence[dimension].append(f"Review {run.summary.run_id}：{finding.title}")
                if penalty_score < 60: errors[dimension][finding.title] += 1
    dimensions: list[CapabilityDimension] = []
    for dimension in DIMENSIONS:
        values = scores[dimension]
        score = round(sum(values) / len(values), 1) if values else 50.0
        repeated = [message for message, count in errors[dimension].items() if count >= 2]
        dimensions.append(CapabilityDimension(dimension=dimension, score=score, evidence=evidence[dimension][-5:], repeated_errors=repeated))
    strengths = [item.dimension for item in sorted(dimensions, key=lambda item: item.score, reverse=True)[:3] if item.score >= 60]
    weak = sorted(dimensions, key=lambda item: item.score)[:3]
    priorities = [item.dimension for item in weak]
    tasks = [f"完成一次针对 {item.dimension} 的补证据与答辩训练" for item in weak]
    return CapabilityProfile(user_id=user_id, dimensions=dimensions, strengths=strengths, priorities=priorities, recommended_tasks=tasks, sample_count=len(runs) + len(theses) + len(defenses))
