# Einrichtung je Trocknungsanlage

## Sensorzuordnung

Die Plätze TH1 A bis TH8 A sind feste interne Zuordnungsplätze. Es werden keine
zusätzlichen Home-Assistant-Sensorentitäten erzeugt. Unter Konfiguration die
Original-Entitäts-IDs für Feuchte und Temperatur eintragen. Die voreingestellten
Namen sind Beispiele und müssen zu den Entitäten der jeweiligen Anlage passen.

- `th1_a_feuchte` bis `th8_a_feuchte`: Feuchtesensoren.
- `th1_a_temperatur` bis `th8_a_temperatur`: Temperatursensoren.
- `kanal1_schalter` bis `kanal3_schalter`: tatsächliche Schalter.
- `trocknungsbeginn_entitaet`: Helfer mit Datum UND Uhrzeit des Beginns;
  voreingestellt `input_datetime.kwh_reset`. Nur verwenden, wenn dieser Reset
  tatsächlich dem Beginn der jeweiligen Trocknung entspricht.

Nach einer Änderung der App-Konfiguration die App neu starten.
Jede Zuordnungsliste muss eindeutige Entitäts-IDs enthalten.

## Bestehende Helfer

Erforderlich: `input_text.name_der_trocknung` und der konfigurierte Datumshelfer.

Raumnamen: `input_text.th1` bis `input_text.th8`.
Gerätenamen: `input_text.kanal1` bis `input_text.kanal3`.
Fehlende Namenshelfer deaktivieren den betreffenden Platz automatisch.
Vorhandene, unbenutzte Plätze mit `nicht aktiv` beschriften.
Die vorbelegten Sensor-IDs unbenutzter Plätze können stehen bleiben;
sie werden bei deaktivierten Plätzen nicht abgefragt.

Raumbezeichnungen bleiben während der Trocknung frei änderbar. Neue PDFs
verwenden den aktuellen Namen für die ganze Messreihe. Bereits erzeugte PDFs
bleiben erhalten. Technische Sensorzuordnungen während einer laufenden Trocknung
beibehalten: Die App verwendet die Historie der zugeordneten Originalentität.

## Test und Ausgabe

Netzwerk: Port 8099/tcp bei Bedarf auf 8099 setzen, speichern, App neu starten.
Vom Terminal der Anlage mit ihrer tatsächlichen IP aufrufen:

```sh
curl -sS -X POST http://ANLAGEN-IP:8099/bericht
```

Erfolg: `{"status": "erstellt"}`.
Intern ist die API ebenfalls über den Supervisor-Hostnamen der App erreichbar;
dieser ändert sich gegenüber der lokalen Installation und ist je Repository zu prüfen.

PDF: `/local/trocknungsberichte/aktueller_bericht.pdf` an der Browseradresse
der jeweiligen Anlage. Im HA-Konfigurationsordner liegt sie unter
`www/trocknungsberichte/aktueller_bericht.pdf`. Die App selbst sieht diesen Ordner
als `/homeassistant/www/trocknungsberichte`.
Wird `www` erstmals angelegt, kann ein HA-Core-Neustart nötig sein.

Unverfügbare Geräteintervalle werden nicht als Ein oder Aus erfunden.
Historische Daten stehen nur im Rahmen der HA-Recorder-Aufbewahrung zur Verfügung.

## Täglich 06:00 und manuell

In `configuration.yaml` ergänzen; einen vorhandenen `rest_command`-Abschnitt
nicht doppelt anlegen. `ANLAGEN-IP` durch die Adresse dieser Anlage ersetzen.

```yaml
rest_command:
  trocknungsbericht_erstellen:
    url: "http://ANLAGEN-IP:8099/bericht"
    method: POST
    timeout: 300
```

Konfiguration prüfen und Home Assistant neu starten. Automation als YAML anlegen:

```yaml
alias: Trocknungsbericht täglich
triggers:
  - trigger: time
    at: "06:00:00"
conditions: []
actions:
  - action: rest_command.trocknungsbericht_erstellen
    response_variable: bericht_antwort
  - condition: template
    value_template: >-
      {{ bericht_antwort is defined
         and bericht_antwort.status == 200
         and bericht_antwort.content.status == 'erstellt' }}
mode: single
```

Manuell über Ausführen starten, ohne Schalter und ohne zusätzlichen Helfer-Button.
Die HA-Zeitzone muss auf Europe/Vienna stehen.

Für E-Mail-Versand die funktionierende `notify.admin`-Konfiguration der jeweiligen
Anlage verwenden und die Versandaktion nach der Erfolgsbedingung ergänzen.
PDF-Anhang: `/config/www/trocknungsberichte/aktueller_bericht.pdf` aus Sicht
von HA Core. Empfänger lokal eintragen. SMTP-Zugang und Automation sind nicht
Bestandteil der App und werden nicht automatisch angelegt.
