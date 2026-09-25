# INS-C2-049 — Design Specification

## Position in AgentCore Architecture

- **Agent Class**: `INSC2049Graph` (alias `Graph`) in `src/graph/graph.py`
- **L1 Base**: `AgentBaseGraph` (L1 direct inheritance — no L2 base agent inheritance)
- **Category**: Cat 2 (multi-step domain workflow) · **Pattern**: DocGeneration (STR document generation)
- **Three-Layer Separation**:
  - **State** (`src/schemas/state.py`): `INSC2049State(AgentState)` — flat TypedDict, JSON-serializable
    primitives only; no Pydantic/dataclass/InvocationContext.
  - **Node**: each node inherits `FunctionNode`, overrides `execute(self, state) -> dict` only; partial
    update + `status = AgentStatus.<X>.value` string. No `_invoke_impl`, no `__call__` override.
  - **Graph**: `register_nodes()` calls `super().register_nodes()` then fills the 3 slots; `add_edges()`
    not overridden.

## Cat 2 Architecture (outer backbone + GraphNode + inner subgraph)

```
OUTER (AgentBaseGraph — src/graph/graph.py):
  initialize → pre_process(TranscriptParse) → main(VoiceComplianceGraphNode) → post_process(ReportFinalize) → finalize
                                                  │ get_subgraph().invoke(validated_input JSON, ctx)
                                                  ▼
INNER (BaseGraph — src/graph/domain_workflow_graph.py):
  START → phrase_scan → suitability_check → str_field_extract → compliance_summary_generate
        → str_draft_assemble → escalation_decide → END
```

## Node mapping (8 design steps → 5-node backbone)

| Slot | Node | Role | Output |
|---|---|---|---|
| pre_process | `TranscriptParseNode` | S-1 INTERNAL trust; normalize phone/LINE/in-person logs → unified sessions | `sessions` |
| main → inner a | `PhraseScanNode` | **deterministic** 保険業法 forbidden-phrase scan (no LLM, auditable); S-4 audit | `phrase_hits` |
| main → inner b | `SuitabilityCheckNode` | 適合性原則 check vs suitability matrix | `suitability_findings` |
| main → inner c | `STRFieldExtractNode` | 犯収法 STR fields (12 by default, configurable) per flagged session (deterministic + optional LLM) | `str_fields` |
| main → inner d | `ComplianceSummaryGenerateNode` | per-agent compliance summary | `compliance_summary` |
| main → inner e | `STRDraftAssembleNode` | populate 犯収法 STR template → submission-ready draft | `str_drafts` |
| main → inner f | `EscalationDecideNode` | none / review / file_str | `escalation_level` |
| post_process | `ReportFinalizeNode` | finalize report + evidence citations; S-4 audit | `final_report`, `formatted_output` |

Deterministic compute lives in `src/services/` (`transcripts.py`, `str_report.py`).

## Error propagation (inner linear topology)

Inner `BaseGraph` linear edges → every node runs; downstream nodes short-circuit (`status==ERROR`
passthrough) so a bad input propagates to the inner final status → outer GraphNode merges ERROR →
backbone `route()` → finalize. Verified: empty input ends `status=error`.

## Security (5-layer)

- **S-1**: `required_trust_level: INTERNAL` (agent.yaml) + `TranscriptParseNode.required_trust_level =
  TrustLevel.INTERNAL`; compliance/STR data is internal-only.
- **Auditable phrase scan**: `PhraseScan` is a deterministic string match (NO LLM, no hallucination) —
  the 金融庁 inspection requirement for forbidden-phrase detection. Evidence (phrase hits) is always cited.
- **S-3 secrets**: `bound_secrets()`/`secrets_factory()`/`provision_secrets()` at the entry point; never
  `os.environ`/`ctx.secrets.require()`.
- **S-4**: `emit_trace_event()` in PhraseScan, STRFieldExtract (LLM), ReportFinalize.
- **S-5**: no credentials in source/state; flat msgpack-safe state.

## LLM & scope

The STR-field-extraction LLM is optional (deterministic baseline is the source of truth; LLM failure
logged with `correlation_id`, degrades). IN — pre-existing text transcripts → 保険業法 scan + 適合性 check
+ 犯収法 STR generation + escalation + evidence summary. DEFERRED — audio-to-text transcription (consumes
the output of an external speech-to-text step), final human STR submission to JAFIO, real-time monitoring. KB + suitability
matrix + STR template injected via config.
