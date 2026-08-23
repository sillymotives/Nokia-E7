#!/usr/bin/env python3
"""Build the Nokia E7 native-content v1 PDF and ZIP fixtures."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / "payloads" / "native-content-v1"
PDF_DIR = ROOT / "output" / "pdf"
PDF_PATH = PDF_DIR / "KAI-ADOBE-PROBE.PDF"
ZIP_PATH = PAYLOAD_DIR / "KAI-ZIP-PROBE.ZIP"
ZIP_SOURCE = PAYLOAD_DIR / "KAI-ZIP-CONTENTS.TXT"


def build_pdf() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    pdf = canvas.Canvas(
        str(PDF_PATH),
        pagesize=A4,
        pageCompression=0,
        pdfVersion=(1, 3),
        invariant=1,
    )
    pdf.setTitle("KAI Nokia E7 Adobe Reader Probe V1")
    pdf.setAuthor("Nokia E7 resurrection project")
    pdf.setSubject("Offline PDF compatibility fixture")

    navy = (23 / 255, 50 / 255, 77 / 255)
    blue = (45 / 255, 115 / 255, 185 / 255)
    pale = (234 / 255, 242 / 255, 248 / 255)
    grey = (86 / 255, 101 / 255, 115 / 255)
    near_white = (248 / 255, 250 / 255, 252 / 255)

    pdf.setFillColorRGB(*navy)
    pdf.rect(0, page_height - 118, page_width, 118, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(48, page_height - 68, "Nokia E7 Native PDF Test")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, page_height - 90, "KAI compatibility fixture v1 - offline and server-free")

    y = page_height - 162
    pdf.setFillColorRGB(*navy)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(48, y, "PASS condition")
    y -= 28
    pdf.setFillColorRGB(*grey)
    pdf.setFont("Helvetica", 11)
    lines = [
        "Adobe Reader opens this page without an activation or network prompt.",
        "The title, blue table, alphabet, digits, and footer are all legible.",
        "Page navigation reports one page and zooming does not corrupt the layout.",
    ]
    for line in lines:
        pdf.drawString(48, y, line)
        y -= 18

    y -= 16
    row_height = 34
    table_x = 48
    table_width = page_width - 96
    column = 150
    rows = [
        ("Document", "KAI-ADOBE-PROBE.PDF"),
        ("Format", "PDF 1.3, one page, standard Helvetica"),
        ("Target", "Nokia E7-00 / Belle Refresh"),
        ("Network", "Not required"),
    ]
    for index, (label, value) in enumerate(rows):
        row_y = y - row_height
        pdf.setFillColorRGB(*(pale if index % 2 == 0 else near_white))
        pdf.rect(table_x, row_y, table_width, row_height, fill=1, stroke=0)
        pdf.setStrokeColorRGB(*blue)
        pdf.rect(table_x, row_y, table_width, row_height, fill=0, stroke=1)
        pdf.line(table_x + column, row_y, table_x + column, row_y + row_height)
        pdf.setFillColorRGB(*navy)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(table_x + 10, row_y + 12, label)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(table_x + column + 10, row_y + 12, value)
        y = row_y

    y -= 42
    pdf.setFillColorRGB(*navy)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(48, y, "Glyph check")
    y -= 24
    pdf.setFillColorRGB(*grey)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(48, y, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    y -= 18
    pdf.drawString(48, y, "abcdefghijklmnopqrstuvwxyz")
    y -= 18
    pdf.drawString(48, y, "0123456789  !  ?  /  +  -  =  (  )")

    pdf.setStrokeColorRGB(*blue)
    pdf.line(48, 54, page_width - 48, 54)
    pdf.setFillColorRGB(*grey)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(48, 38, "Controlled local fixture - no historical Nokia or Microsoft endpoint involved")
    pdf.drawRightString(page_width - 48, 38, "Page 1 of 1")

    pdf.showPage()
    pdf.save()


def build_zip() -> None:
    data = ZIP_SOURCE.read_bytes()
    info = ZipInfo("KAI-ZIP-CONTENTS.TXT", date_time=(2026, 8, 23, 20, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.create_system = 0
    info.external_attr = 0
    with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.comment = b"Nokia E7 native ZIP compatibility fixture v1"
        archive.writestr(info, data)


if __name__ == "__main__":
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    build_pdf()
    build_zip()
    print(PDF_PATH)
    print(ZIP_PATH)
