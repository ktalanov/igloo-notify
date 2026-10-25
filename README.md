# igloo-notify

## Purpose

`igloo-notify` provides bidirectional mobile/remote notifications and remote command input via `ntfy.sh` for Codex and Antigravity agents.

The skill does not use tokens, it uses a deterministic Python script. It is designed to be completely harness-agnostic, with initial verification executed on Google Antigravity (`agy`).

## Current State

- **Version**: 0.3.0
- **Runtime**: Python 3.10+ (Standard Library only — zero external pip dependencies, zero LLM token consumption)
- **Supported Harnesses**: Antigravity (`agy`), Codex (`codex`), and raw terminal CLI.

## Workflow & Interactive Ingestion Gate

When triggered, the agent asks a strict **Yes or No** question:
> *"Should I accept answers / listen for remote replies from you on topic `<topic>` as direct instructions to me? (yes/no)"*

- **If Yes**: The agent launches the background bridge daemon (`scripts/remote_bridge.py`), elevating any incoming user responses on the topic to direct instructions/responses to the agent.
- **If No**: The agent operates in outbound-only mode (`scripts/notify_bridge.py`) without ingesting responses.

### Interactive Timing & Ephemeral Summaries

- **Default Ingestion Timeout**: When awaiting interactive user response or gate confirmation, the listener defaults to **5 minutes (300 seconds)** before falling back or timing out, supporting both freeform and multiple-choice answers.
- **Ephemeral Bridge Summary**: Upon bridge teardown, the system outputs an ephemeral summary detailing the active duration, termination timestamp, and process ID (PID) of the bridge listener daemon.

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
python3 -u scripts/remote_bridge.py --topic <topic>
```

### Dynamic Topic Generation & Entropy
The skill can deterministically generate cryptographically random alphanumeric topics with guaranteed zero stray delimiters:
```bash
python3 -c "from scripts.topic_generator import generate_topic; print(generate_topic('igloo-notify', length=8))"
```

Entropy characteristics across candidate suffix lengths:
- **4 chars**: ~23.82 bits (approx. $1.48 \times 10^7$ combinations)
- **6 chars**: ~35.73 bits (approx. $5.68 \times 10^{10}$ combinations)
- **8 chars**: ~47.63 bits (approx. $2.18 \times 10^{14}$ combinations)
- **12 chars**: ~71.45 bits (approx. $3.23 \times 10^{21}$ combinations)

### Verification Handshake
To verify channel synchronization between chat and mobile, the bridge executes a dual-channel handshake using `fortune rules-of-acquisition`, publishing the exact Ferengi rule of acquisition simultaneously to desktop chat and the ntfy topic.

## Privilege & Credential Guardrails

- **Sudo Status**: If passwordless sudo is configured on the host, the agent informs the user in **desktop chat only**—never over public or unauthenticated ntfy topics.
- **Password Prohibition**: The agent strictly **refuses** to accept or utilize user passwords transmitted over ntfy. If a password is sent accidentally or intentionally, the agent refuses execution and instructs immediate deletion.

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
- [AGENTS.md](AGENTS.md) — Working agreements, commands, and security constraints
- [PLAN.md](PLAN.md) — SemVer planning targets and implementation evidence
- [ROADMAP.md](ROADMAP.md) — Major release milestones
- [CHANGELOG.md](CHANGELOG.md) — Version history following Keep a Changelog
- [references/protocol.md](references/protocol.md) — Topic resolution and reflection loop prevention rules
- [references/installation.md](references/installation.md) — Installation and catalog linking guide
