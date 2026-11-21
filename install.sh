#!/usr/bin/env bash
# DNX Project Manager standalone installer - private unofficial hobby project.
set -Eeuo pipefail
CMD=${1:-help};ROOT=${DNX_PM_ROOT:-/opt/dnx-project-manager};PORT=${DNX_PM_PORT:-8094};ADMIN=${DNX_PM_ADMIN:-admin};HERE=$(cd "$(dirname "$0")"&&pwd);SERVICE=dnx-project-manager.service
notice(){ cat <<'EOF'
DNX Project Manager – privates, unabhängiges Hobbyprojekt.
Kein Projekt, Produkt oder offizielles Plugin von OpenWebRX/OpenWebRX+.
Keine Verbindung, Unterstützung oder Empfehlung durch deren Entwickler.
Nutzung vollständig auf eigene Gefahr; soweit gesetzlich zulässig keine Haftung.
Vorher Backups erstellen und zuerst im vertrauenswürdigen LAN testen.
EOF
}
root(){ [[ $EUID -eq 0 ]]||{ echo 'Bitte als root/sudo ausführen.';exit 1;};}
install_app(){
 root;command -v python3>/dev/null||{ echo 'Python 3 fehlt';exit 1;};mkdir -p "$ROOT"/{database,files,quarantine,previews,logs,backups};
 [[ -f $ROOT/app.py ]]&&cp -a "$ROOT/app.py" "$ROOT/backups/app.py.$(date +%F-%H%M%S)"||true
 cp "$HERE/app.py" "$ROOT/app.py";python3 -m venv "$ROOT/venv";"$ROOT/venv/bin/pip" install --upgrade pip;"$ROOT/venv/bin/pip" install 'Flask>=3,<4' 'waitress>=3,<4';
 [[ -f $ROOT/secret ]]||{ umask 077;python3 - <<PY >"$ROOT/secret"
import secrets;print(secrets.token_hex(48))
PY
 }
 chmod 600 "$ROOT/secret";cat >/etc/systemd/system/$SERVICE <<EOF
[Unit]
Description=DNX standalone private project manager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
Environment=DNX_PM_ROOT=$ROOT
Environment=DNX_PM_SECRET_FILE=$ROOT/secret
Environment=DNX_PM_SECRET=$(cat "$ROOT/secret")
ExecStart=$ROOT/venv/bin/waitress-serve --listen=0.0.0.0:$PORT --threads=8 app:app
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$ROOT

[Install]
WantedBy=multi-user.target
EOF
 systemctl daemon-reload
 if [[ $CMD == install && ! -f $ROOT/database/projects.sqlite3 ]];then echo "Jetzt wird der erste Administrator '$ADMIN' eingerichtet.";"$ROOT/venv/bin/python" "$ROOT/app.py" --init-admin "$ADMIN";fi
 systemctl enable --now "$SERVICE";sleep 3;systemctl --no-pager --full status "$SERVICE"||true;echo "Projekt-Manager: http://SERVER:$PORT/"
}
uninstall_app(){ root;systemctl disable --now "$SERVICE" 2>/dev/null||true;rm -f /etc/systemd/system/$SERVICE;systemctl daemon-reload;echo "Dienst entfernt. Daten bleiben in $ROOT";}
purge(){ root;uninstall_app;read -r -p "WIRKLICH alle Benutzer, Projekte und Dateien löschen? [ja/NEIN] " x;[[ $x == ja ]]||exit 1;rm -rf "$ROOT";echo 'Alle Daten gelöscht.';}
status(){ systemctl --no-pager --full status "$SERVICE"||true;ss -ltnp|grep -E ":$PORT\\b"||true;curl -sS -o /dev/null -w 'HTTP %{http_code}\n' "http://127.0.0.1:$PORT/"||true;du -sh "$ROOT" 2>/dev/null||true;}
backup(){ root;mkdir -p "$ROOT/backups";tar --exclude="$ROOT/backups" -czf "$ROOT/backups/dnx-project-manager-$(date +%F-%H%M%S).tar.gz" "$ROOT/database" "$ROOT/files" "$ROOT/quarantine" "$ROOT/app.py" 2>/dev/null;ls -lh "$ROOT/backups"|tail;}
notice
case "$CMD" in
 install|update)install_app;;uninstall)uninstall_app;;purge)purge;;status)status;;backup)backup;;help|*)cat <<EOF
Befehle:
  sudo ./install.sh install        Installation + erster Admin
  sudo ./install.sh update         Programm aktualisieren, Daten behalten
  ./install.sh status              Status prüfen
  sudo ./install.sh backup         Daten sichern
  sudo ./install.sh uninstall      Dienst entfernen, Daten behalten
  sudo ./install.sh purge          ALLES endgültig löschen

Optionen über Umgebungsvariablen:
  DNX_PM_ROOT=/opt/dnx-project-manager
  DNX_PM_PORT=8094
  DNX_PM_ADMIN=admin

Beispiel:
  DNX_PM_PORT=8094 DNX_PM_ADMIN=admin sudo -E ./install.sh install
EOF
esac
