# Roadmap — igloo-notify

## Intended outcome

Deliver a production-ready, standalone `igloo-notify` skill providing structured outbound mobile notifications and a bidirectional unbuffered command ingestion bridge via `ntfy.sh`.

## Major-release outcomes and dependencies

### Milestone 1 — 0.1.0 → 1.0.0 (MVP to Production Install)
- **0.1.0**: Core skill structure, `notify_bridge.py` outbound dispatcher, `remote_bridge.py` bidirectional streaming listener, and unit test suite.
- **0.2.0**: Full Igloo companion documentation (`AGENTS.md`, `README.md`, `CHANGELOG.md`, `HANDOFF.md`, `.gitignore`, `.env.example`), and evidence-backed plan authoring.
- **0.3.0**: Dynamic alphanumeric topic generator, entropy calculator, zero-token AST audit, fortune verification handshake, 5-minute prompt timeout, and sudo privilege guardrails.
- **1.0.0**: Global skill catalog installation across Codex and Antigravity, end-to-end integration validation.

### Milestone 2 — 1.0.0 → 2.0.0 (Automation & Persistent Daemons)
- **1.1.0**: Systemd user service unit generator (`igloo-create` timer integration) for running unattended background listeners across reboots.
- **1.2.0**: Secure authentication headers and self-hosted ntfy server adapter configuration.

## Decisions

- **2026-10-18**: Selected unbuffered stdlib HTTP streaming (`/json?since=latest`) for `remote_bridge.py` to prevent third-party Python dependency bloat while maintaining sub-second latency.
- **2026-10-18**: Enforced automatic `robot` tag insertion on outbound messages to eliminate infinite reflection loops when running concurrent bidirectional listeners on the same topic.
- **2026-10-18**: Prioritized CLI `--topic` and session override `vonalato` while preserving fallback to project `.env` `<PROJECT>-NOTIFY` and user secrets `~/.env.secrets`.
- **2026-10-25**: Enforced zero LLM token consumption invariant: the skill and its auxiliary scripts remain 100% deterministic local Python.
