"""ReportFinalizeNode (outer post_process) — finalize the compliance report + S-4 audit.

Design step (ReportFinalize). Assembles the final report (per-agent compliance summary + STR drafts
+ escalation level + evidence citations) from the fields merged back from the inner subgraph, via
services/str_report.build_report. Emits the S-4 audit event. Human-in-loop before JAFIO submission
(advisory disclaimer enforced).

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State
from src.services.str_report import build_report


class ReportFinalizeNode(FunctionNode):
    """Finalize the compliance summary + STR drafts + escalation report."""

    # Outer post_process: same boundary as the entry node (compliance data is internal-only).
    required_trust_level = TrustLevel.INTERNAL

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        report = build_report(
            compliance_summary=state.get("compliance_summary", []),
            str_drafts=state.get("str_drafts", []),
            escalation_level=state.get("escalation_level", "none"),
            phrase_hits=state.get("phrase_hits", []),
            suitability_findings=state.get("suitability_findings", []),
        )

        emit_trace_event(
            "voice_compliance_report",
            {
                "escalation": report["escalation_level"],
                "str_drafts": len(report["str_drafts"]),
                "phrase_hits": len(state.get("phrase_hits", [])),
            },
            state,
        )

        return {
            "final_report": report,
            "formatted_output": report,
            "status": AgentStatus.SUCCESS.value,
        }
