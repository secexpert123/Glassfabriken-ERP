#  Glassfabriken Industrial ERP System

An enterprise-grade industrial Enterprise Resource Planning (ERP) platform built for a wholesale ice cream manufacturing facility. The system features a clean four-tier architecture — upgraded from flat CSV/JSON files to a fully database-backed, tested, and secured platform running across Windows and Linux.

---

## Architectural Overview

Built using **Separation of Concerns (SoC)** — every file has exactly one job:

| File | Role |
|------|------|
| `src/models.py` | Strongly typed domain models using Python dataclasses |
| `src/repository.py` | Data Access Layer (DAL) — all SQLite reads & writes via SQLAlchemy ORM |
| `src/engine.py` | Core business logic — validation, stock checks, order pipeline |
| `src/main.py` | Terminal UI — 7-option menu with dispatch dictionary pattern |
| `src/server.py` | FastAPI REST API server — exposes all ERP logic over HTTP |
| `database.py` | SQLAlchemy table definitions and database connection setup |
| `setup_db.py` | One-time migration — loads CSV/JSON data into SQLite |
| `client.ps1` | PowerShell REST client — calls the API from the command line |
| `index.html` | Web dashboard — secure login, live product catalog, order form |
| `run_tests.py` | Automated QA suite — 54/54 tests passing |

**The key insight:** `main.py`, `server.py`, and `index.html` all call the same `engine.py`. Fix a bug once — all three interfaces benefit automatically.

---

## Project Structure

```
Glassfabriken_ERP/
├── data/
│   └── glassfabriken.db        # SQLite database — Products, Customers, Orders
├── orders_input/
│   └── incoming_orders.json    # Sample batch order file
├── src/
│   ├── engine.py               # Business logic — validation, orders, stock
│   ├── main.py                 # Terminal ERP application
│   ├── models.py               # Data models (Customer, Product, Order, OrderLine)
│   ├── repository.py           # SQLAlchemy DAL — replaced CSV/JSON file I/O
│   └── server.py               # FastAPI REST API server
├── client.ps1                  # PowerShell REST client
├── database.py                 # SQLAlchemy table schemas and DB connection
├── index.html                  # Web dashboard frontend
├── requirements.txt            # All dependencies
├── run_tests.py                # Automated test suite (54 tests)
├── setup_db.py                 # DB migration script — run once to populate data
└── README.md
```

---

## Key Features

- **Atomic order pipeline** — validates ALL line items before deducting ANY stock. All-or-nothing, never a partial allocation.
- **Over-allocation protection** — trying to order more than available stock raises a `ValueError` and blocks the save.
- **Case-insensitive customer lookup** — find customers by ID (`C1001`) or name (`Alfa Livs`).
- **Full CRUD REST API** — GET, POST, PUT, PATCH, DELETE for products and customers.
- **API key security** — all endpoints except `/health` require `X-API-Key` header.
- **Pydantic validation** — all incoming API requests validated with type constraints before processing.
- **Web dashboard** — secure login, addresses and discounts masked for privacy.
- **PowerShell client** — full REST consumption via `Invoke-RestMethod`.
- **54/54 automated tests** — 22 unit tests + 32 API tests, all green.
- **Cross-platform** — developed on Windows (VS Code + PowerShell), deployed on Linux (uvicorn).

---

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up the database (run once)
```bash
python setup_db.py
```

### 3. Start the REST API server — local
```bash
python -m uvicorn src.server:app --host 127.0.0.1 --port 8003 --reload
```

### 4. Start the REST API server — deployed on Linux (accessible from other machines)
```bash
python -m uvicorn src.server:app --host 0.0.0.0 --port 8003 --reload
```

### 5. Run the terminal ERP application
```bash
python -m src.main
```

### 6. Run automated tests
```bash
python run_tests.py
```

### 7. Open web dashboard
```
http://127.0.0.1:8003
```
Enter API key: `glassfabriken-secret-2025`

