"""HTML parsing for books.toscrape.com listing and detail pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
LISTING_URL = BASE_URL + "catalogue/page-{page}.html"

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def listing_url(page: int) -> str:
    return LISTING_URL.format(page=page)


def parse_listing(html: str, page_url: str) -> list[dict]:
    """Extract raw book records from one listing page.

    Values are returned as found on the page; cleaning happens in clean.py.
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        rating_tag = card.select_one("p.star-rating")
        rating_word = next((c for c in (rating_tag.get("class", []) if rating_tag else []) if c in RATING_WORDS), "")
        price_tag = card.select_one("p.price_color")
        stock_tag = card.select_one("p.availability")
        records.append(
            {
                "title": link.get("title") or link.get_text(strip=True) if link else "",
                "url": urljoin(page_url, link["href"]) if link and link.get("href") else "",
                "price": price_tag.get_text(strip=True) if price_tag else "",
                "rating": rating_word,
                "stock": stock_tag.get_text(" ", strip=True) if stock_tag else "",
            }
        )
    return records


def has_next_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return soup.select_one("li.next a") is not None


def parse_detail(html: str) -> dict:
    """Extract extra fields from a book's detail page (exact stock count, UPC, category)."""
    soup = BeautifulSoup(html, "html.parser")
    table = {}
    for row in soup.select("table.table tr"):
        th, td = row.find("th"), row.find("td")
        if th and td:
            table[th.get_text(strip=True)] = td.get_text(strip=True)
    crumbs = [a.get_text(strip=True) for a in soup.select("ul.breadcrumb li a")]
    category = crumbs[2] if len(crumbs) >= 3 else ""
    return {
        "upc": table.get("UPC", ""),
        "stock": table.get("Availability", ""),
        "category": category,
    }


def stock_count(text: str) -> int | None:
    """'In stock (22 available)' -> 22. Returns None if no number is present."""
    m = re.search(r"(\d+)\s+available", text or "")
    return int(m.group(1)) if m else None
