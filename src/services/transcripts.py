"""Deterministic multi-channel transcript parsing + phrase scan + suitability for INS-C2-049.

Pure logic, no LLM, no secrets. All rulesets (保険業法 forbidden-phrase KB, suitability matrix) are
injected from config — generic checking machinery, no hardcoded regulation. The phrase scan is
deterministic string match (auditable, no hallucination — 金融庁 inspection requirement).

- ``parse_sessions(batch)`` — normalize phone / LINE / in-person logs into unified session records.
- ``scan_phrases(sessions, phrase_kb)`` — deterministic forbidden-phrase hits (断定的判断 / 不適切勧誘).
- ``check_suitability(sessions, matrix)`` — 適合性原則 findings against the suitability matrix.
"""

from __future__ import annotations

from typing import Any

_CHANNELS = ("phone", "line", "in_person")


def parse_sessions(batch: Any) -> list[dict[str, Any]]:
    """Normalize a multi-channel transcript batch into unified session records."""
    items = batch.get("sessions") if isinstance(batch, dict) else batch
    if not isinstance(items, list):
        return []
    sessions: list[dict[str, Any]] = []
    for i, s in enumerate(items):
        if not isinstance(s, dict):
            continue
        text = str(s.get("text", "") or "").strip()
        if not text:
            continue
        channel = str(s.get("channel", "phone")).lower()
        sessions.append(
            {
                "session_id": str(s.get("session_id", f"sess-{i + 1}")),
                "channel": channel if channel in _CHANNELS else "phone",
                "agent_id": str(s.get("agent_id", "unknown")),
                "text": text,
            }
        )
    return sessions


def scan_phrases(sessions: list[dict[str, Any]], phrase_kb: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic forbidden-phrase scan. phrase_kb: {category: [phrase]}."""
    kb = phrase_kb or {}
    hits: list[dict[str, Any]] = []
    for s in sessions or []:
        low = s.get("text", "").lower()
        for category, phrases in kb.items():
            for phrase in phrases or []:
                if phrase and phrase.lower() in low:
                    hits.append(
                        {
                            "session_id": s.get("session_id", ""),
                            "agent_id": s.get("agent_id", ""),
                            "phrase": phrase,
                            "category": category,
                        }
                    )
    return hits


def check_suitability(sessions: list[dict[str, Any]], matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """適合性原則 check: a session that mentions a product must include the matrix-required phrases.

    matrix: {product: {trigger_phrases:[str], required_phrases:[str], citation}}.
    """
    matrix = matrix or {}
    findings: list[dict[str, Any]] = []
    for s in sessions or []:
        low = s.get("text", "").lower()
        for product, rule in matrix.items():
            triggers = [t.lower() for t in (rule.get("trigger_phrases") or [])]
            if triggers and not any(t in low for t in triggers):
                continue
            for req in rule.get("required_phrases") or []:
                if req and req.lower() not in low:
                    findings.append(
                        {
                            "session_id": s.get("session_id", ""),
                            "agent_id": s.get("agent_id", ""),
                            "rule_id": f"適合性-{product}",
                            "verdict": "violation",
                            "detail": f"product '{product}' explained without required '{req}'",
                            "citation": rule.get("citation", "保険業法 適合性原則"),
                        }
                    )
    return findings
