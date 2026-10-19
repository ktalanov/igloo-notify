# igloo-notify plan

## Intended outcome

Deliver a production-ready, standalone `igloo-notify` skill providing structured outbound mobile notifications and a bidirectional unbuffered command ingestion bridge via `ntfy.sh`.

## 0.1.0 — MVP Core Implementation & Protocol

### 0.1.1 — Skill Scaffolding & Progressive Disclosure
- [x] Task: Initialize skill directory structure with frontmatter and progressive disclosure references.
  - Files: `SKILL.md`, `agents/openai.yaml`, `references/protocol.md`, `references/installation.md`
  - Command: `python3 /home/lenin/.gemini/config/skills/skill-creator/scripts/quick_validate.py /home/lenin/github/plugins/skills/igloo-notify`
  - Evidence: Validator returned `Skill is valid!` with 0 errors.

### 0.1.2 — Outbound Notification Dispatcher
- [x] Task: Implement deterministic notification dispatcher CLI with priority normalization and reflection loop suppression.
  - Files: `scripts/notify_bridge.py`
  - Command: `python3 scripts/notify_bridge.py -m "Skill implementation in progress" -t "[Aggs] igloo-notify Live Dispatch" --topic vonalato --json`
  - Evidence: Live HTTP delivery confirmed (`status: delivered`, `id: zc4ehtqC5aLS`).

### 0.1.3 — Bidirectional Remote Bridge Listener
- [x] Task: Implement unbuffered streaming listener daemon with automatic bot message filtering and deduplication.
  - Files: `scripts/remote_bridge.py`
  - Command: `python3 -u scripts/remote_bridge.py --help`
  - Evidence: Daemon supports CLI `--topic`, environment overrides, and state deduplication.

### 0.1.4 — Test Suite Verification
- [x] Task: Verify topic resolution, bot suppression, and dry-run formatting with unit tests.
  - Files: `tests/test_remote_bridge.py`
  - Command: `python3 -m unittest discover -s tests -v`
  - Evidence: 7 tests passed (0.001s).

## 0.2.0 — Companion Scaffolding & Hardening

### 0.2.1 — Igloo Companion Scaffolding
- [x] Task: Scaffold standard companion files (`AGENTS.md`, `README.md`, `CHANGELOG.md`, `HANDOFF.md`, `.gitignore`, `.env.example`).
  - Command: `python3 /home/lenin/github/plugins/igloo-v2/scripts/scaffold_project.py --apply ...`
  - Evidence: All companion files created and verified without collision.

### 0.2.2 — Plan & Roadmap Normalization
- [x] Task: Populate evidence-based `PLAN.md` and `ROADMAP.md` adhering to Igloo SemVer rules.
  - Files: `PLAN.md`, `ROADMAP.md`
  - Evidence: Slices categorized from 0.1.0 MVP to 1.0.0 Global Installation.

## 1.0.0 — Global Installation & Integration

### 1.0.1 — Catalog Installation
- [x] Task: Install `igloo-notify` into user skill catalogs (`~/.gemini/config/skills/igloo-notify` and `~/.codex/skills/igloo-notify`).
  - Command: Symlinked `/home/lenin/github/plugins/skills/igloo-notify` to `~/.gemini/config/skills/igloo-notify` and `~/.codex/skills/igloo-notify`.
  - Evidence: Both paths validated with `Skill is valid!` via `quick_validate.py`.

### 1.0.2 — Live Verification Smoke Test
- [x] Task: Execute end-to-end smoke test from installed catalog location.
  - Command: `python3 ~/.gemini/config/skills/igloo-notify/scripts/notify_bridge.py -m "Skill igloo-notify successfully installed into ~/.gemini/config/skills and ~/.codex/skills. Ready for global use." -t "[Aggs] Skill Installed & Verified" --topic vonalato -s "normal" --json`
  - Evidence: Event `qGzpG88MmvHi` delivered to `ntfy.sh/vonalato`.

## Deferred Items Ledger

| ID | Type | Priority | Description | Containment / Reason | Target |
|---|---|---|---|---|---|
| DEF-01 | Feature | P3 | Encryption / Authentication support for self-hosted ntfy instances | Unauthenticated ntfy.sh is the user's explicit deployment target | Post-1.0.0 |
| DEF-02 | Feature | P3 | Systemd user unit generation for persistent headless bridge daemon | Currently run via background task / CLI daemon per session | 1.1.0 |
