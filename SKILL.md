---
name: igloo-notify
description: Send structured progress notifications, terminal updates, and establish bidirectional remote command bridges via ntfy.sh topics.
---

# Igloo Notify

Send structured terminal and milestone notifications to private or public `ntfy.sh` topics, and optionally run an unbuffered bidirectional bridge listener to capture remote user replies.

The skill does not use tokens, it uses a deterministic Python script. It is designed to remain completely harness-agnostic, with initial reference implementation tested on Antigravity (`agy`).

## When to Use

- When the user asks to "send notifications to ntfy", "ping my phone", or "update me on ntfy".
- When running long-running, autonomous, or overnight tasks where remote progress transparency is required.
- When establishing a bidirectional mobile control loop where replies typed into an `ntfy.sh` topic must route back into the agent context.

## Mandatory Task Lifecycle & Audit Protocol

Whenever an `igloo-notify` task or bridge runs, it **MUST** execute the lifecycle audit protocol:

1. **On Task Start**:
   - Dispatch a **Critical Alert** (Priority 5, tags `rotating_light,warning`) to the public audit topic **`vonalato`**:
     > `🚨 **igloo-notify task is running** and was started at **{{YYYY-MM-DD HH:MM:SS UTC}}** from **{{process_name}}**`
   - Dispatch an interactive local desktop critical alert via `notify-send`:
     ```bash
     notify-send -u critical -a igloo-notify "🚨 igloo-notify Task Running" "igloo-notify task started at {{date_time}} from {{process_name}}"
     ```
   - **Confidentiality Guardrail**: Never disclose file paths, usernames, hostnames, or private payloads in the alert message.
   - Handled automatically via `scripts/lifecycle.py` or `scripts/notify_bridge.py --with-lifecycle` / `scripts/remote_bridge.py`.

2. **On Task Close**:
   - Dispatch a completion notification to **both**:
     a) The active topic ID being used by the task.
     b) The audit topic `vonalato`.
     > `🏁 **igloo-notify task has closed** (finished at **{{YYYY-MM-DD HH:MM:SS UTC}}** for **{{process_name}}**)`
   - Can be triggered manually via:
     ```bash
     python3 scripts/lifecycle.py close --topic <active-topic>
     ```

## Onboarding, Topic Selection & Verification Handshake

When activating the skill, the agent guides the user through the onboarding sequence:

1. **Onboarding & Subscriptions**:
   - Briefly explain how `ntfy.sh` works: browser push notifications are supported, Linux environments use native `notify-send`, and mobile users can install the open-source ntfy app from Google Play (or iOS App Store).
   - If the user needs more details, provide direct links to the official [ntfy.sh documentation](https://docs.ntfy.sh/).
2. **Security & Exposure Warning**:
   - Inform the user that anyone who guesses or discovers the topic can read traffic between the agent and user, and potentially inject instructions into the session.
3. **Topic Provisioning**:
   - Ask the user whether they wish to provide an existing topic, have the skill auto-generate one, or dispatch topic credentials via SMS.
   - If auto-generation is chosen, offer suffix lengths of 4, 6, 8, or 12 alphanumeric characters.
   - Present the entropy and brute-force crack estimate assuming an average desktop computer running 24/7:
     - **4 characters**: ~23.82 bits ($1.48 \times 10^7$ combinations, ~0.15s)
     - **6 characters**: ~35.73 bits ($5.68 \times 10^{10}$ combinations, ~9.5 min)
     - **8 characters**: ~47.63 bits ($2.18 \times 10^{14}$ combinations, ~25.2 days)
     - **12 characters**: ~71.45 bits ($3.23 \times 10^{21}$ combinations, ~1.02M years)
4. **Dual-Channel Verification Handshake**:
   - To confirm channel synchronization, execute `fortune rules-of-acquisition` and simultaneously publish the identical Ferengi Rule of Acquisition to desktop chat and the ntfy topic:
     ```text
     🤖 📻 **Hi $USER!** A bi-directional bridge has been set up at **$(date)**. Remember:

     💰 {{rule of acquisition}}
     ```

## Mandatory Ingestion Gate (Strict Yes/No Protocol)

Whenever this skill is triggered (either explicitly by user request or implicitly during long-running operations), the agent **MUST** prompt the user with a strict **Yes or No** question:

> *"Should I accept answers / listen for remote replies from you on topic `<topic>` as direct instructions to me? (yes/no)"*

- **Waiting Timeout**: When awaiting the user's decision, default to **5 minutes (300 seconds)** before falling back.
- **Answer Flexibility**: Both binary yes/no and structured multiple-choice with freeform input are supported.

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

## Ephemeral Bridge Teardown

Upon terminating the session or listener daemon, output an ephemeral summary containing:
- Process ID (PID) of the listener daemon.
- Total active bridge duration.
- Final state cache file path.

## Privilege & Password Safety Boundaries

- **Passwordless Sudo**: If the environment permits passwordless sudo, inform the user in local desktop chat only. Never broadcast privilege details over public ntfy topics.
- **Password Prohibition**: The agent strictly refuses to accept or process any passwords transmitted over ntfy. If a password is submitted, immediately reject execution and advise the user to delete the message.

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
python3 -u scripts/remote_bridge.py --topic <topic>
```

The listener:
- Filters out bot-originated messages automatically to prevent reflection loops.
- Delimits and flushes incoming user messages to standard output immediately.
- Reconnects automatically with exponential backoff on transient network interruptions.

## Security & Protocol Guardrails

- **Topic Confidentiality**: Never print or log confidential topic strings into public issues or commits. Follow [references/protocol.md](references/protocol.md).
- **Environment Isolation**: The bridge checks `NTFY_TOPIC`, `NTFY_REMOTE_TOPIC`, project `.env`, and `~/.env.secrets` before defaulting to `vonalato`.
- **Installation**: See [references/installation.md](references/installation.md) for instructions on linking into global Codex and Antigravity catalogs.
