from __future__ import annotations

from .agents import run_gate_blocked_memo
from .llm_agents import run_research_memo_generator_llm
from .models import ResearchMemo, WorkflowState


def run_memo_writing_skill(state: WorkflowState) -> ResearchMemo:
    """Format approved research only; this Skill cannot overrule the Judge."""
    if not state.pre_memo_gate or state.pre_memo_gate.status != "pass":
        return run_gate_blocked_memo(state)
    memo = run_research_memo_generator_llm(state)
    valid_ids = {item.evidence_id for item in state.evidence_items}
    for section in memo.sections:
        section.evidence_ids = [item for item in section.evidence_ids if item in valid_ids]
    return memo
