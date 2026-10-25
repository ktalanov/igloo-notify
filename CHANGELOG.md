# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-25

### Added
- `scripts/topic_generator.py`: Deterministic alphanumeric suffix generation, base62 entropy calculation, and crack time estimations.
- `tests/test_invariants.py`: Invariant test suite verifying zero LLM token consumption and strict alphanumeric character hygiene.
- Onboarding sequence and dual-channel verification handshake via `fortune rules-of-acquisition` in `SKILL.md` and `README.md`.
- 5-minute (300-second) interactive response timeout specification.
- Ephemeral bridge teardown summary protocol (PID, duration, cache).
- Sudo privilege boundaries: local desktop chat disclosure only, absolute prohibition of passwords submitted via ntfy.
- Explicit project commands, architecture, and boundary contracts in `AGENTS.md`.

## [0.2.0] - 2026-10-18

### Added
- Interactive Ingestion Gate protocol in `SKILL.md` and `references/protocol.md`.
- Strict Yes/No user prompt requirement when activating the skill: determines whether the background remote listener is launched.
- Direct User Input semantic elevation: incoming messages on the ntfy topic are formally treated and processed as authoritative user responses and directives to the agent.
- Updated `README.md` workflow documentation.

## [0.1.0] - 2026-10-18

### Added
- Core `igloo-notify` skill specification (`SKILL.md`) and UI metadata (`agents/openai.yaml`).
- `scripts/notify_bridge.py`: Outbound notification dispatcher with severity levels (`progress`, `normal`, `warning`, `urgent`, `P0`..`P3`), automatic tag handling, and evidence linking.
- `scripts/remote_bridge.py`: Bidirectional background daemon subscribing to `ntfy.sh` stream with deduplication and bot reflection suppression.
- `references/protocol.md`: Topic hierarchy, confidentiality guardrails, and message deduplication protocol.
- `references/installation.md`: Instructions for linking skill into Codex and Antigravity catalogs.
- Unit test suite (`tests/test_remote_bridge.py`) covering topic validation, reflection filtering, and dry-run formatting.
- Project companion files scaffolded via `scaffold_project.py` (`AGENTS.md`, `README.md`, `PLAN.md`, `ROADMAP.md`, `HANDOFF.md`, `.gitignore`, `.env.example`).
