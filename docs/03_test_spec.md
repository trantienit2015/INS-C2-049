# INS-C2-049 — Test Specification

## Test layout

- `tests/unit/` — per-node + services + security (S-1 gate)
- `tests/integration/` — full graph `compile()` + `invoke()`
- `tests/proof_of_boundary/` — state safety + import isolation

## Test cases (TC)

| TC-ID | Test | File | Expected |
|---|---|---|---|
| TC-01 | State flat `AgentState` subtype; no Pydantic/credential fields | `proof_of_boundary/test_state_safety.py` | 0 violations |
| TC-02 | Empty / no-session input → `status=ERROR` | `unit/test_nodes.py` + integration | ERROR |
| TC-03 | No credentials in source/state | `proof_of_boundary/*` + S-5 CI | pass |
| TC-04 | Secrets via provider pattern (entry point), not `os.environ` | `src/api/server.py` (review) | pass |
| TC-05 | `emit_trace_event()` for side-effect nodes (phrase-scan / str-extract / report) | code review + S-4 | pass |
| TC-06 | Nodes stateless; data flows through state | node design | pass |
| TC-07 | No `_invoke_impl`; `execute(self, state)` only | node contract | pass |
| TC-08 | S-1 trust gate: `TranscriptParseNode.required_trust_level = INTERNAL` blocks ANONYMOUS | `unit/test_security.py` | ERROR via `__call__` |

## Node + services unit coverage

| Unit | Success | Error/edge |
|---|---|---|
| `TranscriptParseNode` | multi-channel normalize | empty / no sessions → ERROR |
| `PhraseScanNode` | **deterministic** 保険業法 hit | no sessions → ERROR |
| `SuitabilityCheckNode` | 適合性 violation | upstream-error passthrough |
| `STRFieldExtractNode` | 犯収法 fields per flagged session | LLM-failure degrades (logged) |
| `ComplianceSummaryGenerateNode` | per-agent counts | — |
| `STRDraftAssembleNode` | 犯収法 STR draft | — |
| `EscalationDecideNode` | file_str / review / none | — |
| `ReportFinalizeNode` | report + citations + disclaimer | — |
| services | parse / phrase scan / suitability / STR fields / escalation / report | — |

## Proof-of-Boundary (PB)

| PB-ID | Boundary | Test |
|---|---|---|
| PB-2/5 | State serialization safety | `test_state_safety.py` |
| PB-4 | Import isolation (no agenticstar/Level 0) | `test_import_isolation.py` |
| PB-1 | S-1 trust gate blocks under-trusted caller | `unit/test_security.py` |
| PB-6 | Full pipeline compile + invoke → initialize→pre→main→post→finalize | `integration::test_backbone_node_history` |

## Domain-specific assertions

- **Deterministic phrase scan**: a 断定的判断/不適切勧誘 phrase produces an auditable hit (no LLM); evidence
  cited in the report (`test_nodes.py`, `test_services.py`, integration).
- **STR generation + escalation**: a flagged session → 犯収法 STR draft + `file_str` escalation; a clean
  batch → `none` (`test_nodes.py`, integration).
- **Human-in-loop**: the report carries an advisory disclaimer (no auto-submission to JAFIO).

## Run

```bash
python -m pytest tests/ -v
ruff check src/ tests/
```