### 8. Open Swagger API docs
```
http://127.0.0.1:8003/docs
```

---

## REST API Endpoints

All endpoints except `/health` require:
```
X-API-Key: glassfabriken-secret-2025
```

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Public health check — no key required |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products |
| GET | `/products/{sku}` | Get one product by SKU |
| POST | `/products` | Create a new product |
| PUT | `/products/{sku}` | Full update (name, stock, price) |
| PATCH | `/products/{sku}` | Partial update — only send fields to change |
| DELETE | `/products/{sku}` | Remove a product |

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers` | List all customers |
| POST | `/customers` | Register a new customer |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calculate-order` | Preview order total — no stock deducted |
| POST | `/orders` | Place order — deducts stock, saves to database |

---

## PowerShell API Examples

```powershell
$headers = @{"X-API-Key" = "glassfabriken-secret-2025"}
$base = "http://127.0.0.1:8003"

# GET all products
Invoke-RestMethod "$base/products" -Headers $headers

# GET one product by SKU
Invoke-RestMethod "$base/products/10001" -Headers $headers

# Search by name
(Invoke-RestMethod "$base/products" -Headers $headers) | Where-Object { $_.name -like "*Vanilj*" }

# Products under 20 SEK
(Invoke-RestMethod "$base/products" -Headers $headers) | Where-Object { $_.price_sek -lt 20 }

# POST new product
$b = @{sku="10099"; name="TestGlass"; stock=50; price_sek=29.99} | ConvertTo-Json
Invoke-RestMethod "$base/products" -Method POST -Headers $headers -Body $b -ContentType "application/json"

# PATCH price only
$b = @{price_sek=19.99} | ConvertTo-Json
Invoke-RestMethod "$base/products/10099" -Method PATCH -Headers $headers -Body $b -ContentType "application/json"

# DELETE product
Invoke-RestMethod "$base/products/10099" -Method DELETE -Headers $headers

# Test security — no key (expect 403 Forbidden)
Invoke-RestMethod "$base/products"

# Place an order
$b = @{customer_id="C1001"; lines=@(@{sku="10001"; qty=2})} | ConvertTo-Json -Depth 3
Invoke-RestMethod "$base/orders" -Method POST -Headers $headers -Body $b -ContentType "application/json"
```

---

## Terminal Menu Options

```
1. Process Order via Terminal UI
2. Batch Process Orders via JSON File
3. Register New Customer 
4. Register New Product 
5. Edit Product Price / Stock 
6. Delete Product 
7. Terminate System Operations
```

---

## Security

- All API endpoints (except `/health`) are protected with an `X-API-Key` HTTP header.
- The web dashboard login screen holds the key in memory only — it is never embedded in the HTML source.
- Customer addresses and discount percentages are masked in the web UI to protect sensitive business data.
- CORS middleware is configured in `server.py` so the browser can call the API.
- In production, the API key would be stored as an environment variable and HTTPS/TLS enforced.
- Customer records are never deleted via the API — deleting a customer would break historical order records. This follows standard ERP practice.

---

## Known Limitations

- SQLite is used instead of PostgreSQL. The database URL in `database.py` is a single line change to migrate — designed for this upgrade path.
- No real-time synchronisation between the terminal app and the API server — last write wins if both run simultaneously.
- API key is hardcoded in `server.py` for simplicity — production systems use environment variables or secret managers.
- No user roles or JWT authentication — a natural next step after this build.

---

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| Python 3.11+ | Core language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| SQLAlchemy 2.0 | ORM and database abstraction layer |
| SQLite | Embedded relational database |
| Pydantic 2.0 | Request/response validation |
| PowerShell | REST client scripting |
| HTML / CSS / JS | Web dashboard frontend |

---

## Test Results

```
22 / 22 unit tests    ✅
32 / 32 API tests     ✅
──────────────────
54 / 54 total         ✅  All green
```

Upgraded from 13/22 passing (3 failing, 2 skipped) to a fully passing suite after the database migration, stock bug fix, and security improvements.