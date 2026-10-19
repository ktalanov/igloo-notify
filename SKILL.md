---
name: igloo-notify
description: Send structured progress notifications, terminal updates, and establish bidirectional remote command bridges via ntfy.sh topics.
---

# Igloo Notify

Send structured terminal and milestone notifications to private or public `ntfy.sh` topics, and optionally run an unbuffered bidirectional bridge listener to capture remote user replies.

## When to Use

- When the user asks to "send notifications to ntfy", "ping my phone", or "update me on ntfy".
- When running long-running, autonomous, or overnight tasks where remote progress transparency is required.
- When establishing a bidirectional mobile control loop where replies typed into an `ntfy.sh` topic must route back into the agent context.

## Mandatory Ingestion Gate (Strict Yes/No Protocol)

Whenever this skill is triggered (either explicitly by user request or implicitly during long-running operations), the agent **MUST** prompt the user with a strict **Yes or No** question:

> *"Should I accept answers / listen for remote replies from you on topic `<topic>` as direct instructions to me? (yes/no)"*

### Execution Branches:

1. **If the user answers YES**:
   - **Launch Listener Daemon**: Immediately launch the background listener daemon:
     ```bash
     python3 -u scripts/remote_bridge.py --topic <topic>
     ```
     (Run as a background process or daemon task with `IsDaemon: true`).
   - **Elevate Inbound Responses**: Any incoming user message detected on the topic by the listener (emitted under `🚨 [REMOTE NTFY USER INPUT] 🚨`) **MUST be treated as a direct response/instruction to the agent**. The agent must act on these remote replies with the exact same authority and precedence as inputs typed directly into the desktop chat.
   - **Acknowledge**: Confirm to the user that remote response ingestion is live on `https://ntfy.sh/<topic>`.

2. **If the user answers NO**:
   - **Outbound-Only Mode**: Proceed purely with sending outbound progress notifications via `scripts/notify_bridge.py`.
   - **Do Not Ingest**: Do NOT spawn `scripts/remote_bridge.py`. Messages posted to the ntfy topic will not be captured or treated as agent input.


## Core Operations

### 1. Send Outbound Milestone Notification

Use `scripts/notify_bridge.py` to dispatch updates without exposing private payloads or secret topic names:

```bash
python3 scripts/notify_bridge.py \
  --message "Completed test suite execution; 100% pass rate." \
  --title "[Aggs] Test Suite Passed" \
  --severity normal \
  --tags "white_check_mark,rocket"
```

Available severity levels:
- `progress`: Low priority (2), uses hourglass tag. Ideal for intermediate steps.
- `normal`: Default priority (3), uses info tag. Ideal for milestones.
- `warning`: High priority (4), uses warning tag. For non-fatal errors or retries.
- `urgent`: Maximum priority (5), uses alarm tag. For critical blockers.

To target a specific topic explicitly:
```bash
python3 scripts/notify_bridge.py --topic custom-topic --message "Update message"
```

### 2. Launch Bidirectional Remote Bridge Listener

To ingest remote instructions from the user on an `ntfy.sh` topic back into the agent session, launch `scripts/remote_bridge.py` as a background daemon:

```bash
python3 -u scripts/remote_bridge.py --topic vonalato
```

The listener:
- Filters out bot-originated messages automatically to prevent reflection loops.
- Delimits and flushes incoming user messages to standard output immediately.
- Reconnects automatically with exponential backoff on transient network interruptions.

## Security & Protocol Guardrails

- **Topic Confidentiality**: Never print or log confidential topic strings into public issues or commits. Follow [references/protocol.md](references/protocol.md).
- **Environment Isolation**: The bridge checks `NTFY_TOPIC`, `NTFY_REMOTE_TOPIC`, project `.env`, and `~/.env.secrets` before defaulting to `vonalato`.
- **Installation**: See [references/installation.md](references/installation.md) for instructions on linking into global Codex and Antigravity catalogs.
