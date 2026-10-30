---
name: mnemosyne-install
description: Safely install, verify, or upgrade a local Mnemosyne node for DSH or standalone use. Prefer dry-run plans; never overwrite data without backup; never expand remote bind or scopes without user consent.
---

# Mnemosyne Install Skill

## When to use

- User asks to install / upgrade / diagnose Mnemosyne or dsh-mnemosyne.
- Plugin added but memory service will not start.

## Hard rules

1. Run `mnemosyne plan-install --target dsh` first and show the plan.
2. Do **not** execute install until the user confirms the plan.
3. Always `mnemosyne backup --label pre-install` (or pre-upgrade) before mutating.
4. Do not change `host` away from `127.0.0.1` unless explicitly requested.
5. Component registration does **not** grant full scopes by default.
6. Never delete or replace an existing `data_dir` without explicit confirmation.

## Commands (machine-readable JSON)

```bash
# --data-dir / --token 是全局参数，写在子命令之前
python -m mnemosyne.cli --data-dir "$DATA" doctor
python -m mnemosyne.cli plan-install --target dsh
python -m mnemosyne.cli --data-dir "$DATA" backup --label pre-install
pip install -e ./service
python -m mnemosyne.cli --data-dir "$DATA" verify --target dsh
python -m mnemosyne.cli --data-dir "$DATA" status
```

## Verify checklist

- [ ] `health.ok == true`
- [ ] MCP tool list includes `memory_retrieve` and `memory_observe`
- [ ] Observation write succeeds
- [ ] Lock file only for this data_dir
- [ ] Token stored under `runtime/token` with restricted permissions when possible

## Rollback

```bash
python -m mnemosyne.cli restore <backup-bundle-or-db> --data-dir "$DATA" --force
```
