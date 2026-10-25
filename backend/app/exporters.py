"""Exporters: turn a list of weather records into downloadable files.

Supported formats: JSON, CSV, XML, Markdown and PDF.
Each function returns (content_bytes, media_type, filename) so the API
layer can build a download response without knowing format details.
"""

import csv
import io
import json
from xml.etree import ElementTree as ET

from fpdf import FPDF

# The columns every export shares, in display order.
FIELDS = [
    "id",
    "location_query",
    "resolved_name",
    "country",
    "latitude",
    "longitude",
    "start_date",
    "end_date",
    "avg_temp",
    "min_temp",
    "max_temp",
    "note",
]


def record_to_dict(record):
    """Convert a WeatherRecord model into a plain, JSON-friendly dict."""
    return {
        "id": record.id,
        "location_query": record.location_query,
        "resolved_name": record.resolved_name,
        "country": record.country,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "start_date": record.start_date.isoformat(),
        "end_date": record.end_date.isoformat(),
        "avg_temp": record.avg_temp,
        "min_temp": record.min_temp,
        "max_temp": record.max_temp,
        "note": record.note,
    }


def export_json(records):
    rows = [record_to_dict(r) for r in records]
    content = json.dumps(rows, indent=2).encode("utf-8")
    return content, "application/json", "weather_records.json"


def export_csv(records):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    for record in records:
        writer.writerow(record_to_dict(record))
    return buffer.getvalue().encode("utf-8"), "text/csv", "weather_records.csv"


def export_xml(records):
    root = ET.Element("weather_records")
    for record in records:
        row = ET.SubElement(root, "record")
        for key, value in record_to_dict(record).items():
            child = ET.SubElement(row, key)
            child.text = "" if value is None else str(value)
    content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return content, "application/xml", "weather_records.xml"


def export_markdown(records):
    header = "| " + " | ".join(FIELDS) + " |"
    separator = "| " + " | ".join("---" for _ in FIELDS) + " |"
    lines = ["# Weather Records", "", header, separator]
    for record in records:
        row = record_to_dict(record)
        cells = ["" if row[f] is None else str(row[f]) for f in FIELDS]
        lines.append("| " + " | ".join(cells) + " |")
    content = "\n".join(lines).encode("utf-8")
    return content, "text/markdown", "weather_records.md"


def export_pdf(records):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Weather Records", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(
        0,
        8,
        f"{len(records)} saved weather quer{'y' if len(records) == 1 else 'ies'}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)
    for record in records:
        row = record_to_dict(record)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(
            0,
            7,
            f"#{row['id']} {row['resolved_name']}"
            + (f" ({row['country']})" if row["country"] else ""),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(
            0,
            6,
            f"Queried as: {row['location_query']} | "
            f"Coordinates: {row['latitude']}, {row['longitude']}\n"
            f"Date range: {row['start_date']} to {row['end_date']}\n"
            f"Average temp: {row['avg_temp']} C | "
            f"Min: {row['min_temp']} C | Max: {row['max_temp']} C"
            + (f"\nNote: {row['note']}" if row["note"] else ""),
        )
        pdf.ln(4)
    return bytes(pdf.output()), "application/pdf", "weather_records.pdf"


EXPORTERS = {
    "json": export_json,
    "csv": export_csv,
    "xml": export_xml,
    "markdown": export_markdown,
    "pdf": export_pdf,
}
