"""Export to CSV, a formatted Excel workbook, and (optionally) Google Sheets."""

from __future__ import annotations

import csv
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .clean import Book

log = logging.getLogger(__name__)

HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADERS = {
    "title": "Title",
    "price_gbp": "Price (GBP)",
    "rating": "Rating (1-5)",
    "in_stock": "In stock",
    "stock_qty": "Qty available",
    "category": "Category",
    "upc": "UPC",
    "url": "URL",
}


def write_csv(books: list[Book], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(Book.columns())
        for b in books:
            writer.writerow(b.as_row())
    log.info("Wrote %d rows to %s", len(books), path)
    return path


def _style_header(ws, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22


def _autosize(ws, max_width: int = 60) -> None:
    widths: dict[int, int] = defaultdict(int)
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                widths[cell.column] = max(widths[cell.column], len(str(cell.value)))
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = min(max(width + 2, 10), max_width)


def summarize(books: list[Book]) -> list[tuple[int, int, float]]:
    """(rating, count, average price) for each rating present, highest rating first."""
    groups: dict[int, list[float]] = defaultdict(list)
    for b in books:
        groups[b.rating].append(b.price_gbp)
    return [(r, len(p), round(sum(p) / len(p), 2)) for r, p in sorted(groups.items(), reverse=True)]


def write_excel(books: list[Book], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Books"
    cols = Book.columns()
    ws.append([HEADERS[c] for c in cols])
    for b in books:
        ws.append(b.as_row())
    _style_header(ws, len(cols))
    price_col = cols.index("price_gbp") + 1
    for row in ws.iter_rows(min_row=2, min_col=price_col, max_col=price_col):
        for cell in row:
            cell.number_format = '"£"#,##0.00'
    ws.auto_filter.ref = ws.dimensions
    _autosize(ws)

    summary = wb.create_sheet("Summary")
    summary.append(["Rating", "Books", "Average price (GBP)"])
    for rating, count, avg in summarize(books):
        summary.append([rating, count, avg])
    summary.append([])
    summary.append(["Total books", len(books)])
    summary.append(["Generated (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")])
    _style_header(summary, 3)
    for row in summary.iter_rows(min_row=2, min_col=3, max_col=3):
        for cell in row:
            if isinstance(cell.value, float):
                cell.number_format = '"£"#,##0.00'
    _autosize(summary)

    wb.save(path)
    log.info("Wrote %d rows to %s", len(books), path)
    return path


def sheets_configured() -> bool:
    return bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") and os.getenv("GOOGLE_SHEET_ID"))


def upload_to_sheets(books: list[Book], worksheet_name: str = "Books") -> bool:
    """Replace the worksheet's contents with the data. Returns False (and logs why) if skipped."""
    if not sheets_configured():
        log.info("Google Sheets upload skipped: GOOGLE_SERVICE_ACCOUNT_FILE / GOOGLE_SHEET_ID not set")
        return False
    creds_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    if not Path(creds_file).is_file():
        log.warning("Google Sheets upload skipped: credentials file %s not found", creds_file)
        return False
    try:
        import gspread
    except ImportError:
        log.warning("Google Sheets upload skipped: gspread is not installed")
        return False

    client = gspread.service_account(filename=creds_file)
    sheet = client.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        ws = sheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=worksheet_name, rows=len(books) + 10, cols=len(Book.columns()))
    ws.clear()
    ws.update([[HEADERS[c] for c in Book.columns()]] + [b.as_row() for b in books], "A1")
    ws.format("1:1", {"textFormat": {"bold": True}})
    log.info("Uploaded %d rows to Google Sheet %s / %s", len(books), sheet.title, worksheet_name)
    return True
