# auctelis_research (maintainer-only)

Passive rule pack, scan/annotate, corpus, graph, and related helpers.

**Not shipped in the product wheel.** Importable from a source checkout /
editable install so `auctelis-dev scan` keeps working for maintainers and CI
that runs from this repository.

Product path (`auctelis check` / `lock` / `gate` / `diff`) must not import this
package at module load time.
