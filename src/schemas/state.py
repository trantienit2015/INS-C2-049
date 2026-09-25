"""State schema for INS-C2-049 — Insurance Agency Multi-Channel Voice Compliance Summary & STR Generation.

Flat TypedDict extending AgentState. Only agent-specific fields declared here; shared fields inherited.
All fields flat / JSON-serializable — no Pydantic, dataclasses, credentials, or InvocationContext
(S-5 + #8). Consumes pre-transcribed text (no audio); produces a 犯収法 STR draft + compliance summary.
"""

from __future__ import annotations

from typing import Any
from framework.schemas.agent_state import AgentState


class INSC2049State(AgentState):
    # --- TranscriptParse (pre_process) output ---
    # Unified session records: {session_id, channel, agent_id, text}
    sessions: list[dict[str, Any]]

    # --- PhraseScan (inner) output — deterministic, auditable (no LLM) ---
    # {session_id, phrase, category: "断定的判断"|"不適切勧誘", segment}
    phrase_hits: list[dict[str, Any]]

    # --- SuitabilityCheck (inner) output ---
    suitability_findings: list[dict[str, Any]]  # {session_id, rule_id, verdict, detail}

    # --- STRFieldExtract (inner) output ---
    str_fields: list[dict[str, Any]]  # per flagged session: {session_id, fields: {<24 犯収法 fields>}}

    # --- ComplianceSummaryGenerate (inner) output ---
    compliance_summary: list[dict[str, Any]]  # per-agent: {agent_id, hits, findings, sessions_reviewed}

    # --- STRDraftAssemble (inner) output ---
    str_drafts: list[dict[str, Any]]  # {session_id, str_draft}

    # --- EscalationDecide (inner) output ---
    escalation_level: str  # "none" | "review" | "file_str"

    # --- ReportFinalize (post_process) output ---
    final_report: dict[str, Any]  # summary + STR drafts + escalation + citations
