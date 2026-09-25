# INS-C2-049 — Unit tests: deterministic services (transcripts / str_report)

from src.services.str_report import baseline_str_fields, build_report, decide_escalation, flagged_sessions
from src.services.transcripts import check_suitability, parse_sessions, scan_phrases

_SESSIONS = [
    {"session_id": "c1", "channel": "phone", "agent_id": "A001", "text": "必ず儲かります"},
    {"session_id": "c2", "channel": "line", "agent_id": "A002", "text": "ありがとう"},
]


class TestTranscripts:
    def test_parse_normalizes(self):
        out = parse_sessions({"sessions": [{"session_id": "c1", "channel": "PHONE", "text": "hi"}]})
        assert out[0]["channel"] == "phone"

    def test_parse_drops_empty(self):
        assert parse_sessions({"sessions": [{"session_id": "c1", "text": ""}]}) == []

    def test_scan_phrases(self):
        hits = scan_phrases(_SESSIONS, {"断定的判断": ["必ず儲か"]})
        assert hits and hits[0]["session_id"] == "c1"

    def test_check_suitability_violation(self):
        matrix = {"変額保険": {"trigger_phrases": ["変額保険"], "required_phrases": ["リスク"]}}
        sessions = [{"session_id": "c1", "agent_id": "A", "text": "変額保険です"}]
        assert check_suitability(sessions, matrix)

    def test_check_suitability_no_trigger(self):
        matrix = {"変額保険": {"trigger_phrases": ["変額保険"], "required_phrases": ["リスク"]}}
        sessions = [{"session_id": "c1", "agent_id": "A", "text": "普通の会話"}]
        assert check_suitability(sessions, matrix) == []


class TestSTRReport:
    def test_flagged_sessions(self):
        hits = [{"session_id": "c1"}]
        assert flagged_sessions(_SESSIONS, hits, []) == ["c1"]

    def test_baseline_fields(self):
        f = baseline_str_fields(_SESSIONS[0], [{"session_id": "c1", "phrase": "必ず儲か"}], [])
        assert f["report_type"] == "犯収法 STR" and "必ず儲か" in f["detected_phrases"]

    def test_escalation(self):
        assert decide_escalation([{"x": 1}], [], [{"y": 1}]) == "file_str"
        assert decide_escalation([{"x": 1}], [], []) == "review"
        assert decide_escalation([], [], []) == "none"

    def test_build_report(self):
        rep = build_report([{"agent_id": "A"}], [{"session_id": "c1"}], "file_str", [{"x": 1}], [])
        assert rep["escalation_level"] == "file_str" and rep["disclaimer"]
