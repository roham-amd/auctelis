# Migration: archived host stack

`watch` / `allow` / `hook` / `doctor` / `lock --home` are **not** the product.
They remain callable for one transition window and are on the kill list for 0.8.0.

**Use instead:**

```bash
auctelis check
auctelis lock --update
auctelis ci init --apply --owner @team
auctelis diff --base origin/main
```

There is no allow store, no heartbeat, and no tripwire enforcement on the
product path. Do not treat archived hooks as a sandbox.
