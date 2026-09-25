"""INSC2049Graph — Cat 2 outer graph (AgentBaseGraph, L1 direct).

Cat 2 pattern: the outer graph owns the fixed 5-node backbone (initialize → pre_process → main →
post_process → finalize); the multi-step voice-compliance + STR-generation workflow is encapsulated in
VoiceComplianceGraphNode (a GraphNode) in the `main` slot, wrapping the inner VoiceComplianceWorkflowGraph.

Node mapping (8 design steps → 5-node backbone):
  - TranscriptParse              → pre_process
  - PhraseScan                    ┐ (deterministic 保険業法 scan, no LLM)
  - SuitabilityCheck              │
  - STRFieldExtract               ├→ inner VoiceComplianceWorkflowGraph (main via VoiceComplianceGraphNode)
  - ComplianceSummaryGenerate     │
  - STRDraftAssemble              │
  - EscalationDecide              ┘
  - ReportFinalize               → post_process (S-4 audit)

Public entry: Graph().compile() then .invoke(user_input, ctx=ctx). No _invoke_impl, no .run(),
no add_edges() override.
"""

from __future__ import annotations

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel

from src.nodes.report_finalize_node import ReportFinalizeNode
from src.nodes.transcript_parse_node import TranscriptParseNode
from src.schemas.state import INSC2049State


class VoiceComplianceGraphNode(GraphNode):
    """Inner-workflow wrapper for the voice-compliance + STR-generation pipeline.

    Lives next to the outer graph (canonical Cat 2 layout): a GraphNode's __call__ skips the
    FunctionNode S-2/S-3 lifecycle and delegates gating to the inner subgraph. Its S-1 gate and
    boundary mapping are covered by tests/proof_of_boundary/test_pb_graphnode_boundary.py.
    """

    # S-1: outer main-slot wrapper; same boundary as the entry node and agent.yaml.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.INTERNAL
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def __init__(
        self, phrase_kb: Any = None, suitability_matrix: Any = None, str_template_fields: Any = None, llm: Any = None
    ) -> None:
        super().__init__()
        self._phrase_kb = phrase_kb or {}
        self._suitability_matrix = suitability_matrix or {}
        self._str_template_fields = str_template_fields
        self._llm = llm

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import VoiceComplianceWorkflowGraph

        subgraph = VoiceComplianceWorkflowGraph(config=self._parent_config())
        subgraph.compile()
        return subgraph

    def extract_input(self, state: AgentState) -> str:
        return cast(str, state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "sessions": sub_result.get("sessions", []),
            "phrase_hits": sub_result.get("phrase_hits", []),
            "suitability_findings": sub_result.get("suitability_findings", []),
            "str_fields": sub_result.get("str_fields", []),
            "compliance_summary": sub_result.get("compliance_summary", []),
            "str_drafts": sub_result.get("str_drafts", []),
            "escalation_level": sub_result.get("escalation_level", "none"),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {
            "phrase_kb": self._phrase_kb,
            "suitability_matrix": self._suitability_matrix,
            "str_template_fields": self._str_template_fields,
            "llm": self._llm,
        }


class INSC2049Graph(AgentBaseGraph):
    """Insurance agency multi-channel voice compliance summary & 犯収法 STR generation (Cat 2, DocGen)."""

    @property
    def name(self) -> str:
        return "ins-c2-049"

    @property
    def state_schema(self) -> type:
        return INSC2049State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects default initialize + finalize
        cfg = self.config if hasattr(self, "config") else {}
        self._nodes["pre_process"] = TranscriptParseNode()
        self._nodes["main"] = VoiceComplianceGraphNode(
            phrase_kb=cfg.get("phrase_kb", {}),
            suitability_matrix=cfg.get("suitability_matrix", {}),
            str_template_fields=cfg.get("str_template_fields"),
            llm=cfg.get("llm"),
        )
        self._nodes["post_process"] = ReportFinalizeNode()

    # add_edges() is NOT overridden — backbone wiring belongs to AgentBaseGraph.


# Alias so config/agent.yaml `module: "src.graph"` resolves a stable `Graph` symbol too.
Graph = INSC2049Graph
