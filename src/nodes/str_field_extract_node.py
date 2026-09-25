"""STRFieldExtractNode (inner step_c) — extract 犯収法 STR fields from flagged sessions.

Third node of the Cat 2 inner subgraph. For each flagged session (any phrase hit / suitability finding),
populates the 24 犯収法 STR fields. Deterministic baseline (services/str_report.baseline_str_fields) is
the source of truth; an LLM (optional, injected) enriches free-text fields. An LLM failure is LOGGED with
the correlation_id (never silently swallowed) and degrades to the deterministic fields. S-4 audit on LLM.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
import logging

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State
from src.services.str_report import baseline_str_fields, flagged_sessions

logger = logging.getLogger(__name__)


class STRFieldExtractNode(FunctionNode):
    """Extract the 犯収法 STR fields for each flagged session."""

    # Inner subgraph node: the caller is authenticated once at the outer backbone (INTERNAL).
    required_trust_level = TrustLevel.ANONYMOUS

    def __init__(self, llm: Any = None, str_template_fields: Any = None) -> None:
        self._llm = llm
        self._template_fields = str_template_fields

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        if state.get("status") in (AgentStatus.ERROR.value,):
            return {"status": AgentStatus.ERROR.value}  # short-circuit: an upstream inner step already errored

        sessions = state.get("sessions", [])
        hits = state.get("phrase_hits", [])
        findings = state.get("suitability_findings", [])
        flagged_ids = set(flagged_sessions(sessions, hits, findings))
        by_id = {s.get("session_id"): s for s in sessions}

        str_fields: list[dict[str, Any]] = []
        llm_used = False
        for sid in flagged_ids:
            session = by_id.get(sid, {"session_id": sid})
            fields = baseline_str_fields(session, hits, findings, self._template_fields)
            if self._llm is not None:
                try:
                    enriched = self._llm.complete(
                        "Extract 犯収法 STR free-text fields from this session: " + session.get("text", "")
                    )
                    if isinstance(enriched, dict):
                        fields.update({k: v for k, v in enriched.items() if k in fields})
                    llm_used = True
                except Exception as exc:  # noqa: BLE001 — degrade, never silently
                    logger.warning(
                        "str_field_extract: LLM failed (correlation_id=%s, session=%s): %s",
                        state.get("correlation_id", ""),
                        sid,
                        exc,
                    )
            str_fields.append({"session_id": sid, "fields": fields})

        emit_trace_event("str_field_extract", {"flagged": len(flagged_ids), "llm_used": llm_used}, state)
        return {"str_fields": str_fields, "status": AgentStatus.SUCCESS.value}
