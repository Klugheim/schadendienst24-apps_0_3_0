# SchadenDienst24 – Trocknungsbericht

Home-Assistant-App für PDF-Trocknungsberichte. Dieselbe App kann auf mehreren
Trocknungsanlagen installiert werden; Sensorzuordnungen bleiben je Anlage lokal.

## Am Windows-PC mit Visual Studio Code veröffentlichen

1. ZIP vollständig entpacken, z.B. nach `Dokumente/schadendienst24-apps`.
2. In VS Code **Datei → Ordner öffnen**: den Ordner wählen, in dem
   `repository.yaml` und der Unterordner `trocknungsbericht` direkt liegen.
3. **Quellcodeverwaltung → Repository initialisieren**. Falls Git fehlt:
   Git für Windows installieren und VS Code neu öffnen.
4. Dateien prüfen, Commit-Nachricht `Trocknungsbericht 0.3.0` eingeben und committen.
5. **Branch veröffentlichen / Publish to GitHub**, bei GitHub anmelden und
   ein **öffentliches** Repository `schadendienst24-apps` erstellen.
6. Die zurückgegebene GitHub-Repository-Adresse für Home Assistant verwenden.

Nur Programmcode und Dokumentation veröffentlichen. Keine PDFs, Tokens,
HA-Konfigurationsdateien, Kundendaten oder lokalen Optionen hinzufügen.

## Auf Trocknung 2 und 3 installieren

1. Einstellungen → Apps → App-Store → Menü → Repositorys.
2. GitHub-Repository-Adresse hinzufügen und App-Store neu laden.
3. Trocknungsbericht 0.3.0 unter SchadenDienst24 Apps installieren.
4. Vor dem Start die Konfiguration gemäß `trocknungsbericht/DOCS.md` setzen.
5. Beim Booten starten aktivieren und App starten.
6. Bericht testen, danach Automation und E-Mail-Versand einrichten.

Trocknung 1 bleibt vorerst bei ihrer funktionierenden lokalen Installation.
Die Repository-App hat eine andere Supervisor-ID und ersetzt diese nicht automatisch.

Updates: Quellcode ändern, Versionsnummer in `trocknungsbericht/config.yaml`
erhöhen, committen und pushen. Danach App-Store aktualisieren und Update installieren.

## Prüfung

Python-Syntax, Konfigurationsfelder, Zeitachsenintegration und die Tests unter
`tests` wurden geprüft. Der Container-Build und der erste Live-Test dieser
Repository-Version stehen noch aus. Die Ausgangsversion läuft auf Trocknung 1.

Tests: `python -m unittest discover -s tests -v`

Offizielle Anleitung: https://contributors.home-assistant.io/apps/guides/repository/
