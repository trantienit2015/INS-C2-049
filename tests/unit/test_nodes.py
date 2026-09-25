# INS-C2-049 — Unit tests: nodes

import json

from framework.schemas.agent_status import AgentStatus
from src.nodes.compliance_summary_generate_node import ComplianceSummaryGenerateNode
from src.nodes.escalation_decide_node import EscalationDecideNode
from src.nodes.phrase_scan_node import PhraseScanNode
from src.nodes.report_finalize_node import ReportFinalizeNode
from src.nodes.str_draft_assemble_node import STRDraftAssembleNode
from src.nodes.str_field_extract_node import STRFieldExtractNode
from src.nodes.suitability_check_node import SuitabilityCheckNode
from src.nodes.transcript_parse_node import TranscriptParseNode

_PHRASE_KB = {"断定的判断": ["必ず儲か"], "不適切勧誘": ["今だけ特別"]}
_SESSIONS = [
    {"session_id": "c1", "channel": "phone", "agent_id": "A001", "text": "必ず儲かります"},
    {"session_id": "c2", "channel": "line", "agent_id": "A002", "text": "ありがとうございました"},
]


def _st(**kw):
    base = {"node_history": [], "error_log": [], "correlation_id": "c1"}
    base.update(kw)
    return base


class TestTranscriptParse:
    def test_success(self):
        p = json.dumps({"sessions": _SESSIONS})
        r = TranscriptParseNode().execute(_st(user_input=p))
        assert r["status"] == AgentStatus.SUCCESS and len(r["sessions"]) == 2

    def test_empty_errors(self):
        assert TranscriptParseNode().execute(_st(user_input="  "))["status"] == AgentStatus.ERROR

    def test_no_sessions_errors(self):
        assert TranscriptParseNode().execute(_st(user_input=json.dumps({"sessions": []})))["status"] == AgentStatus.ERROR


class TestPhraseScan:
    def test_deterministic_hit(self):
        p = json.dumps({"sessions": _SESSIONS})
        r = PhraseScanNode(phrase_kb=_PHRASE_KB).execute(_st(user_input=p))
        assert r["status"] == AgentStatus.SUCCESS
        assert any(h["session_id"] == "c1" and h["category"] == "断定的判断" for h in r["phrase_hits"])

    def test_no_sessions_errors(self):
        assert PhraseScanNode().execute(_st(user_input="{}"))["status"] == AgentStatus.ERROR


class TestSuitabilityCheck:
    def test_violation(self):
        matrix = {"変額保険": {"trigger_phrases": ["変額保険"], "required_phrases": ["リスク"]}}
        sessions = [{"session_id": "c1", "agent_id": "A", "text": "変額保険のご案内"}]
        r = SuitabilityCheckNode(suitability_matrix=matrix).execute(_st(sessions=sessions))
        assert r["suitability_findings"]

    def test_upstream_error_passthrough(self):
        assert SuitabilityCheckNode().execute(_st(status=AgentStatus.ERROR.value))["status"] == AgentStatus.ERROR


class TestSTRFieldExtract:
    def test_extracts_for_flagged(self):
        hits = [{"session_id": "c1", "agent_id": "A001", "phrase": "必ず儲か", "category": "断定的判断"}]
        r = STRFieldExtractNode().execute(_st(sessions=_SESSIONS, phrase_hits=hits, suitability_findings=[]))
        assert any(e["session_id"] == "c1" for e in r["str_fields"])

    def test_llm_failure_degrades(self, caplog):
        class _Bad:
            def complete(self, p):
                raise RuntimeError("down")
        hits = [{"session_id": "c1", "agent_id": "A001", "phrase": "必ず儲か", "category": "断定的判断"}]
        with caplog.at_level("WARNING"):
            r = STRFieldExtractNode(llm=_Bad()).execute(_st(sessions=_SESSIONS, phrase_hits=hits, suitability_findings=[]))
        assert r["status"] == AgentStatus.SUCCESS
        assert any("LLM failed" in rec.message for rec in caplog.records)


class TestComplianceSummaryGenerate:
    def test_per_agent(self):
        hits = [{"session_id": "c1", "agent_id": "A001", "phrase": "x", "category": "断定的判断"}]
        r = ComplianceSummaryGenerateNode().execute(_st(sessions=_SESSIONS, phrase_hits=hits, suitability_findings=[]))
        a001 = [a for a in r["compliance_summary"] if a["agent_id"] == "A001"][0]
        assert a001["hits"] == 1


class TestSTRDraftAssemble:
    def test_assembles(self):
        r = STRDraftAssembleNode().execute(_st(str_fields=[{"session_id": "c1", "fields": {"report_type": "犯収法 STR", "agent_id": "A001"}}]))
        assert r["str_drafts"][0]["str_draft"].startswith("# 犯収法")


class TestEscalationDecide:
    def test_file_str(self):
        r = EscalationDecideNode().execute(_st(phrase_hits=[{"x": 1}], suitability_findings=[], str_drafts=[{"y": 1}]))
        assert r["escalation_level"] == "file_str"

    def test_none(self):
        r = EscalationDecideNode().execute(_st(phrase_hits=[], suitability_findings=[], str_drafts=[]))
        assert r["escalation_level"] == "none"


class TestReportFinalize:
    def test_finalize(self):
        r = ReportFinalizeNode().execute(_st(compliance_summary=[{"agent_id": "A001"}],
                                             str_drafts=[{"session_id": "c1"}], escalation_level="file_str",
                                             phrase_hits=[{"x": 1}], suitability_findings=[]))
        assert r["status"] == AgentStatus.SUCCESS
        assert r["final_report"]["escalation_level"] == "file_str"
        assert r["final_report"]["disclaimer"]
