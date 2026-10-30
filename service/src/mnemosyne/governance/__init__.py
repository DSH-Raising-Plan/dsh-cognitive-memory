# -*- coding: utf-8 -*-
"""治理：Capability Gate / 审计（不可由 Agent 自授权）。"""

from mnemosyne.governance.capability_gate import (
    CAPABILITIES,
    CapabilityLockedError,
    check_capability,
    ensure_default_capabilities,
    list_capabilities,
    require_capability,
    set_capability_level,
)

__all__ = [
    "CAPABILITIES",
    "CapabilityLockedError",
    "check_capability",
    "ensure_default_capabilities",
    "list_capabilities",
    "require_capability",
    "set_capability_level",
]
