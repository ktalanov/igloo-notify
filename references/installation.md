# Igloo Notify Installation Guide

This skill can be installed as a discoverable standalone skill across Codex and Antigravity environments.

## Automated Linking / Installation

To install `igloo-notify` into user skill catalogs:

### For Antigravity
```bash
mkdir -p ~/.gemini/config/skills
ln -sfn /home/lenin/github/plugins/skills/igloo-notify ~/.gemini/config/skills/igloo-notify
```

### For Codex
```bash
mkdir -p ~/.codex/skills
ln -sfn /home/lenin/github/plugins/skills/igloo-notify ~/.codex/skills/igloo-notify
```

## Verification

After installation, verify discovery:

1. **Schema Check**:
   ```bash
   python3 /home/lenin/.gemini/config/skills/skill-creator/scripts/quick_validate.py /home/lenin/github/plugins/skills/igloo-notify
   ```
2. **Smoke Test**:
   ```bash
   python3 /home/lenin/github/plugins/skills/igloo-notify/scripts/notify_bridge.py -m "Skill install test" --dry-run
   ```
