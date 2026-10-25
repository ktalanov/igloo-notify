# igloo-notify project rules

Purpose: Bidirectional ntfy.sh notification and command bridge skill

## Project-specific commands

- **Test**: `python3 -m unittest discover tests` (zero external dependencies, Python standard library)
- **Notify CLI**: `python3 scripts/notify_bridge.py --topic <topic> --message "<text>"`
- **Bridge Listener Daemon**: `python3 -u scripts/remote_bridge.py --topic <topic>`
- **Audit Lifecycle**: `python3 scripts/lifecycle.py {start|close} --topic <topic>`

## Architecture and boundaries

- **Core Components**:
  - `scripts/notify_bridge.py`: Outbound notification dispatcher with severity/tag normalization and loop suppression.
  - `scripts/remote_bridge.py`: Streaming ntfy bridge daemon with duplicate suppression and input elevation.
  - `scripts/lifecycle.py`: Task audit lifecycle manager dispatching critical start/close alerts to `vonalato` and local desktop notifications via `notify-send`.
- **Data Boundaries**:
  - Audit Topic: `vonalato` (strict audit logging, never exposes hostnames, usernames, or paths).
  - Target Topic: Configured via CLI override `--topic`, environment variables (`NTFY_TOPIC`, `NTFY_REMOTE_TOPIC`), `.env`, or `~/.env.secrets`.
  - State Cache: Local persistent deduplication log at `~/.cache/igloo-notify/seen_<topic>.txt`.
- **Security Boundaries**:
  - Mandatory Ingestion Gate: Requires explicit Yes/No user approval before spawning listener daemon or elevating remote commands.
  - Zero-Token Guarantee: Deterministic Python runtime using standard library only; zero LLM token consumption.
  - Credential Protection: Topics must not be committed to git. Passwords submitted over ntfy are strictly prohibited and immediately refused/deleted.

## Completion evidence

- All unit tests passing via `python3 -m unittest discover tests`.
- Zero-token execution verified across scripts.
- Conventional Commits 1.0.0 for all git history.
- SemVer 2.0.0 compliance maintained across `PLAN.md`, `ROADMAP.md`, `CHANGELOG.md`, `README.md`, and `SKILL.md`.
