"""EscalationDecideNode (inner step_f) — decide the escalation level.

Sixth node of the Cat 2 inner subgraph. Decides none / review / file_str from the phrase hits +
suitability findings + STR drafts via services/str_report.decide_escalation.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State
from src.services.str_report import decide_escalation


class EscalationDecideNode(FunctionNode):
    """Decide the escalation level."""

    # Inner subgraph node: the caller is authenticated once at the outer backbone (INTERNAL).
    required_trust_level = TrustLevel.ANONYMOUS

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        if state.get("status") in (AgentStatus.ERROR.value,):
            return {"status": AgentStatus.ERROR.value}  # short-circuit: an upstream inner step already errored
        level = decide_escalation(
            state.get("phrase_hits", []), state.get("suitability_findings", []), state.get("str_drafts", [])
        )
        emit_trace_event("escalation_decide", {"escalation_level": level}, state)
        return {"escalation_level": level, "status": AgentStatus.SUCCESS.value}
