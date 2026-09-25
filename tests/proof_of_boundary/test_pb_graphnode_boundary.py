# INS-C2-049 - GraphNode boundary test (Cat 2 outer main-slot wrapper).
#
# PB-6 (test_pb_invoke_order.py) discovers BaseNode subclasses under src/nodes/ only.
# VoiceComplianceGraphNode lives in src/graph/graph.py (canonical Cat 2 layout) and
# subclasses GraphNode directly, so this file covers its S-1 gate, its boundary mapping
# and the inner FunctionNode chain it delegates S-2/S-3 gating to.

import json

from framework.nodes.function_node import FunctionNode
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import VoiceComplianceGraphNode
from src.nodes.phrase_scan_node import PhraseScanNode


def _node():
    return VoiceComplianceGraphNode()


class TestGraphNodeS1TrustGate:
    def test_insufficient_trust_returns_error_without_invoking_subgraph(self, monkeypatch):
        node = _node()
        called = {"get_subgraph": False}

        def _spy_get_subgraph():
            called["get_subgraph"] = True
            raise AssertionError("get_subgraph() must not run when the S-1 gate denies")

        monkeypatch.setattr(node, "get_subgraph", _spy_get_subgraph)
        state = {
            "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
            "validated_input": json.dumps({"sessions": [{"session_id": "s1", "text": "hello"}]}),
        }
        out = node(state)

        assert out["status"] == "error"
        assert any("S-1 trust gate denied" in e for e in out["error_log"])
        assert called["get_subgraph"] is False

    def test_matches_agent_yaml_required_trust_level(self):
        assert VoiceComplianceGraphNode.required_trust_level == TrustLevel.INTERNAL


class TestGraphNodeBoundaryMapping:
    def test_extract_input_only_reads_validated_input(self):
        state = {
            "validated_input": json.dumps({"sessions": []}),
            "unrelated_secret_field": "must-not-appear",
        }
        extracted = _node().extract_input(state)

        assert isinstance(extracted, str)
        assert "must-not-appear" not in extracted

    def test_merge_output_maps_fields_explicitly_no_raw_passthrough(self):
        sub_result = {
            "sessions": [],
            "phrase_hits": [],
            "suitability_findings": [],
            "str_fields": [],
            "compliance_summary": [],
            "str_drafts": [],
            "escalation_level": "none",
            "status": "success",
            "internal_debug_trace": "should-not-be-copied",
        }
        merged = _node().merge_output({}, sub_result)

        assert "internal_debug_trace" not in merged
        assert merged["status"] == "success"
        assert set(merged) == {
            "sessions",
            "phrase_hits",
            "suitability_findings",
            "str_fields",
            "compliance_summary",
            "str_drafts",
            "escalation_level",
            "status",
        }


class TestGraphNodeDelegatesGatingToInnerSubgraph:
    def test_inner_entry_node_is_a_function_node_with_security_gates(self):
        # phrase_scan is the inner subgraph's entry node (START -> phrase_scan).
        assert issubclass(PhraseScanNode, FunctionNode)
        assert "required_trust_level" in PhraseScanNode.__dict__
