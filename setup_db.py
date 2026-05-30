"""
setup_db.py — Run this ONCE to create the SQLite database
and migrate all existing CSV data into it.

Run with: python setup_db.py
"""
import sqlite3
import csv
import json
from pathlib import Path

DB_PATH = Path("data/glassfabriken.db")

def setup():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Create tables ──────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        sku          TEXT PRIMARY KEY,
        name         TEXT NOT NULL,
        stock        INTEGER DEFAULT 0,
        price_sek    REAL    DEFAULT 0.0
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id  TEXT PRIMARY KEY,
        name         TEXT NOT NULL,
        address      TEXT DEFAULT '',
        discount_pct INTEGER DEFAULT 0,
        email        TEXT DEFAULT '',
        phone        TEXT DEFAULT '',
        loyalty_points INTEGER DEFAULT 0
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id    TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_lines (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id    TEXT NOT NULL,
        sku         TEXT NOT NULL,
        qty         INTEGER NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    )""")

    print("✅ Tables created.")

    # ── Migrate products.csv ───────────────────────────────────
    products_path = Path("data/products.csv")
    if products_path.exists():
        with open(products_path, encoding="utf-8-sig") as f:
            count = 0
            for row in csv.DictReader(f):
                sku = str(row.get("sku", "")).strip()
                if not sku:
                    continue
                cur.execute("""
                    INSERT OR IGNORE INTO products (sku, name, stock, price_sek)
                    VALUES (?, ?, ?, ?)""",
                    (sku,
                     str(row.get("name", "")).strip(),
                     int(row.get("antal_i_lager") or 0),
                     float(row.get("price_sek") or 0.0)))
                count += 1
        print(f"✅ Migrated {count} products from CSV.")
    else:
        print("⚠️  products.csv not found — skipping.")

    # ── Migrate customers.csv ──────────────────────────────────
    customers_path = Path("data/customers.csv")
    if customers_path.exists():
        with open(customers_path, encoding="utf-8-sig") as f:
            count = 0
            for row in csv.DictReader(f):
                cid = str(row.get("customer_id", "")).strip()
                if not cid:
                    continue
                cur.execute("""
                    INSERT OR IGNORE INTO customers
                    (customer_id, name, address, discount_pct, email, phone, loyalty_points)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (cid,
                     str(row.get("name", "")).strip(),
                     str(row.get("address", "")).strip(),
                     int(row.get("discount_pct") or 0),
                     str(row.get("email", "")).strip(),
                     str(row.get("phone", "")).strip(),
                     int(row.get("loyalty_points") or 0)))
                count += 1
        print(f"✅ Migrated {count} customers from CSV.")
    else:
        print("⚠️  customers.csv not found — skipping.")

    # ── Migrate orders.json ────────────────────────────────────
    orders_path = Path("data/orders.json")
    if orders_path.exists() and orders_path.stat().st_size > 0:
        with open(orders_path, encoding="utf-8") as f:
            try:
                orders = json.load(f)
                count = 0
                for o in orders:
                    cur.execute("""
                        INSERT OR IGNORE INTO orders (order_id, customer_id)
                        VALUES (?, ?)""",
                        (o["order_id"], o["customer_id"]))
                    for line in o.get("lines", []):
                        cur.execute("""
                            INSERT INTO order_lines (order_id, sku, qty)
                            VALUES (?, ?, ?)""",
                            (o["order_id"], line["sku"], line["qty"]))
                    count += 1
                print(f"✅ Migrated {count} orders from JSON.")
            except Exception as e:
                print(f"⚠️  Could not migrate orders: {e}")
    else:
        print("⚠️  orders.json empty or not found — skipping.")

    conn.commit()
    conn.close()
    print(f"\n🎉 Database ready at: {DB_PATH.resolve()}")
    print("   Now run: python -m uvicorn src.server:app --host 0.0.0.0 --port 8003 --reload")

if __name__ == "__main__":
    setup()