"""ComplianceSummaryGenerateNode (inner step_d) — per-agent compliance summary.

Fourth node of the Cat 2 inner subgraph. Aggregates phrase hits + suitability findings into a per-agent
compliance summary (deterministic). No LLM.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State


class ComplianceSummaryGenerateNode(FunctionNode):
    """Per-agent compliance summary from hits + findings."""

    # Inner subgraph node: the caller is authenticated once at the outer backbone (INTERNAL).
    required_trust_level = TrustLevel.ANONYMOUS

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        if state.get("status") in (AgentStatus.ERROR.value,):
            return {"status": AgentStatus.ERROR.value}  # short-circuit: an upstream inner step already errored

        sessions = state.get("sessions", [])
        hits = state.get("phrase_hits", [])
        findings = state.get("suitability_findings", [])

        agents: dict[str, dict[str, Any]] = {}
        for s in sessions:
            a = agents.setdefault(
                s.get("agent_id", "unknown"),
                {"agent_id": s.get("agent_id", "unknown"), "hits": 0, "findings": 0, "sessions_reviewed": 0},
            )
            a["sessions_reviewed"] += 1
        for h in hits:
            agents.setdefault(
                h.get("agent_id", "unknown"),
                {"agent_id": h.get("agent_id", "unknown"), "hits": 0, "findings": 0, "sessions_reviewed": 0},
            )["hits"] += 1
        for f in findings:
            agents.setdefault(
                f.get("agent_id", "unknown"),
                {"agent_id": f.get("agent_id", "unknown"), "hits": 0, "findings": 0, "sessions_reviewed": 0},
            )["findings"] += 1

        emit_trace_event("compliance_summary_generate", {"agents": len(agents)}, state)
        return {"compliance_summary": list(agents.values()), "status": AgentStatus.SUCCESS.value}
