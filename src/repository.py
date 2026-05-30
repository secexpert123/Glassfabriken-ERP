"""
repository.py — Data Access Layer (DAL)
Now powered by SQLAlchemy ORM instead of raw CSV/JSON files.
All method signatures are IDENTICAL to the original version —
so engine.py, server.py, and main.py need zero changes.
"""
from pathlib import Path
from typing import Dict, List
from sqlalchemy.orm import Session

from src.models import Customer, Product, Order, OrderLine
from database import SessionLocal, ProductTable, CustomerTable, OrderTable, OrderLineTable, init_db


class ERPRepository:
    def __init__(self, data_dir: Path):
        # data_dir kept for compatibility with engine.py constructor
        self.data_dir = data_dir
        # Initialize database tables on first run
        init_db()

    def _get_session(self) -> Session:
        """Create and return a new database session."""
        return SessionLocal()

    # ── Products ───────────────────────────────────────────────────────────────

    def load_products(self) -> Dict[str, Product]:
        """
        Load all products from SQLite via SQLAlchemy.
        Returns dict keyed by SKU — same as original CSV version.
        """
        db = self._get_session()
        try:
            rows = db.query(ProductTable).all()
            return {
                row.sku: Product(
                    sku=row.sku,
                    name=row.name,
                    stock=row.stock,
                    price_sek=row.price_sek
                )
                for row in rows
            }
        finally:
            db.close()

    def save_all_products(self, products: Dict[str, Product]) -> None:
        """
        Save all products to database.
        Deletes existing records and re-inserts — simple and reliable.
        Called by engine after stock updates, price edits, or deletions.
        """
        db = self._get_session()
        try:
            db.query(ProductTable).delete()
            for p in products.values():
                db.add(ProductTable(
                    sku=p.sku,
                    name=p.name,
                    stock=p.stock,
                    price_sek=p.price_sek
                ))
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    # ── Customers ──────────────────────────────────────────────────────────────

    def load_customers(self) -> Dict[str, Customer]:
        """
        Load all customers from SQLite via SQLAlchemy.
        Returns dict keyed by customer_id — same as original CSV version.
        """
        db = self._get_session()
        try:
            rows = db.query(CustomerTable).all()
            return {
                row.customer_id: Customer(
                    customer_id=row.customer_id,
                    name=row.name,
                    address=row.address,
                    discount_pct=row.discount_pct,
                    email=row.email or "",
                    phone=row.phone or "",
                    loyalty_points=row.loyalty_points or 0
                )
                for row in rows
            }
        finally:
            db.close()

    def save_customer_dict(self, data: Dict) -> None:
        """
        Insert a new customer into the database.
        Checks for duplicates before inserting.
        """
        db = self._get_session()
        try:
            existing = db.query(CustomerTable).filter(
                CustomerTable.customer_id == data["customer_id"]
            ).first()
            if not existing:
                db.add(CustomerTable(
                    customer_id=data["customer_id"],
                    name=data["name"],
                    address=data.get("address", ""),
                    discount_pct=data.get("discount_pct", 0),
                    email=data.get("email", ""),
                    phone=data.get("phone", ""),
                    loyalty_points=0
                ))
                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    # ── Orders ─────────────────────────────────────────────────────────────────

    def load_orders(self) -> List[Order]:
        """
        Load all orders with their lines from SQLite.
        Returns list of Order objects — same as original JSON version.
        """
        db = self._get_session()
        try:
            rows = db.query(OrderTable).all()
            orders = []
            for row in rows:
                lines = [OrderLine(line.sku, line.qty) for line in row.lines]
                orders.append(Order(row.order_id, row.customer_id, lines))
            return orders
        finally:
            db.close()

    def save_order(self, order: Order) -> None:
        """
        Persist a new order and all its lines to the database.
        Uses rollback on failure to maintain data integrity.
        """
        db = self._get_session()
        try:
            db.add(OrderTable(
                order_id=order.order_id,
                customer_id=order.customer_id
            ))
            for line in order.lines:
                db.add(OrderLineTable(
                    order_id=order.order_id,
                    sku=line.sku,
                    qty=line.qty
                ))
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()