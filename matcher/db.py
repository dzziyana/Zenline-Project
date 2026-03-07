"""SQLite database backend for product matching.

Stores products, matches, and scraping results persistently.
Provides search and query capabilities for the web UI.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Match, Product

DEFAULT_DB = Path("data/matcher.db")


def get_connection(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            reference TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT DEFAULT '',
            category TEXT DEFAULT '',
            price_eur REAL,
            ean TEXT,
            url TEXT,
            image_url TEXT,
            retailer TEXT,
            specifications TEXT DEFAULT '{}',
            is_source INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_reference TEXT NOT NULL,
            target_reference TEXT NOT NULL,
            target_name TEXT DEFAULT '',
            target_retailer TEXT DEFAULT '',
            target_url TEXT DEFAULT '',
            target_price REAL,
            confidence REAL DEFAULT 0.0,
            method TEXT DEFAULT '',
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_reference, target_reference)
        );

        CREATE TABLE IF NOT EXISTS scrape_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_reference TEXT NOT NULL,
            retailer TEXT NOT NULL,
            query TEXT NOT NULL,
            result_name TEXT,
            result_url TEXT,
            result_price REAL,
            result_ean TEXT,
            matched INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            source_count INTEGER,
            target_count INTEGER,
            match_count INTEGER,
            sources_matched INTEGER,
            methods TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_products_ean ON products(ean);
        CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
        CREATE INDEX IF NOT EXISTS idx_products_retailer ON products(retailer);
        CREATE INDEX IF NOT EXISTS idx_products_source ON products(is_source);
        CREATE INDEX IF NOT EXISTS idx_matches_source ON matches(source_reference);
        CREATE INDEX IF NOT EXISTS idx_matches_target ON matches(target_reference);
        CREATE INDEX IF NOT EXISTS idx_matches_method ON matches(method);
    """)


def insert_products(conn: sqlite3.Connection, products: list[Product], is_source: bool = False):
    conn.executemany(
        """INSERT OR REPLACE INTO products
           (reference, name, brand, category, price_eur, ean, url, image_url, retailer, specifications, is_source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(p.reference, p.name, p.brand, p.category, p.price_eur, p.ean,
          p.url, p.image_url, p.retailer, json.dumps(p.specifications), int(is_source))
         for p in products]
    )
    conn.commit()


def insert_matches(conn: sqlite3.Connection, matches: list[Match]):
    conn.executemany(
        """INSERT OR REPLACE INTO matches
           (source_reference, target_reference, target_name, target_retailer,
            target_url, target_price, confidence, method)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(m.source_reference, m.target_reference, m.target_name, m.target_retailer,
          m.target_url, m.target_price, m.confidence, m.method)
         for m in matches]
    )
    conn.commit()


def insert_scrape_results(conn: sqlite3.Connection, results: list[dict]):
    """Store raw scrape results for auditing."""
    conn.executemany(
        """INSERT INTO scrape_results
           (source_reference, retailer, query, result_name, result_url, result_price, result_ean, matched)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r.get("source_reference", ""), r.get("retailer", ""), r.get("query_used", ""),
          r.get("name", ""), r.get("url", ""), r.get("price"), r.get("ean"), 0)
         for r in results]
    )
    conn.commit()


def log_pipeline_run(conn: sqlite3.Connection, category: str, source_count: int,
                     target_count: int, matches: list[Match]):
    by_method: dict[str, int] = {}
    for m in matches:
        by_method[m.method] = by_method.get(m.method, 0) + 1
    sources_matched = len({m.source_reference for m in matches})
    conn.execute(
        """INSERT INTO pipeline_runs (category, source_count, target_count, match_count, sources_matched, methods)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (category, source_count, target_count, len(matches), sources_matched, json.dumps(by_method))
    )
    conn.commit()


def search_products(conn: sqlite3.Connection, query: str, limit: int = 20,
                    brand: str | None = None, retailer: str | None = None,
                    source_only: bool = False) -> list[dict]:
    """Full-text search across product names, brands, and EANs.

    Splits multi-word queries into terms and requires each term to match
    somewhere in name, ean, or brand.
    """
    terms = query.strip().split()
    if not terms:
        return []

    clauses = []
    params: list = []
    for term in terms:
        clauses.append("(name LIKE ? OR ean LIKE ? OR brand LIKE ?)")
        params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])

    sql = "SELECT * FROM products WHERE " + " AND ".join(clauses)

    if brand:
        sql += " AND brand LIKE ?"
        params.append(f"%{brand}%")
    if retailer:
        sql += " AND retailer LIKE ?"
        params.append(f"%{retailer}%")
    if source_only:
        sql += " AND is_source = 1"

    sql += " ORDER BY is_source DESC, name LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_matches_for_source(conn: sqlite3.Connection, source_ref: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM matches WHERE source_reference = ? ORDER BY confidence DESC",
        (source_ref,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_sources(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM products WHERE is_source = 1 ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


def get_unmatched_sources(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT p.* FROM products p
        WHERE p.is_source = 1
        AND p.reference NOT IN (SELECT DISTINCT source_reference FROM matches)
        ORDER BY p.name
    """).fetchall()
    return [dict(r) for r in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    source_count = conn.execute("SELECT COUNT(*) FROM products WHERE is_source = 1").fetchone()[0]
    target_count = conn.execute("SELECT COUNT(*) FROM products WHERE is_source = 0").fetchone()[0]
    match_count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    sources_matched = conn.execute("SELECT COUNT(DISTINCT source_reference) FROM matches").fetchone()[0]

    methods = conn.execute(
        "SELECT method, COUNT(*) as cnt FROM matches GROUP BY method ORDER BY cnt DESC"
    ).fetchall()

    retailers = conn.execute(
        "SELECT DISTINCT retailer FROM products WHERE retailer IS NOT NULL ORDER BY retailer"
    ).fetchall()

    # Confidence histogram (10 buckets: 0-10%, 10-20%, ..., 90-100%)
    hist_rows = conn.execute("""
        SELECT CAST(confidence * 10 AS INTEGER) as bucket, COUNT(*) as cnt
        FROM matches GROUP BY bucket ORDER BY bucket
    """).fetchall()
    histogram = {i: 0 for i in range(11)}
    for r in hist_rows:
        bucket = min(r["bucket"], 10)
        histogram[bucket] = r["cnt"]
    confidence_histogram = [histogram[i] for i in range(11)]

    return {
        "source_count": source_count,
        "target_count": target_count,
        "match_count": match_count,
        "sources_matched": sources_matched,
        "methods": {r["method"]: r["cnt"] for r in methods},
        "retailers": [r["retailer"] for r in retailers],
        "confidence_histogram": confidence_histogram,
    }


def get_product(conn: sqlite3.Connection, reference: str) -> dict | None:
    row = conn.execute("SELECT * FROM products WHERE reference = ?", (reference,)).fetchone()
    if row:
        result = dict(row)
        result["specifications"] = json.loads(result.get("specifications", "{}"))
        return result
    return None
