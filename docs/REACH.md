# Reach definition (v1)

**Reach** is what a declared agent configuration can contact or launch — not
what it is proven to do at runtime.

```
reach = destination host set ∩ launcher identity ∩ capabilities ∩ pin
```

| Term | Meaning |
| --- | --- |
| Destination host set | URL hosts and declared destination hosts on a record |
| Launcher identity | Executable / transport (`npx`, `uvx`, `node`, URL transport, …) |
| Capabilities | Normalized capability labels (network, secrets, execute, tools, …) |
| Pin | Pin posture (`floating` / `pinned` / `digest` / …) |

## Change classes humans should see first

| Signal | Meaning |
| --- | --- |
| New destination | A host that was not in the sealed baseline |
| New executable | A launcher / argv digest change on an identity |
| New secrets | New `env_keys` or secrets-class capabilities |
| Inventory | Everything else (skills, commands, host settings) — collapsed on first run |

## What reach is not

- Not publisher verification (`publisher NOT VERIFIED` until separately attested)
- Not effective sandbox / approval enforcement
- Not a runtime egress firewall

Schema: [`../schemas/authority-lock.schema.json`](../schemas/authority-lock.schema.json)  
Contract detail: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md)
