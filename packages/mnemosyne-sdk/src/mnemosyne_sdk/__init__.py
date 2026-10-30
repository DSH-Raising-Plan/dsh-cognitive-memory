"""Mnemosyne Python SDK — thin REST client (no duplicated business logic)."""

from .client import MnemosyneClient
from .paths import FOUNDATION_PATHS

__all__ = ["MnemosyneClient", "FOUNDATION_PATHS"]
