"""Deterministic 犯収法 STR field assembly + escalation + report for INS-C2-049.

Pure logic, no secrets. The 24 犯収法 STR field set is injected from config (the STR template); the
deterministic baseline populates what it can from the session + findings, and the LLM (when injected,
in the node) enriches free-text fields. This module is the deterministic source of truth + assembler.

- ``flagged_sessions(sessions, phrase_hits, suitability_findings)`` — sessions with any compliance flag.
- ``baseline_str_fields(session, hits, findings, template_fields)`` — populate STR fields deterministically.
- ``decide_escalation(phrase_hits, suitability_findings, str_drafts)`` — none / review / file_str.
- ``build_report(...)`` — final compliance summary + STR drafts + escalation + citations.
"""

from __future__ import annotations

from typing import Any

# Minimal default 犯収法 STR field set (overridable via config `str_template_fields`).
_DEFAULT_STR_FIELDS = [
    "report_type",
    "agency_id",
    "agent_id",
    "session_id",
    "channel",
    "customer_ref",
    "product",
    "transaction_summary",
    "suspicion_grounds",
    "detected_phrases",
    "suitability_issues",
    "escalation_level",
]


def flagged_sessions(sessions: Any, phrase_hits: Any, suitability_findings: Any) -> list[str]:
    flagged = {h.get("session_id") for h in (phrase_hits or [])}
    flagged |= {f.get("session_id") for f in (suitability_findings or [])}
    return [s.get("session_id") for s in (sessions or []) if s.get("session_id") in flagged]


def baseline_str_fields(
    session: dict[str, Any], hits: list[dict[str, Any]], findings: list[dict[str, Any]], template_fields: Any = None
) -> dict[str, Any]:
    fields = {k: "" for k in (template_fields or _DEFAULT_STR_FIELDS)}
    sid = session.get("session_id", "")
    fields.update(
        {
            "report_type": "犯収法 STR",
            "agent_id": session.get("agent_id", ""),
            "session_id": sid,
            "channel": session.get("channel", ""),
            "detected_phrases": "; ".join(h["phrase"] for h in hits if h.get("session_id") == sid),
            "suitability_issues": "; ".join(f["detail"] for f in findings if f.get("session_id") == sid),
            "suspicion_grounds": "forbidden-phrase / suitability violation detected in sales conversation",
        }
    )
    return fields


def decide_escalation(phrase_hits: Any, suitability_findings: Any, str_drafts: Any) -> str:
    if str_drafts:
        return "file_str"
    if phrase_hits or suitability_findings:
        return "review"
    return "none"


def build_report(
    compliance_summary: Any, str_drafts: Any, escalation_level: Any, phrase_hits: Any, suitability_findings: Any
) -> dict[str, Any]:
    citations = sorted(
        {"保険業法"} | {f.get("citation", "") for f in (suitability_findings or []) if f.get("citation")}
    )
    return {
        "compliance_summary": compliance_summary,
        "str_drafts": str_drafts,
        "escalation_level": escalation_level,
        "evidence": {
            "phrase_hits": phrase_hits,
            "suitability_findings": suitability_findings,
        },
        "citations": [c for c in citations if c],
        "disclaimer": "Advisory — human review required before STR submission to JAFIO.",
    }
