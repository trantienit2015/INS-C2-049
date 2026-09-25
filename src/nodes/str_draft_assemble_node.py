"""STRDraftAssembleNode (inner step_e) — assemble submission-ready 犯収法 STR drafts.

Fifth node of the Cat 2 inner subgraph. Populates the 犯収法 STR template per flagged session from the
extracted STR fields → submission-ready draft (deterministic). No LLM.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State


class STRDraftAssembleNode(FunctionNode):
    """Assemble the 犯収法 STR draft per flagged session."""

    # Inner subgraph node: the caller is authenticated once at the outer backbone (INTERNAL).
    required_trust_level = TrustLevel.ANONYMOUS

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        if state.get("status") in (AgentStatus.ERROR.value,):
            return {"status": AgentStatus.ERROR.value}  # short-circuit: an upstream inner step already errored

        drafts: list[dict[str, Any]] = []
        for entry in state.get("str_fields", []):
            fields = dict(entry.get("fields", {}))
            sid = entry.get("session_id", "")
            lines = ["# 犯収法 疑わしい取引の届出 (STR) ドラフト", f"- session: {sid}"]
            lines += [f"- {k}: {v}" for k, v in fields.items() if v]
            drafts.append({"session_id": sid, "fields": fields, "str_draft": "\n".join(lines)})

        emit_trace_event("str_draft_assemble", {"drafts": len(drafts)}, state)
        return {"str_drafts": drafts, "status": AgentStatus.SUCCESS.value}
