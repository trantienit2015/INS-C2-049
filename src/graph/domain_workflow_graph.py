"""VoiceComplianceWorkflowGraph — Cat 2 inner domain workflow graph.

Inherits BaseGraph directly for a fully custom linear topology:

    START → phrase_scan → suitability_check → str_field_extract → compliance_summary_generate
          → str_draft_assemble → escalation_decide → END

Instantiated by VoiceComplianceGraphNode.get_subgraph() in the outer graph's `main` slot. The six steps
are the voice-compliance + STR-generation workflow; deterministic compute lives in services/. get_output()
shapes the sub_result consumed by the outer merge_output(). Downstream nodes short-circuit on upstream error.

Implements all 7 BaseGraph abstract methods. register_nodes() does NOT call super() (abstract in
BaseGraph) and does NOT register initialize/finalize (outer backbone concern).
"""

from __future__ import annotations

from typing import Any
from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus

from src.nodes.compliance_summary_generate_node import ComplianceSummaryGenerateNode
from src.nodes.escalation_decide_node import EscalationDecideNode
from src.nodes.phrase_scan_node import PhraseScanNode
from src.nodes.str_draft_assemble_node import STRDraftAssembleNode
from src.nodes.str_field_extract_node import STRFieldExtractNode
from src.nodes.suitability_check_node import SuitabilityCheckNode
from src.schemas.state import INSC2049State


class VoiceComplianceWorkflowGraph(BaseGraph):
    """Inner workflow: phrase-scan → suitability → STR-extract → summary → STR-draft → escalation."""

    @property
    def name(self) -> str:
        return "voice_compliance_workflow"

    @property
    def state_schema(self) -> type:
        return INSC2049State

    def _validate_config(self) -> None:
        pass

    def register_nodes(self) -> None:
        cfg = self.config if hasattr(self, "config") else {}
        self._nodes["phrase_scan"] = PhraseScanNode(phrase_kb=cfg.get("phrase_kb", {}))
        self._nodes["suitability_check"] = SuitabilityCheckNode(suitability_matrix=cfg.get("suitability_matrix", {}))
        self._nodes["str_field_extract"] = STRFieldExtractNode(
            llm=cfg.get("llm"),
            str_template_fields=cfg.get("str_template_fields"),
        )
        self._nodes["compliance_summary_generate"] = ComplianceSummaryGenerateNode()
        self._nodes["str_draft_assemble"] = STRDraftAssembleNode()
        self._nodes["escalation_decide"] = EscalationDecideNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "phrase_scan")
        self._sg.add_edge("phrase_scan", "suitability_check")
        self._sg.add_edge("suitability_check", "str_field_extract")
        self._sg.add_edge("str_field_extract", "compliance_summary_generate")
        self._sg.add_edge("compliance_summary_generate", "str_draft_assemble")
        self._sg.add_edge("str_draft_assemble", "escalation_decide")
        self._sg.add_edge("escalation_decide", END)

    def route(self, state: AgentState) -> str:
        return END if state.get("status") == AgentStatus.ERROR.value else "escalation_decide"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "sessions": state.get("sessions", []),
            "phrase_hits": state.get("phrase_hits", []),
            "suitability_findings": state.get("suitability_findings", []),
            "str_fields": state.get("str_fields", []),
            "compliance_summary": state.get("compliance_summary", []),
            "str_drafts": state.get("str_drafts", []),
            "escalation_level": state.get("escalation_level", "none"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
