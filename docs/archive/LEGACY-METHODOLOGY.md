# Legacy methodology (physically archived)

As of Guard **3.6** / **authdiff**, the product path is the deterministic CLI +
Action (`tools/`, `.github/actions/authdiff-gate`). Methodology trees live under:

**[`archive/methodology/`](../archive/methodology/)**

| Archived tree | Role |
| --- | --- |
| `archive/methodology/prompts/` | Optional deep-mode procedure; monoliths are not CI-gated |
| `archive/methodology/modules/` | Checklist content; prefer host adapters |
| `archive/methodology/control-packs/` | Policy templates; superseded by `.authdiff.yml` packs |
| `archive/methodology/kit/` | Former optional kit entry |

Keep `canonical/` schemas for build consistency; product runtime uses packaged
`aesa/data/*`. AgentSecBench intake / outreach remains frozen (`N = 0` external).

Prefer `authdiff doctor` / `authdiff open` / `authdiff scan` / the Authority Diff Action.
