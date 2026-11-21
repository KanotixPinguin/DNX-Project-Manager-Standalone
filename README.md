# DNX Project Manager – eigenständiger Prototyp

> Rein privates, unabhängiges Hobbyprojekt. Kein Projekt, Produkt oder offizielles Plugin von OpenWebRX/OpenWebRX+. Keine Verbindung, Unterstützung, Prüfung oder Empfehlung durch deren Entwickler. Nutzung auf eigene Gefahr; soweit gesetzlich zulässig keine Haftung. Vorher Backups erstellen und zunächst ausschließlich im vertrauenswürdigen LAN testen.

## Architektur

Dieser Projekt-Manager ist vollständig eigenständig:

- keine OpenWebRX-Benutzer
- keine OpenWebRX-Sitzungen
- keine Änderungen an OpenWebRX
- eigener Dienst auf Port 8094
- eigene SQLite-Datenbank
- eigene Registrierung, Anmeldung und Rollen
- eigener Speicher unter `/opt/dnx-project-manager`

## Rollen

### Anonym

- veröffentlichte Projekte ansehen
- suchen
- herunterladen
- registrieren

### Benutzer

Nach Adminfreigabe:

- anmelden
- eigene Projekte hochladen
- eigene Projekte sehen und löschen
- Uploads landen zunächst in Quarantäne

### Vertrauenswürdiger Benutzer

- Uploads werden direkt veröffentlicht, sofern ClamAV keinen Fund meldet

### Administrator

- neue Nutzer freigeben oder sperren
- Rollen `user`, `trusted` und `admin` vergeben
- Uploads freigeben oder ablehnen
- alle Projekte moderieren

## Sicherheit

- Passwort-Hash mit Werkzeugs scrypt-Implementierung
- zufällige serverseitige Sitzungen
- HttpOnly- und SameSite-Sitzungscookies
- CSRF-Token für Upload, Löschen und Administration
- Sperre für 15 Minuten nach fünf fehlerhaften Anmeldungen
- Streaming-Upload in 1-MB-Blöcken
- 500 MB je Datei
- 10 GB je Nutzer
- SHA-256
- sichere zufällige Projekt-IDs
- optionaler ClamAV-Scan
- Downloads als Anlage
- keine automatische Ausführung hochgeladener Dateien

## Installation

```bash
chmod +x install.sh
sudo ./install.sh install
```

Während der Installation wird das Passwort für den ersten Administrator abgefragt:

```text
Benutzername: admin
```

Das Passwort muss mindestens acht Zeichen haben.

Anderer Adminname:

```bash
DNX_PM_ADMIN=DNX sudo -E ./install.sh install
```

Anderer Port oder Speicherpfad:

```bash
DNX_PM_PORT=8094 \
DNX_PM_ROOT=/opt/dnx-project-manager \
sudo -E ./install.sh install
```

Danach öffnen:

```text
http://SERVER:8094/
```

## Status

```bash
./install.sh status
```

## Update

```bash
sudo ./install.sh update
```

Datenbank, Benutzer und Dateien bleiben erhalten.

## Backup

```bash
sudo ./install.sh backup
```

Backups liegen in:

```text
/opt/dnx-project-manager/backups
```

## Entfernen

Dienst entfernen, Daten behalten:

```bash
sudo ./install.sh uninstall
```

Alles endgültig löschen:

```bash
sudo ./install.sh purge
```

## Verzeichnisse

```text
/opt/dnx-project-manager/
├── app.py
├── secret
├── venv/
├── database/projects.sqlite3
├── files/
├── quarantine/
├── previews/
├── logs/
└── backups/
```

## Öffentlicher Betrieb

Vor einer Veröffentlichung im Internet unbedingt:

- HTTPS-Reverse-Proxy einsetzen
- `DNX_PM_SECURE_COOKIE=1` setzen
- Upload- und Login-Ratenlimit im Proxy konfigurieren
- regelmäßige Backups einrichten
- ClamAV installieren und Signaturen aktualisieren
- Firewall konfigurieren
- Dienst nicht zusätzlich ungeschützt auf mehreren Ports veröffentlichen

Beispiel ClamAV:

```bash
apt update
apt install clamav
freshclam
```

## Einschränkungen des Prototyps

- noch keine E-Mail-Bestätigung
- noch keine TOTP-Zwei-Faktor-Anmeldung
- noch keine Vorschaugenerierung
- noch keine Archiv-Inhaltsanalyse
- noch keine fortsetzbaren Uploads
- noch keine automatische Löschfrist
- noch keine mehrteilige Versionshistorie pro Projekt

Archive werden bewusst nicht automatisch entpackt. Das verhindert Pfadtraversal beim Prototyp.

## Unabhängigkeit

OpenWebRX/OpenWebRX+ wird nur als früherer Kontext erwähnt. Der Dienst ist kein Bestandteil davon und benötigt OpenWebRX weder zur Installation noch zur Laufzeit.
