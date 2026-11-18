"""Command-line entry point: python -m scraper --pages 5 --output output/books"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from .clean import clean_all
from .export import upload_to_sheets, write_csv, write_excel
from .fetch import Fetcher
from .parse import has_next_page, listing_url, parse_detail, parse_listing

log = logging.getLogger("scraper")


def scrape(pages: int, fetcher: Fetcher, details: bool = False) -> list[dict]:
    """Scrape up to `pages` listing pages (0 = all). Returns raw records."""
    raw: list[dict] = []
    page = 1
    while pages == 0 or page <= pages:
        url = listing_url(page)
        html = fetcher.get(url)
        if html is None:
            break
        records = parse_listing(html, url)
        log.info("Page %d: %d books", page, len(records))
        if details:
            for rec in records:
                detail_html = fetcher.get(rec["url"])
                if detail_html:
                    rec.update(parse_detail(detail_html))
        raw.extend(records)
        if not has_next_page(html):
            break
        page += 1
    return raw


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scraper",
        description="Scrape books.toscrape.com into CSV, Excel and (optionally) Google Sheets.",
    )
    p.add_argument("--pages", type=int, default=5, help="listing pages to scrape, 0 = all (default: 5)")
    p.add_argument("--output", default="output/books", help="output path without extension (default: output/books)")
    p.add_argument("--details", action="store_true", help="also visit each book page for exact stock, UPC and category")
    p.add_argument("--delay", type=float, default=0.5, help="seconds between requests (default: 0.5)")
    p.add_argument("--no-excel", action="store_true", help="skip the .xlsx file")
    p.add_argument("--sheets", action="store_true", help="upload to Google Sheets if credentials are configured")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv()
    if args.pages < 0:
        log.error("--pages must be 0 or more")
        return 2

    raw = scrape(args.pages, Fetcher(delay=args.delay), details=args.details)
    books, rejected = clean_all(raw)
    log.info("Scraped %d rows, kept %d, rejected %d", len(raw), len(books), len(rejected))
    if not books:
        log.error("No valid rows scraped")
        return 1

    out = Path(args.output)
    write_csv(books, out.with_suffix(".csv"))
    if not args.no_excel:
        write_excel(books, out.with_suffix(".xlsx"))
    if args.sheets:
        upload_to_sheets(books)
    return 0


if __name__ == "__main__":
    sys.exit(main())
