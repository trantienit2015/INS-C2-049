"""TranscriptParseNode (outer pre_process) — normalize multi-channel transcripts.

Design step 1. Parses the day's batch of pre-existing transcripts (phone / LINE / in-person) into
unified session records via services/transcripts.parse_sessions, rejects empty, and serializes them into
validated_input (JSON string) for the Cat 2 inner subgraph. Compliance data is internal-only (S-1):
require INTERNAL trust.

Node contract: execute(self, state) -> dict; partial update; status is an AgentStatus value string.
"""

from __future__ import annotations

from typing import Any
import json

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import INSC2049State
from src.services.transcripts import parse_sessions


class TranscriptParseNode(FunctionNode):
    """Normalize the multi-channel transcript batch into unified session records."""

    required_trust_level = TrustLevel.INTERNAL

    def execute(self, state: INSC2049State) -> dict[str, Any]:
        raw = state.get("user_input", "")
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": ["Empty input — transcript batch (JSON) required"],
                }
            try:
                batch = json.loads(raw)
            except (ValueError, TypeError):
                return {"status": AgentStatus.ERROR.value, "error_log": ["Input is not valid JSON transcript batch"]}
        else:
            batch = raw

        sessions = parse_sessions(batch)
        # S-4: session count only, no transcript content.
        emit_trace_event("transcript_parse", {"sessions": len(sessions)}, state)
        if not sessions:
            return {"status": AgentStatus.ERROR.value, "error_log": ["No valid transcript sessions found in batch"]}

        return {
            "sessions": sessions,
            "validated_input": json.dumps({"sessions": sessions}, ensure_ascii=False),
            "status": AgentStatus.SUCCESS.value,
        }
