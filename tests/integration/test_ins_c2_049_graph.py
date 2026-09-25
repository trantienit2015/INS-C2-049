# INS-C2-049 — Integration tests: full outer graph compile() + invoke()

import json

from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from src.graph.graph import Graph

_PHRASE_KB = {"断定的判断": ["必ず儲か", "元本保証"], "不適切勧誘": ["今だけ特別"]}
_SUITABILITY = {"変額保険": {"trigger_phrases": ["変額保険"], "required_phrases": ["リスク"], "citation": "保険業法 適合性原則"}}


def _agent():
    agent = Graph(config={"phrase_kb": _PHRASE_KB, "suitability_matrix": _SUITABILITY})
    agent.compile()
    return agent


def _ctx():
    return InvocationContext(session_id="s1", caller_trust_level=TrustLevel.INTERNAL, caller_id="agencyA")


class TestINSC2049Graph:
    def test_full_pipeline_flags_and_str(self):
        batch = {"sessions": [
            {"session_id": "c1", "channel": "phone", "agent_id": "A001", "text": "この変額保険は必ず儲かります"},
            {"session_id": "c2", "channel": "line", "agent_id": "A002", "text": "本日はありがとうございました"},
        ]}
        r = _agent().invoke(json.dumps(batch, ensure_ascii=False), ctx=_ctx())
        assert r["status"] in (AgentStatus.SUCCESS, AgentStatus.SUCCESS.value)
        out = r.get("output") or r.get("formatted_output")
        assert isinstance(out, dict)
        assert out["escalation_level"] == "file_str"  # forbidden phrase + suitability → STR drafted
        assert out["str_drafts"]
        assert out["evidence"]["phrase_hits"]

    def test_clean_batch_no_escalation(self):
        batch = {"sessions": [{"session_id": "c1", "channel": "phone", "agent_id": "A001", "text": "本日はありがとうございました"}]}
        r = _agent().invoke(json.dumps(batch, ensure_ascii=False), ctx=_ctx())
        out = r.get("output") or r.get("formatted_output")
        assert out["escalation_level"] == "none"

    def test_backbone_node_history(self):
        batch = {"sessions": [{"session_id": "c1", "channel": "phone", "agent_id": "A001", "text": "普通の会話"}]}
        r = _agent().invoke(json.dumps(batch, ensure_ascii=False), ctx=_ctx())
        h = r.get("node_history", [])
        assert "TranscriptParseNode" in h and "VoiceComplianceGraphNode" in h and "ReportFinalizeNode" in h

    def test_empty_errors(self):
        assert _agent().invoke("", ctx=_ctx())["status"] in (AgentStatus.ERROR, AgentStatus.ERROR.value)
