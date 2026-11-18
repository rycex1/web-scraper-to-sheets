import csv

from openpyxl import load_workbook

from scraper.clean import Book
from scraper.export import summarize, upload_to_sheets, write_csv, write_excel
from scraper.fetch import build_session

BOOKS = [
    Book("Alpha", 10.0, 5, True, 4, "Poetry", "u1", "https://example.test/a"),
    Book("Beta", 20.0, 5, True, None, "", "", "https://example.test/b"),
    Book("Gamma", 30.0, 1, False, None, "", "", "https://example.test/c"),
]


def test_write_csv_roundtrip(tmp_path):
    path = write_csv(BOOKS, tmp_path / "books.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 3
    assert rows[0]["title"] == "Alpha"
    assert rows[2]["price_gbp"] == "30.0"


def test_write_excel_has_formatted_header_and_summary(tmp_path):
    path = write_excel(BOOKS, tmp_path / "books.xlsx")
    wb = load_workbook(path)
    ws = wb["Books"]
    assert ws["A1"].value == "Title"
    assert ws["A1"].font.bold
    assert ws.freeze_panes == "A2"
    assert ws.max_row == 4
    assert "£" in ws["B2"].number_format
    summary = wb["Summary"]
    assert [c.value for c in summary[2]] == [5, 2, 15.0]
    assert [c.value for c in summary[3]] == [1, 1, 30.0]


def test_summarize():
    assert summarize(BOOKS) == [(5, 2, 15.0), (1, 1, 30.0)]


def test_sheets_upload_skipped_without_config(monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)
    assert upload_to_sheets(BOOKS) is False


def test_sheets_upload_skipped_when_credentials_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setenv("GOOGLE_SHEET_ID", "placeholder")
    assert upload_to_sheets(BOOKS) is False


def test_session_retries_with_backoff():
    session = build_session(retries=3, backoff=0.5)
    retry = session.get_adapter("https://books.toscrape.com").max_retries
    assert retry.total == 3
    assert retry.backoff_factor == 0.5
    assert 503 in retry.status_forcelist
    assert session.headers["User-Agent"].startswith("portfolio-demo")
