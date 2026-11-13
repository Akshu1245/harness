# DSH front door: verified install (2026-11-13)

`scripts/install_dsh.sh` reproduces all of this on his laptop.

## Pins and digests (checked live against GitHub and npm)

| Component | Pin | Digest | Verified |
|---|---|---|---|
| DeepSeek Harness | deepseek-ai/deepseek-harness `39163dd30f703a79079e2d2446545cff3c453738` (master HEAD; the 0.2.2-rc.3 release commit) = npm `@deepseek-ai/dsh@0.2.2-rc.3` | npm integrity `sha512-S+4oUYVKWuc1SCMMp1mpUa2llxVy0o9gIgp7TDg/Ea7PuvXVkAfnykqSH1/oDXVB+y5VzEm0QIJulo1LIB3qRg==` | installed; `dsh web` booted, served auth-gated UI (401 without token, HTTP 200 `<title>DeepSeek Harness</title>` with) |
| Simular box plugin | simular-ai/box-plugin release `dsh-v0.2.1`, asset `dsh-box.tgz` | sha256 `bbc79df73954d08e86d9c17ace40a8c751e7f8c0fa0b2a55bbfb3a0830b05235` (from GitHub release API, matched locally) | installed into the dsh web profile; code vetted (171 lines, MIT, reads BOX_TOKEN from dsh's credential store, never logs it, talks only to box.simular.ai) |
| dsh-mobile | saya-ch/dsh-mobile `1616b43b61c7b22c170da1dc1eccdc4053c0cfbd` (main HEAD) = npm `dsh-mobile@0.8.8` | npm integrity `sha512-Eg0oseMuf7JOeRYD8+y1iROOq1+Yxo3yQ62AEbc9tj65iM5+6In4Gnz8lenchK0Uj638PHWcD6jE1HWUqA/SaQ==` | installed into the dsh web profile; its `mobile-access` plugin activates on boot (seen in dsh startup diagnostics) |

## Simular box

- Box `harness`, id `cb-61047bdfc05f`, created fresh 2026-11-13 on the account the
  vaulted "Simular box key" belongs to (that account had zero boxes before).
- Verified over MCP (`https://mcp.box.simular.ai/mcp/cb-61047bdfc05f`): box running,
  fresh Ubuntu 24.04 + XFCE desktop; `/home/user` holds only image dotfiles,
  `/workspace` empty.
- Account: free plan, 5,000 credits at creation. The box itself is free; only its
  model calls draw credits. No payment method involved anywhere in this setup.
- Caveat from Simular's docs: a box left asleep for 14 straight days is deleted
  with its files. Any wake resets the count.

## Caveats

- The sandbox has 2 GB RAM; a full source build of the deepseek-harness monorepo
  does not finish there (host-compiler gate). The npm install above is the exact
  pinned release (0.2.2-rc.3 is the release commit), so no source build is needed.
- `dsh-mobile setup` (LAN certificate + phone pairing) belongs on the computer the
  phone connects to; it exits with "no active private LAN address" where there is no
  LAN. Its CLI imports `@deepseek-ai/cordis`, an optional peer dependency pnpm does
  not install into the profile, so `dsh plugin exec` fails with ERR_MODULE_NOT_FOUND
  until you link the copy that ships with dsh - `scripts/install_dsh.sh` does this.
  Verified 2026-11-13: with the link, `setup` runs and stops at exactly the LAN check.
- `dsh web` gates the UI behind a per-boot token URL. Treat that URL like a
  password; never commit or share it.
