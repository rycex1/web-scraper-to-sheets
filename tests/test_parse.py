from pathlib import Path

from scraper.parse import has_next_page, listing_url, parse_detail, parse_listing, stock_count

FIXTURES = Path(__file__).parent / "fixtures"
PAGE_URL = "https://books.toscrape.com/catalogue/page-1.html"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_listing_url():
    assert listing_url(3) == "https://books.toscrape.com/catalogue/page-3.html"


def test_parse_listing_extracts_all_cards():
    records = parse_listing(load("listing.html"), PAGE_URL)
    assert len(records) == 3
    first = records[0]
    assert first["title"] == "Sample Book One: A Long Subtitle"  # full title from the attribute, not the truncated text
    assert first["url"] == "https://books.toscrape.com/catalogue/sample-book-one_1/index.html"
    assert first["price"] == "£51.77"
    assert first["rating"] == "Three"
    assert first["stock"] == "In stock"
    assert records[2]["stock"] == "Out of stock"


def test_has_next_page():
    assert has_next_page(load("listing.html"))
    assert not has_next_page("<html><body><ul class='pager'></ul></body></html>")


def test_parse_detail():
    detail = parse_detail(load("detail.html"))
    assert detail == {"upc": "a897fe39b1053632", "stock": "In stock (22 available)", "category": "Poetry"}


def test_stock_count():
    assert stock_count("In stock (22 available)") == 22
    assert stock_count("In stock") is None
    assert stock_count("") is None
