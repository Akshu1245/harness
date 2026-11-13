#!/usr/bin/env bash
# Local-only developer installer. No cloud resource, model call, key prompt or public listener.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TARGET=${1:-"$HOME/.local/share/rashi-harness"}
if [ "$#" -gt 1 ] || [ "$TARGET" = --help ]; then
  printf '%s\n' 'Usage: bash scripts/install_dsh.sh [empty-install-directory]' 'Requires Python 3.10+, Node 22.18+ and npm. Installs locally; does not start DSH.'
  exit 0
fi
command -v python3
command -v node
command -v npm
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
node -e 'const [a,b]=process.versions.node.split(".").map(Number);if(a<22||(a===22&&b<18))throw Error("Node 22.18+ required")'
# Never overwrite an existing installation or the caller's own files.
if [ -e "$TARGET" ]; then
  printf '%s\n' 'Install directory already exists. Choose a new empty path; nothing was changed.' >&2
  exit 1
fi
mkdir -p -- "$TARGET"
TARGET=$(cd -- "$TARGET" && pwd)
printf '%s\n' 'rashi-local-installer-v1' > "$TARGET/.rashi-install"
python3 -m venv "$TARGET/venv"
"$TARGET/venv/bin/python" -m pip install "$ROOT"
mkdir -- "$TARGET/dsh-host"
printf '%s\n' '{"name":"rashi-local-host","version":"0.1.0","private":true,"type":"module"}' > "$TARGET/dsh-host/package.json"
(cd -- "$TARGET/dsh-host" && npm install --ignore-scripts --no-audit --no-fund --save-exact '@deepseek-ai/dsh@0.2.2-rc.3')
node "$ROOT/scripts/build_dsh_plugin.mjs" "$TARGET/dsh-host/rashi-plugin"
python3 - "$TARGET" "$(command -v node)" <<'LAUNCHERPY'
import json
from pathlib import Path
import shlex
import sys
root=Path(sys.argv[1])
(root/'overlay.yml').write_text('- id: workspace-controller\n  config:\n    documentsDirectory: '+json.dumps(str(root/'projects'))+
                               '\n- insert:\n    - id: rashi\n      name: '+json.dumps(str(root/'dsh-host/rashi-plugin/rashi-plugin.mjs'))+'\n')
quote=lambda p:shlex.quote(str(p))
launcher=('#!/usr/bin/env bash\nset -euo pipefail\n'
          'export RASHI_CMD='+quote(root/'venv/bin/rashi')+'\n'
          'export DSH_HOME='+quote(root/'profile')+'\n'
          'exec '+quote(sys.argv[2])+' '+quote(root/'dsh-host/node_modules/@deepseek-ai/dsh/lib/bin.js')+
          ' web --patch '+quote(root/'overlay.yml')+' "$@"\n')
(root/'start-rashi.sh').write_text(launcher)
(root/'start-rashi.sh').chmod(0o700)
LAUNCHERPY
"$TARGET/venv/bin/rashi" fleet
printf '%s\n' 'Local developer installation finished. No model or cloud call was made.'
printf 'Start the local DSH UI with: %q\n' "$TARGET/start-rashi.sh"
printf '%s\n' 'Model credentials are still yours to configure. Coding CLIs must be installed separately.' 'This is not a branded EXE/APK release; it is the pinned DSH UI with the Rashi tool.'
