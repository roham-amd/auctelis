"""Deterministic inventory adapters.

Add a new surface by implementing a DiscoveryAdapter and registering it in
``registry.DISCOVERY_ADAPTERS``.
"""

from auctelis.inventory.adapters.registry import DISCOVERY_ADAPTERS

__all__ = ["DISCOVERY_ADAPTERS"]
