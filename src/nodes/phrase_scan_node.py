"""PhraseScanNode (inner step_a) — deterministic 保険業法 forbidden-phrase scan.

First node of the Cat 2 inner subgraph. Parses the JSON sessions (validated_input) and scans them
deterministically against the 保険業法 forbidden-phrase KB (断定的判断 / 不適切勧誘) via
services/transcripts.scan_phrases. Deterministic string match — auditable, NO LLM, NO hallucination
(金融庁 inspection requirement). KB injected via the inner graph config. S-4 audit.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus enum.
"""

from __future__ import annotations

from typing import Any
import json

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State
from src.services.transcripts import scan_phrases


class PhraseScanNode(FunctionNode):
    """Deterministic 保険業法 forbidden-phrase detection."""

    # Inner subgraph node: the caller is authenticated once at the outer backbone (INTERNAL).
    required_trust_level = TrustLevel.ANONYMOUS

    def __init__(self, phrase_kb: Any = None) -> None:
        self._phrase_kb = phrase_kb or {}

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        raw = state.get("user_input", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
            sessions = payload.get("sessions") if isinstance(payload, dict) else payload
        except (ValueError, TypeError):
            sessions = None
        if not isinstance(sessions, list) or not sessions:
            return {"status": AgentStatus.ERROR.value, "error_log": ["phrase_scan: no sessions in inner input"]}

        hits = scan_phrases(sessions, self._phrase_kb)
        emit_trace_event("phrase_scan", {"sessions": len(sessions), "hits": len(hits)}, state)
        return {"sessions": sessions, "phrase_hits": hits, "status": AgentStatus.SUCCESS.value}
