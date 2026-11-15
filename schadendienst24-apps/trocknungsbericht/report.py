import os
import shutil
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.platypus import (
    PageBreak,
    SimpleDocTemplate, Paragraph, Spacer,
    Image, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from xml.sax.saxutils import escape

HA_URL = "http://supervisor/core/api"
TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
TZ = ZoneInfo("Europe/Vienna")
OUTPUT = Path("/homeassistant/www/trocknungsberichte")

from zuordnung import HUMIDITY, TEMPERATURE, SWITCHES, START_ENTITY

def get_state(entity, optional=False):
    response = requests.get(
        f"{HA_URL}/states/{entity}",
        headers=HEADERS,
        timeout=20
    )
    if response.status_code == 404 and optional:
        return "nicht aktiv"
    response.raise_for_status()
    return response.json()["state"]


def get_history(entities, start, end):
    url = (
        f"{HA_URL}/history/period/"
        f"{quote(start.isoformat(), safe=':T+-')}"
    )
    response = requests.get(
        url,
        headers=HEADERS,
        params={
            "filter_entity_id": ",".join(entities),
            "end_time": end.isoformat(),
            "minimal_response": "true",
            "no_attributes": "true",
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()


def apply_time_axis(ax, start, end):
    from datetime import timedelta, timezone

    duration = (end - start).total_seconds() / 86400

    if duration <= 2:
        hours = 6
    elif duration <= 7:
        hours = 12
    elif duration <= 21:
        hours = 24
    else:
        hours = 48

    ticks = []
    current = start.astimezone(timezone.utc)

    while current <= end.astimezone(timezone.utc):
        ticks.append(current)
        current += timedelta(hours=hours)

    ax.set_xlim(start, end)
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d.%m %H:%M", tz=TZ)
    )


def make_chart(history, entities, names, title, ylabel, path, start, end):
    fig, ax = plt.subplots(figsize=(10, 4.3))
    plotted = 0

    for series in history:
        if not series:
            continue

        entity = series[0].get("entity_id")
        if entity not in entities:
            continue

        index = entities.index(entity)
        points = []

        for item in series:
            try:
                value = float(item["state"])
                stamp = item.get("last_changed")
                if stamp:
                    moment = datetime.fromisoformat(stamp)
                    points.append((moment.astimezone(TZ), value))
            except (ValueError, TypeError, KeyError):
                continue

        if not points:
            continue

        points.sort(key=lambda item: item[0])
        x, y = zip(*points)
        ax.plot(x, y, label=f"TH{index+1} - {names[index]}")
        plotted += 1

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Datum / Uhrzeit")
    apply_time_axis(ax, start, end)
    ax.grid(True, alpha=0.3)

    if plotted:
        ax.legend(fontsize=7, loc="best")
    else:
        ax.text(
            0.5, 0.5, "Keine Messwerte vorhanden",
            transform=ax.transAxes,
            ha="center", va="center"
        )

    fig.autofmt_xdate()
    fig.subplots_adjust(left=0.19, right=0.97, top=0.88, bottom=0.24)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return plotted


def create_report():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    customer = get_state("input_text.name_der_trocknung")
    start_text = get_state(START_ENTITY)
    start = datetime.fromisoformat(start_text).replace(tzinfo=TZ)
    end = datetime.now(TZ)

    if start > end:
        raise ValueError("Trocknungsbeginn liegt in der Zukunft")

    names = []
    for i in range(1, 9):
        value = get_state(f"input_text.th{i}", optional=True)
        if value in ("unknown", "unavailable", ""):
            value = f"Messstelle {i}"
        names.append(value)

    active_indices = [
        i for i, name in enumerate(names)
        if name.strip().casefold() != "nicht aktiv"
    ]
    channel_names = [get_state(f"input_text.kanal{i}", optional=True) for i in range(1, 4)]
    active_channels = [
        i for i, name in enumerate(channel_names)
        if name.strip().casefold() not in ("nicht aktiv", "unknown", "unavailable", "")
    ]
    active_switches = [SWITCHES[i] for i in active_channels]
    switch_history = get_history(active_switches, start, end) if active_switches else []
    print("Aktive Gerätekanäle:", [channel_names[i] for i in active_channels], flush=True)
    print("Schaltverläufe abgerufen:", len(switch_history), flush=True)
    for i, records in enumerate(switch_history):
        print("Kanal:", active_switches[i], "Datenpunkte:", len(records), flush=True)
        print("Zustände:", [(r.get("state"), r.get("last_changed")) for r in records[:5]], flush=True)



    active_humidity = [HUMIDITY[i] for i in active_indices]
    active_temperature = [TEMPERATURE[i] for i in active_indices]

    print("Lese Feuchteverlauf...", flush=True)
    humidity_history = get_history(active_humidity, start, end) if active_humidity else []

    print("Lese Temperaturverlauf...", flush=True)
    temperature_history = get_history(active_temperature, start, end) if active_temperature else []

    humidity_chart = Path("/tmp/feuchte.png")
    temperature_chart = Path("/tmp/temperatur.png")

    humidity_count = make_chart(
        humidity_history, HUMIDITY, names,
        "Luftfeuchtigkeit", "Relative Feuchte (%)",
        humidity_chart, start, end
    )
    temperature_count = make_chart(
        temperature_history, TEMPERATURE, names,
        "Temperatur", "Temperatur (°C)",
        temperature_chart, start, end
    )

    switch_chart = Path("/tmp/geraete.png")
    if active_switches:
        make_switch_chart(
            switch_history,
            active_switches,
            [channel_names[i].strip() for i in active_channels],
            start, end, switch_chart
        )

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", customer).strip("_")
    safe_name = safe_name[:60] or "Trocknung"
    filename = f"{safe_name}_{end:%Y-%m-%d_%H-%M-%S}.pdf"
    pdf_path = OUTPUT / filename

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=(21 * cm, 29.7 * cm),
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
    )

    story = [
        Paragraph("SchadenDienst24 Villach", styles["Title"]),
        Paragraph("Trocknungsbericht", styles["Heading2"]),
        Spacer(1, 0.4 * cm),
        Paragraph(f"<b>Trocknung:</b> {escape(customer)}", styles["Normal"]),
        Paragraph(
            f"<b>Beginn:</b> {start:%d.%m.%Y %H:%M}",
            styles["Normal"]
        ),
        Paragraph(
            f"<b>Berichtsdatum:</b> {end:%d.%m.%Y %H:%M}",
            styles["Normal"]
        ),
        Spacer(1, 0.6 * cm),
        Image(str(humidity_chart), width=17 * cm, height=7.3 * cm),
        Spacer(1, 0.4 * cm),
        Image(str(temperature_chart), width=17 * cm, height=7.3 * cm),
        Spacer(1, 0.5 * cm),
        PageBreak(),
    ]

    if active_switches:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Image(str(switch_chart), width=17 * cm, height=4.8 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Messstellen", styles["Heading2"]))

    rows = [["Sensor", "Bezeichnung"]]
    rows.extend([
        [f"TH{i+1}", Paragraph(escape(name), styles["Normal"])]
        for i, name in enumerate(names) if i in active_indices
    ])

    table = Table(rows, colWidths=[3 * cm, 14 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    doc.build(story)
    shutil.copyfile(pdf_path, OUTPUT / "aktueller_bericht.pdf")

    print("PDF ERSTELLT:", pdf_path, flush=True)
    print("Feuchte-Messreihen:", humidity_count, flush=True)
    print("Temperatur-Messreihen:", temperature_count, flush=True)
    print("Browserpfad: /local/trocknungsberichte/" + filename, flush=True)


print("Trocknungsbericht gestartet.", flush=True)
print("Supervisor-Token vorhanden:", bool(TOKEN), flush=True)



from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

REPORT_LOCK = threading.Lock()


def make_switch_chart(history, entities, names, start, end, path):
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(10, 2.8))

    colors_map = {
        "on": "#2e8b57",
        "off": "#a0a0a0"
    }

    for i, entity in enumerate(entities):
        records = next(
            (group for group in history
             if group and group[0].get("entity_id") == entity),
            []
        )

        intervals = switch_intervals(records, start, end)

        for begin, finish, state in intervals:
            if state not in colors_map:
                continue

            ax.broken_barh(
                [(mdates.date2num(begin),
                  mdates.date2num(finish) - mdates.date2num(begin))],
                (i - 0.35, 0.7),
                facecolors=colors_map[state]
            )

    ax.set_yticks(range(len(entities)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    apply_time_axis(ax, start, end)

    ax.set_title("Betriebszeiten der Trocknungsgeräte")
    ax.grid(axis="x", alpha=0.25)

    ax.legend(
        handles=[
            Patch(color="#2e8b57", label="Ein"),
            Patch(color="#a0a0a0", label="Aus")
        ],
        loc="upper right", bbox_to_anchor=(1.0, 1.20), ncol=2
    )

    fig.autofmt_xdate()
    fig.subplots_adjust(left=0.19, right=0.97, top=0.88, bottom=0.24)
    fig.savefig(path, dpi=140)
    plt.close(fig)

def switch_intervals(records, start, end):
    from datetime import datetime, timezone

    def parse_time(value):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    start = parse_time(start.isoformat())
    end = parse_time(end.isoformat())

    if not records:
        return [(start, end, "unknown")]

    events = []
    for record in records:
        timestamp = record.get("last_changed") or record.get("last_updated")
        if not timestamp:
            continue
        state = record.get("state", "unknown")
        if state not in ("on", "off"):
            state = "unknown"
        events.append((parse_time(timestamp), state))

    events.sort(key=lambda item: item[0])

    intervals = []
    current_time = start
    current_state = "unknown"

    for timestamp, state in events:
        if timestamp <= start:
            current_state = state
            continue
        if timestamp >= end:
            break
        if timestamp > current_time:
            intervals.append((current_time, timestamp, current_state))
        current_time = timestamp
        current_state = state

    if current_time < end:
        intervals.append((current_time, end, current_state))

    return intervals

class ReportHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return

        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/bericht":
            self.send_error(404)
            return

        if not REPORT_LOCK.acquire(blocking=False):
            self.send_error(409, "Bericht wird bereits erstellt")
            return

        try:
            create_report()
            body = json.dumps({"status": "erstellt"}).encode()
            status = 200
        except Exception as error:
            print("BERICHTSFEHLER:", repr(error), flush=True)
            body = json.dumps({"error": str(error)}).encode()
            status = 500
        finally:
            REPORT_LOCK.release()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


print("HTTP-Server startet auf Port 8099", flush=True)
HTTPServer(("0.0.0.0", 8099), ReportHandler).serve_forever()

