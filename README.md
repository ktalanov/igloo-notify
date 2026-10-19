# igloo-notify

## Purpose

`igloo-notify` provides bidirectional mobile/remote notifications and remote command input via `ntfy.sh` for Codex and Antigravity agents.

## Current State

- **Version**: 0.1.0 MVP
- **Runtime**: Python 3.10+ (Standard Library only — zero external pip dependencies)
- **Supported Harnesses**: Antigravity (`agy`), Codex (`codex`), and raw terminal CLI.

## Setup and Use

### Sending Notifications
```bash
python3 scripts/notify_bridge.py \
  --message "Build completed successfully." \
  --title "[Aggs] Build Status" \
  --severity normal \
  --tags "white_check_mark,gear"
```

### Running the Bidirectional Listener
```bash
python3 -u scripts/remote_bridge.py --topic vonalato
```

## Verification

Run the test suite:
```bash
python3 -m unittest discover -s tests -v
```

Validate skill specification:
```bash
python3 /home/lenin/.gemini/config/skills/skill-creator/scripts/quick_validate.py .
```

## Project Documents

- [SKILL.md](SKILL.md) — Authoritative skill instructions for AI agents
- [AGENTS.md](AGENTS.md) — Working agreements and security constraints
- [PLAN.md](PLAN.md) — SemVer planning targets and implementation evidence
- [ROADMAP.md](ROADMAP.md) — Major release milestones
- [CHANGELOG.md](CHANGELOG.md) — Version history following Keep a Changelog
- [references/protocol.md](references/protocol.md) — Topic resolution and reflection loop prevention rules
- [references/installation.md](references/installation.md) — Installation and catalog linking guide
