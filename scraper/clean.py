"""Cleaning and validation: raw strings in, typed and checked records out."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, fields

from .parse import RATING_WORDS, stock_count

log = logging.getLogger(__name__)


@dataclass
class Book:
    title: str
    price_gbp: float
    rating: int
    in_stock: bool
    stock_qty: int | None
    category: str
    upc: str
    url: str

    @classmethod
    def columns(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def as_row(self) -> list:
        return list(asdict(self).values())


class ValidationError(ValueError):
    pass


def parse_price(text: str) -> float:
    """'£51.77' or 'Â£51.77' -> 51.77"""
    m = re.search(r"(\d+(?:[.,]\d+)?)", text or "")
    if not m:
        raise ValidationError(f"no price in {text!r}")
    value = float(m.group(1).replace(",", "."))
    if value <= 0:
        raise ValidationError(f"price must be positive, got {value}")
    return round(value, 2)


def parse_rating(word) -> int:
    if isinstance(word, int):
        rating = word
    else:
        rating = RATING_WORDS.get(str(word).strip().title(), 0)
    if not 1 <= rating <= 5:
        raise ValidationError(f"rating must be 1-5, got {word!r}")
    return rating


def clean_record(raw: dict) -> Book:
    title = " ".join((raw.get("title") or "").split())
    if not title:
        raise ValidationError("missing title")
    stock_text = raw.get("stock") or ""
    return Book(
        title=title,
        price_gbp=parse_price(raw.get("price", "")),
        rating=parse_rating(raw.get("rating", "")),
        in_stock="in stock" in stock_text.lower(),
        stock_qty=stock_count(stock_text),
        category=raw.get("category", "") or "",
        upc=raw.get("upc", "") or "",
        url=raw.get("url", "") or "",
    )


def clean_all(raw_records: list[dict]) -> tuple[list[Book], list[tuple[dict, str]]]:
    """Clean every record, dropping duplicates (by URL, else title) and invalid rows.

    Returns (books, rejected) where rejected holds (raw_record, reason) pairs.
    """
    books: list[Book] = []
    rejected: list[tuple[dict, str]] = []
    seen: set[str] = set()
    for raw in raw_records:
        try:
            book = clean_record(raw)
        except ValidationError as exc:
            log.warning("Dropping row %r: %s", raw.get("title"), exc)
            rejected.append((raw, str(exc)))
            continue
        key = book.url or book.title.lower()
        if key in seen:
            rejected.append((raw, "duplicate"))
            continue
        seen.add(key)
        books.append(book)
    return books, rejected
