#!/usr/bin/env bash
# Install the DSH front door: DeepSeek Harness (pinned), the Simular box plugin
# (sha256-verified), and dsh-mobile (pinned). Verified end to end 2026-11-13 in a
# clean Linux sandbox (Node 22, npm): dsh web booted and served its auth-gated UI.
# Zero cost: everything here is free; the Simular box is on the free plan.
set -euo pipefail

# Pin manifest (verified live against GitHub + npm, 2026-11-13; see docs/DSH_SETUP.md)
DSH_VERSION=0.2.2-rc.3        # == github.com/deepseek-ai/deepseek-harness @ 39163dd30f703a79079e2d2446545cff3c453738
DSH_MOBILE_VERSION=0.8.8      # == github.com/saya-ch/dsh-mobile @ 1616b43b61c7b22c170da1dc1eccdc4053c0cfbd
BOX_TGZ_URL=https://github.com/simular-ai/box-plugin/releases/download/dsh-v0.2.1/dsh-box.tgz
BOX_TGZ_SHA256=bbc79df73954d08e86d9c17ace40a8c751e7f8c0fa0b2a55bbfb3a0830b05235

mkdir -p dsh-host && cd dsh-host
npm init -y
npm install "@deepseek-ai/dsh@$DSH_VERSION" --no-audit --no-fund

curl -sL -o /tmp/dsh-box.tgz "$BOX_TGZ_URL"
echo "$BOX_TGZ_SHA256  /tmp/dsh-box.tgz" | sha256sum -c -

npx dsh plugin --profile web add /tmp/dsh-box.tgz
npx dsh plugin --profile web add "dsh-mobile@$DSH_MOBILE_VERSION"

# dsh-mobile's setup CLI imports @deepseek-ai/cordis, an OPTIONAL peer dependency that
# pnpm does not install into the profile; the dsh runtime provides it at boot but
# `dsh plugin exec` does not. Link the copy installed with dsh so `setup` resolves it.
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
ln -sfn "$(pwd)/node_modules/@deepseek-ai/cordis" "$DSH_HOME/profiles/web/node_modules/@deepseek-ai/cordis"

# Personal box key (cb_...) from https://box.simular.ai/access. The "harness" box
# (cb-61047bdfc05f, created 2026-11-13, free plan) already lives on that account.
# Never commit the key; it stays in this shell's environment only.
read -r -s -p "BOX_TOKEN (cb_...): " BOX_TOKEN; export BOX_TOKEN; echo

npx dsh web   # prints a tokenised http://127.0.0.1:3080 URL; open it in a browser

# Phone pairing, run on the computer the phone should reach (needs an active LAN;
# exits with "no active private LAN address" otherwise):
#   npx dsh plugin --profile web exec dsh-mobile setup
