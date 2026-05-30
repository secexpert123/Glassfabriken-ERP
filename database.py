"""
database.py — SQLAlchemy Database Setup
Defines the database connection, base model, and all table schemas.
This is the single source of truth for the database structure.
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from pathlib import Path

# Database file location
DB_PATH = Path("data/glassfabriken.db")

# SQLite connection URL — swap this one line to move to PostgreSQL in production:
# DATABASE_URL = "postgresql://user:password@localhost/glassfabriken"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create the SQLAlchemy engine
# connect_args needed for SQLite + FastAPI (different threads)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Base class all ORM models inherit from
Base = declarative_base()

# Session factory — each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── ORM Table Models ───────────────────────────────────────────────────────────

class ProductTable(Base):
    """Maps to 'products' table in the database."""
    __tablename__ = "products"

    sku       = Column(String, primary_key=True, index=True)
    name      = Column(String, nullable=False)
    stock     = Column(Integer, default=0)
    price_sek = Column(Float, default=0.0)


class CustomerTable(Base):
    """Maps to 'customers' table in the database."""
    __tablename__ = "customers"

    customer_id    = Column(String, primary_key=True, index=True)
    name           = Column(String, nullable=False)
    address        = Column(String, default="")
    discount_pct   = Column(Integer, default=0)
    email          = Column(String, default="")
    phone          = Column(String, default="")
    loyalty_points = Column(Integer, default=0)

    # Relationship — one customer can have many orders
    orders = relationship("OrderTable", back_populates="customer")


class OrderTable(Base):
    """Maps to 'orders' table in the database."""
    __tablename__ = "orders"

    order_id    = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"))
    created_at  = Column(DateTime, server_default=func.now())

    # Relationships
    customer = relationship("CustomerTable", back_populates="orders")
    lines    = relationship("OrderLineTable", back_populates="order")


class OrderLineTable(Base):
    """Maps to 'order_lines' table in the database."""
    __tablename__ = "order_lines"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.order_id"))
    sku      = Column(String, nullable=False)
    qty      = Column(Integer, nullable=False)

    # Relationship back to order
    order = relationship("OrderTable", back_populates="lines")


def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)
    print("✅ SQLAlchemy database initialized.")


def get_db():
    """
    FastAPI dependency — yields a database session per request.
    Automatically closes session when request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()