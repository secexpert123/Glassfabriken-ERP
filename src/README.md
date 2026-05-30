# Glassfabriken Industrial ERP System

An enterprise-grade, localized industrial Enterprise Resource Planning (ERP) platform designed for a wholesale ice cream manufacturing facility. This system features a robust, decoupled three-tier architecture that automates sales order ingestion, performs atomic inventory allocations, and manages long-term master data.

---

## 🏗️ Architectural Overview

The system is built utilizing **Separation of Concerns (SoC)** to ensure high maintainability, testability, and scalability:

| File | Role |
|------|------|
| `src/models.py` | Strongly typed Domain Models using Python dataclasses (OOP) |
| `src/repository.py` | Data Access Layer (DAL) — isolates all CSV/JSON file I/O |
| `src/engine.py` | Core Business Logic — validation, order processing, stock management |
| `src/main.py` | Terminal UI — 7-option menu with dispatch dictionary pattern |
| `src/server.py` | FastAPI REST API Server — exposes all ERP logic over HTTP |
| `client.ps1` | PowerShell REST client — calls the API from the command line |
| `index.html` | Dark professional web dashboard — full browser-based ERP UI |
| `run_tests.py` | Automated QA test suite — validates core business logic |

---

## 📁 Project Structure

```
Glassfabriken_ERP/
├── data/
│   ├── customers.csv        # Customer master data
│   ├── products.csv         # Product catalog with stock levels
│   └── orders.json          # Persisted order history
├── orders_input/
│   └── incoming_orders.json # Sample batch order file
├── src/
│   ├── api.py               # Early draft (unused)
│   ├── engine.py            # Business logic layer
│   ├── main.py              # Terminal ERP application
│   ├── models.py            # Data models (Customer, Product, Order)
│   ├── repository.py        # File I/O layer
│   └── server.py            # FastAPI REST API server
├── client.ps1               # PowerShell REST client
├── index.html               # Web dashboard frontend
├── run_tests.py             # Automated test suite
└── README.md
```

---

## 🚀 Key Features Implemented

- **Omni-channel Order Ingestion:** Processes multi-line sales orders via interactive terminal UI and batch JSON file drops.
- **Case-Insensitive Validation:** Customers can be looked up by ID or name (e.g. `C1001` or `Alfa Livs`).
- **Over-Allocation Protection:** Aggregates all line items before stock deduction to prevent negative inventory.
- **Automated Order ID Generation:** Generates predictable sequences (e.g. `ORD-1`, `ORD-2`).
- **Full CRUD via REST API:** GET, POST, PUT, PATCH, DELETE for products and customers over HTTP.
- **API Key Security:** All protected endpoints require `X-API-Key` header authentication.
- **Pydantic Validation:** All incoming API requests are validated with type constraints before processing.
- **Web Dashboard:** Dark professional browser UI with real-time API integration.
- **PowerShell Client:** Demonstrates full REST API consumption from PowerShell using `Invoke-RestMethod`.
- **Master Data Integrity (VG):** Add, edit, and delete products; register new customers — all persisted to CSV.

---

## ▶️ How to Run

### 1. Install dependencies
```bash
pip install fastapi "uvicorn[standard]" pydantic
```

### 2. Start the REST API server (local)
```bash
python -m uvicorn src.server:app --host 127.0.0.1 --port 8003 --reload
```

### 3. Start the REST API server (deployed on Linux)
```bash
python -m uvicorn src.server:app --host 0.0.0.0 --port 8003 --reload
```

### 4. Run the terminal ERP application
```bash
python -m src.main
```

### 5. Run the PowerShell client
```powershell
.\client.ps1
```

### 6. Run automated tests
```bash
python run_tests.py
```

### 7. Open web dashboard
```
http://127.0.0.1:8003
```

### 8. Open Swagger API docs
```
http://127.0.0.1:8003/docs
```

---

## 🌐 REST API Endpoints

All endpoints except `/health` require the API key header:
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
| PATCH | `/products/{sku}` | Partial update (only fields sent) |
| DELETE | `/products/{sku}` | Remove a product |

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers` | List all customers |
| POST | `/customers` | Register a new customer |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calculate-order` | Preview order total (no stock deducted) |
| POST | `/orders` | Place order — deducts stock, saves to JSON |

---

## 💻 PowerShell API Examples

```powershell
$headers = @{"X-API-Key" = "glassfabriken-secret-2025"}
$base = "http://127.0.0.1:8003"

# GET all products
Invoke-RestMethod "$base/products" -Headers $headers

# GET one product
Invoke-RestMethod "$base/products/10001" -Headers $headers

# POST new product
$b = @{sku="10099"; name="TestGlass"; stock=50; price_sek=29.99} | ConvertTo-Json
Invoke-RestMethod "$base/products" -Method POST -Headers $headers -Body $b -ContentType "application/json"

# PUT full update
$b = @{name="TestGlass Pro"; stock=100; price_sek=39.99} | ConvertTo-Json
Invoke-RestMethod "$base/products/10099" -Method PUT -Headers $headers -Body $b -ContentType "application/json"

# PATCH price only
$b = @{price_sek=19.99} | ConvertTo-Json
Invoke-RestMethod "$base/products/10099" -Method PATCH -Headers $headers -Body $b -ContentType "application/json"

# DELETE product
Invoke-RestMethod "$base/products/10099" -Method DELETE -Headers $headers

# Search by name
(Invoke-RestMethod "$base/products" -Headers $headers) | Where-Object { $_.name -like "*Vanilj*" }

# Products under 20 SEK
(Invoke-RestMethod "$base/products" -Headers $headers) | Where-Object { $_.price_sek -lt 20 }

# Place an order
$b = @{customer_id="C1001"; lines=@(@{sku="10001"; qty=2})} | ConvertTo-Json -Depth 3
Invoke-RestMethod "$base/orders" -Method POST -Headers $headers -Body $b -ContentType "application/json"
```

---

## 🖥️ Terminal Menu Options

```
1. Process Order via Terminal UI
2. Batch Process Orders via JSON File
3. Register New Customer (VG)
4. Register New Product (VG)
5. Edit Product Price / Stock (VG)
6. Delete Product (VG)
7. Terminate System Operations
```

---

## 🔒 Security Considerations

- All API endpoints (except `/health`) are protected with an API key sent via the `X-API-Key` HTTP header.
- Customer addresses and discount percentages are masked in the web UI to protect sensitive business data.
- In a production environment, the API key would be stored in environment variables (not hardcoded), and HTTPS/TLS would be enforced.
- Customer records are never deleted via the API — deleting a customer would break historical order records. This follows standard ERP practice.

---

## ⚠️ Known Limitations

- Data is stored in CSV and JSON files instead of a proper database. In production, PostgreSQL or SQLite with SQLAlchemy would be used.
- No real-time synchronization between the terminal app and the API server — last write wins if both run simultaneously.
- API key is hardcoded for simplicity — production systems use environment variables or secret managers.

---

## 📚 Tech Stack

| Technology | Purpose |
|-----------|---------|
| Python 3.11+ | Core language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| Pydantic | Request validation |
| PowerShell | REST client scripting |
| CSV / JSON | Lightweight data persistence |
| HTML / CSS / JS | Web dashboard frontend |