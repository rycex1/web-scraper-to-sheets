import pytest

from scraper.clean import ValidationError, clean_all, clean_record, parse_price, parse_rating


@pytest.mark.parametrize("text,expected", [("£51.77", 51.77), ("Â£13.99", 13.99), ("12,50 €", 12.5)])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("bad", ["", "free", "£0.00"])
def test_parse_price_rejects_bad_values(bad):
    with pytest.raises(ValidationError):
        parse_price(bad)


def test_parse_rating():
    assert parse_rating("Three") == 3
    assert parse_rating("five") == 5
    assert parse_rating(4) == 4
    with pytest.raises(ValidationError):
        parse_rating("Zero")


def test_clean_record_types_and_whitespace():
    book = clean_record(
        {"title": "  A   Book \n", "price": "£10.50", "rating": "Two", "stock": "In stock (3 available)", "url": "u1"}
    )
    assert book.title == "A Book"
    assert book.price_gbp == 10.5
    assert book.rating == 2
    assert book.in_stock is True
    assert book.stock_qty == 3


def test_clean_all_drops_invalid_and_duplicates():
    raw = [
        {"title": "Good", "price": "£5.00", "rating": "One", "stock": "In stock", "url": "u1"},
        {"title": "Good again", "price": "£5.00", "rating": "One", "stock": "In stock", "url": "u1"},  # duplicate URL
        {"title": "", "price": "£5.00", "rating": "One", "stock": "In stock", "url": "u2"},  # no title
        {"title": "No price", "price": "", "rating": "One", "stock": "In stock", "url": "u3"},
        {"title": "Sold out", "price": "£7.00", "rating": "Five", "stock": "Out of stock", "url": "u4"},
    ]
    books, rejected = clean_all(raw)
    assert [b.title for b in books] == ["Good", "Sold out"]
    assert books[1].in_stock is False
    assert sorted(reason for _, reason in rejected) == ["duplicate", "missing title", "no price in ''"]
