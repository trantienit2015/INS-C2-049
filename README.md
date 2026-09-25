# INS-C2-049 — Insurance Agency Multi-Channel Voice Compliance Summary & STR Generation Agent

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific use case)
> **Industry**: INS

## Overview

Reviews a batch of insurance-agency sales conversation transcripts for compliance issues and
drafts suspicious-transaction report (STR) forms for the conversations that need one. The input
is a JSON object with a `sessions` list (or the list itself); each session has `text` and optional
`session_id`, `channel` (phone, line or in_person) and `agent_id`. Input that is empty, not valid
JSON or has no session with text is rejected. The entry nodes require an internal-level caller.
The agent works on existing text transcripts; it does not transcribe audio.

Each session is scanned by plain case-insensitive substring match against a forbidden-phrase list
(for example guaranteed-profit or pressure-selling wording) and checked against a suitability
matrix: when a session mentions a product's trigger phrase but omits a required phrase (such as
an explanation of risk), it is recorded as a suitability violation. Both rulesets come from
`config/config.yaml`; the bundled entries are illustrative samples, not a complete ruleset. Every
session with a hit or a violation gets an STR draft whose fields (12 by default) are filled from
the session metadata and the detected issues; fields the agent cannot know, such as the customer
reference or product, stay empty. The report contains a per-agent summary, the STR drafts, an
escalation level (`file_str` when any draft exists, `review` otherwise if anything was found,
`none` for a clean batch), the evidence and a note that human review is required before any
report is submitted.

A language model is optional and only used to try to enrich the STR fields; if the call fails the
deterministic fields are kept and a warning is logged. The bundled HTTP entry point supplies an
Anthropic client only when an `ANTHROPIC_API_KEY` secret is available.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
