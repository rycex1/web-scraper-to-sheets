"""Render the README images in docs/ from a real scraper output CSV.

Usage: python scripts/make_docs_images.py output/books_details.csv output/books.csv
(needs matplotlib from requirements-dev.txt)
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DOCS = Path(__file__).resolve().parent.parent / "docs"


def read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def table_preview(rows, out):
    cols = ["title", "price_gbp", "rating", "in_stock", "stock_qty", "category", "upc"]
    labels = ["Title", "Price (GBP)", "Rating", "In stock", "Qty", "Category", "UPC"]
    cells = []
    for r in rows[:12]:
        title = r["title"] if len(r["title"]) <= 38 else r["title"][:37] + "…"
        cells.append([title, f"£{float(r['price_gbp']):.2f}", r["rating"], r["in_stock"], r["stock_qty"], r["category"], r["upc"]])
    fig, ax = plt.subplots(figsize=(12, 4.6), dpi=130)
    ax.axis("off")
    table = ax.table(cellText=cells, colLabels=labels, loc="center", cellLoc="left",
                     colWidths=[0.33, 0.1, 0.07, 0.08, 0.06, 0.16, 0.17])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.35)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#d0d7de")
        if row == 0:
            cell.set_facecolor("#1F3A5F")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f6f8fa")
    ax.set_title("Sample output (first 12 rows of a real --details run)", loc="left", fontsize=11, pad=8)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def rating_chart(rows, out):
    groups = defaultdict(list)
    for r in rows:
        groups[int(r["rating"])].append(float(r["price_gbp"]))
    ratings = sorted(groups)
    avg = [sum(groups[r]) / len(groups[r]) for r in ratings]
    counts = [len(groups[r]) for r in ratings]
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=130)
    bars = ax.bar([f"{r} star" for r in ratings], avg, color="#2f6fb0", width=0.6)
    for bar, n, a in zip(bars, counts, avg):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6, f"£{a:.2f}\n{n} books",
                ha="center", va="bottom", fontsize=8.5, color="#333")
    ax.set_ylabel("Average price (GBP)")
    ax.set_ylim(0, max(avg) * 1.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"Average price by rating ({len(rows)} books scraped)", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


if __name__ == "__main__":
    detail_csv, full_csv = sys.argv[1], sys.argv[2]
    table_preview(read(detail_csv), DOCS / "sample_table.png")
    rating_chart(read(full_csv), DOCS / "price_by_rating.png")
    print("wrote", DOCS / "sample_table.png", DOCS / "price_by_rating.png")
