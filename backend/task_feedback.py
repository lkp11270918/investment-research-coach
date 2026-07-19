from __future__ import annotations

import hashlib

from .models import EvidenceGraph, MemoVersion, ResearchMap, ResearchTask, ThesisVersion


def tasks_from_research_state(project_id: str, research_map: ResearchMap, graph: EvidenceGraph) -> list[ResearchTask]:
    tasks = []
    for question in research_map.questions:
        if question.status.value == "answered":
            continue
        tasks.append(ResearchTask(project_id=project_id, title=f"补全研究问题：{question.question}", detail="；".join(question.missing_materials) or "补充并确认能够直接回答该问题的证据", source_type="research_map", source_id=f"map:{question.question_id}", priority=question.priority, evidence_ids=question.evidence_ids))
    for conflict in graph.conflicts:
        key = hashlib.sha256(conflict.encode()).hexdigest()[:12]
        tasks.append(ResearchTask(project_id=project_id, title="核对证据冲突", detail=conflict, source_type="evidence_conflict", source_id=f"conflict:{key}", priority=1))
    return tasks


def tasks_from_thesis(thesis: ThesisVersion) -> list[ResearchTask]:
    return [ResearchTask(project_id=thesis.project_id, title="补强 Thesis", detail=issue, source_type="thesis", source_id=f"thesis:{thesis.thesis_id}:{index}", priority=1 if "反证" in issue or "推翻" in issue else 2, evidence_ids=thesis.draft.supporting_evidence_ids + thesis.draft.counter_evidence_ids) for index, issue in enumerate(thesis.assessment.issues)]


def tasks_from_memo(version: MemoVersion) -> list[ResearchTask]:
    return [ResearchTask(project_id=version.project_id, title="补强 Memo 证据与表达", detail=issue, source_type="memo", source_id=f"memo:{version.memo_version_id}:{index}", priority=1, evidence_ids=[evidence_id for section in version.sections for evidence_id in section.evidence_ids]) for index, issue in enumerate(version.gate_issues)]
