"""SuitabilityCheckNode (inner step_b) — 適合性原則 suitability check.

Second node of the Cat 2 inner subgraph. Checks each session against the 適合性原則 suitability matrix
(product × required explanation) via services/transcripts.check_suitability. Matrix injected via config.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State
from src.services.transcripts import check_suitability


class SuitabilityCheckNode(FunctionNode):
    """適合性原則 suitability findings."""

    # Inner subgraph node: the caller is authenticated once at the outer backbone (INTERNAL).
    required_trust_level = TrustLevel.ANONYMOUS

    def __init__(self, suitability_matrix: Any = None) -> None:
        self._matrix = suitability_matrix or {}

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        if state.get("status") in (AgentStatus.ERROR.value,):
            return {"status": AgentStatus.ERROR.value}  # short-circuit: an upstream inner step already errored
        sessions = state.get("sessions", [])
        if not sessions:
            return {"status": AgentStatus.ERROR.value, "error_log": ["suitability_check: no sessions"]}
        findings = check_suitability(sessions, self._matrix)
        emit_trace_event("suitability_check", {"sessions": len(sessions), "findings": len(findings)}, state)
        return {"suitability_findings": findings, "status": AgentStatus.SUCCESS.value}
