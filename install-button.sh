#!/usr/bin/env bash
set -Eeuo pipefail
CMD=${1:-install}
TYP=${TYP:-auto}
CONTAINER=${CONTAINER:-owrx-8013}
PLUGINS=${PLUGINS:-}
NORESTART=${NORESTART:-0}
PM_URL=${PM_URL:-}
HERE=$(cd "$(dirname "$0")" && pwd)
BACK="/opt/dnx-pm-button-backups"

resolve_paths() {
  if [[ "$TYP" == "normal" ]]; then
    SRC="$PLUGINS"
    if [[ -z "$SRC" ]]; then
      for cand in /usr/lib/python3/dist-packages/htdocs/plugins /opt/openwebrx/htdocs/plugins /srv/openwebrx/htdocs/plugins; do
        if [[ -d "$cand/receiver" ]]; then SRC="$cand"; break; fi
      done
    fi
  else
    if [[ "$TYP" == "auto" && -n "$PLUGINS" && -d "$PLUGINS/receiver" ]]; then
      SRC="$PLUGINS"
    else
      command -v docker >/dev/null 2>&1 || { echo "Docker nicht gefunden. Nutze TYP=normal PLUGINS=/pfad/zu/plugins."; exit 1; }
      SRC=$(docker inspect "$CONTAINER" --format '{{range .Mounts}}{{if eq .Destination "/usr/lib/python3/dist-packages/htdocs/plugins"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)
    fi
  fi
  [[ -n "${SRC:-}" && -d "$SRC/receiver" ]] || { echo "Plugin-Pfad nicht gefunden ($SRC)."; exit 1; }
  INIT="$SRC/receiver/init.js"
  DEST="$SRC/receiver/dnx_pm_button"
}

remove_loader() {
  python3 - "$INIT" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
t = p.read_text(encoding='utf-8')
a = '/* DNX_PM_BUTTON_LOADER_START */'
b = '/* DNX_PM_BUTTON_LOADER_END */'
if a in t and b in t:
    x, y = t.split(a, 1)
    _, z = y.split(b, 1)
    p.write_text(x.rstrip() + '\n' + z.lstrip(), encoding='utf-8')
PY
}

install_btn() {
  [[ $EUID -eq 0 ]] || { echo "Bitte als root/sudo ausführen."; exit 1; }
  resolve_paths
  S=$(date +%F-%H%M%S)
  mkdir -p "$BACK/$S" "$DEST"
  cp -a "$INIT" "$BACK/$S/init.js"
  cp "$HERE/files/dnx_project_manager_button.js" "$DEST/dnx_project_manager_button.js"
  remove_loader
  URL_LINE=""
  [[ -n "$PM_URL" ]] && URL_LINE="window.DNX_PM_URL=$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$PM_URL");"
  cat >> "$INIT" <<JS

/* DNX_PM_BUTTON_LOADER_START */
(function(){if(window.__dnxLoad_pm_btn)return;window.__dnxLoad_pm_btn=true;$URL_LINE var s=document.createElement('script');s.src='/static/plugins/receiver/dnx_pm_button/dnx_project_manager_button.js';document.head.appendChild(s);})();
/* DNX_PM_BUTTON_LOADER_END */
JS
  command -v node >/dev/null 2>&1 && node --check "$INIT"
  if [[ "$NORESTART" != "1" ]] && command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    docker restart "$CONTAINER"
  fi
  echo "DNX Project Manager Button installiert."
}

uninstall_btn() {
  [[ $EUID -eq 0 ]] || { echo "Bitte als root/sudo ausführen."; exit 1; }
  resolve_paths; remove_loader; rm -rf "$DEST"
  echo "DNX Project Manager Button entfernt."
}

case "$CMD" in
  install|update) install_btn ;;
  uninstall) uninstall_btn ;;
  *) echo "Aufruf: $0 [install|update|uninstall]" ;;
esac
