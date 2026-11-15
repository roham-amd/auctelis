"""auctelis — the authority lockfile and PR review for AI agent reach.

Public entry points:
- CLI: ``auctelis`` / ``python -m auctelis``
  (``check`` / ``lock`` / ``ci`` / ``gate`` / ``diff`` / ``why`` / ``demo``)
- Library: ``auctelis.check``, ``auctelis.authority_lock``,
  ``auctelis.gate``, ``auctelis.inventory.collector.collect_inventory``
- Archived (callable): ``watch`` / ``allow`` / ``hook`` / ``doctor``
- Hidden annotation: ``auctelis.security.scan``
"""

__version__ = "0.8.0"
__product_version__ = "0.8.0"
__product_name__ = "auctelis"
