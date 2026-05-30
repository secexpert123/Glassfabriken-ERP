# =============================================================================
# server.py — Glassfabriken ERP REST API Server
# Built with FastAPI — a modern, fast Python web framework for building APIs.
# This file is the main entry point for the HTTP server that exposes our
# ERP business logic over a REST API with JSON responses.
# =============================================================================

# FastAPI is the web framework — HTTPException lets us return proper error codes
from fastapi import FastAPI, HTTPException, Security, Depends

# StaticFiles lets us serve our HTML frontend from the same server
from fastapi.staticfiles import StaticFiles

# CORSMiddleware allows our HTML page (running in browser) to call this API
# Without CORS, the browser would block the requests for security reasons
from fastapi.middleware.cors import CORSMiddleware

# APIKeyHeader extracts the API key from incoming request headers
from fastapi.security.api_key import APIKeyHeader

# BaseModel is the base class for Pydantic data validation models
# Field lets us add constraints, examples, and descriptions to each field
from pydantic import BaseModel, Field

# Optional means a field is not required — used for PATCH/PUT partial updates
from typing import Optional

# Path helps us build file system paths in a cross-platform way (Windows/Linux)
from pathlib import Path

# Our own classes — Repository handles file I/O, Engine handles business logic
from src.repository import ERPRepository
from src.engine import ERPEngine

# uvicorn is the ASGI server that actually runs our FastAPI application
import uvicorn


# =============================================================================
# API KEY SECURITY
# We use a simple API key to protect our endpoints when deployed on a server.
# The key must be sent in the request header as: X-API-Key: <key>
# In production, this would be stored in environment variables, not hardcoded.
# =============================================================================

# This is our secret API key — clients must send this to access protected routes
API_KEY = "glassfabriken-secret-2025"

# APIKeyHeader tells FastAPI to look for the key in the HTTP header "X-API-Key"
# auto_error=False means we handle the error ourselves with a custom message
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(key: str = Security(api_key_header)):
    """
    Dependency function — FastAPI runs this before any protected endpoint.
    If the key is wrong or missing, it returns HTTP 403 Forbidden.
    If the key is correct, the request is allowed through.
    """
    if key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key. Include header: X-API-Key: glassfabriken-secret-2025"
        )
    return key


# =============================================================================
# FASTAPI APPLICATION INSTANCE
# We create one FastAPI app object and configure it with metadata.
# This metadata appears in the auto-generated Swagger UI at /docs
# =============================================================================

app = FastAPI(
    title="Glassfabriken ERP API",
    description="REST API for the Glassfabriken ice cream factory ERP system. "
                "Implements full CRUD operations for products, customers and orders. "
                "Protected endpoints require X-API-Key header.",
    version="1.0.0"
)

# =============================================================================
# CORS MIDDLEWARE
# CORS = Cross-Origin Resource Sharing.
# We add this so our index.html (served from the browser) can call the API.
# Without this, browsers block requests between different origins for security.
# allow_origins=["*"] means any origin is allowed — fine for local development.
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Allow all origins (restrict this in production)
    allow_methods=["*"],    # Allow GET, POST, PUT, PATCH, DELETE etc.
    allow_headers=["*"],    # Allow all headers including X-API-Key
)


# =============================================================================
# REPOSITORY AND ENGINE SETUP
# Repository handles all file I/O (reading/writing CSV and JSON files).
# Engine contains the business logic (validation, order processing etc.).
# We pass the project root path so the repository can find the data/ folder.
# =============================================================================

# __file__ is the path to this file (server.py inside src/)
# .parent goes up to src/, .parent again goes up to project root
repo = ERPRepository(Path(__file__).resolve().parent.parent)
engine = ERPEngine(repo)


# =============================================================================
# PYDANTIC MODELS — REQUEST VALIDATION
# Pydantic models define the shape and rules for incoming JSON data.
# FastAPI uses these to automatically validate requests and show examples in /docs.
# If a request does not match the model, FastAPI returns HTTP 422 automatically.
# =============================================================================

class ProductCreate(BaseModel):
    """Model for creating a new product — all fields are required."""
    sku: str = Field(..., example="10004", description="Unique product identifier")
    name: str = Field(..., example="Paronglass", description="Product display name")
    stock: int = Field(..., ge=0, example=50, description="Initial warehouse stock. Must be >= 0")
    price_sek: float = Field(..., ge=0.0, example=22.50, description="Unit price in SEK. Must be >= 0")

class ProductUpdate(BaseModel):
    """
    Model for updating a product — all fields are Optional.
    This means the client can send just the fields they want to change.
    Used by both PUT (full update intent) and PATCH (explicit partial update).
    """
    name: Optional[str] = Field(None, example="Paronglass Premium")
    stock: Optional[int] = Field(None, ge=0, example=75)
    price_sek: Optional[float] = Field(None, ge=0.0, example=24.99)

class CustomerCreate(BaseModel):
    """Model for registering a new customer — all fields are required."""
    customer_id: str = Field(..., example="C1004", description="Unique customer ID")
    name: str = Field(..., example="Delta Livsmedel", description="Company or person name")
    address: str = Field(..., example="Deltavagen 4", description="Shipping address")
    discount_pct: int = Field(..., ge=0, le=100, example=10, description="Discount percentage 0-100")

class OrderLineIn(BaseModel):
    """Represents one line in an order — which product and how many."""
    sku: str = Field(..., example="10001", description="Product SKU to order")
    qty: int = Field(..., gt=0, example=3, description="Quantity to order. Must be > 0")

class OrderRequest(BaseModel):
    """Full order request — a customer ID and one or more order lines."""
    customer_id: str = Field(..., example="C1001", description="The customer placing the order")
    lines: list[OrderLineIn]   # A list of products and quantities


# =============================================================================
# HEALTH CHECK ENDPOINT
# This endpoint is public (no API key needed) so monitoring tools and the
# HTML frontend can always check if the server is running.
# Returns HTTP 200 with {"status": "ok"} when the server is alive.
# =============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """Public endpoint — confirms the server is running. No API key required."""
    return {"status": "ok"}


# =============================================================================
# PRODUCT ENDPOINTS — Full CRUD
# CRUD = Create, Read, Update, Delete — the four basic data operations.
# We implement all HTTP methods: GET, POST, PUT, PATCH, DELETE
# All product endpoints are protected with the API key dependency.
# =============================================================================

@app.get("/products", tags=["Products"], dependencies=[Depends(verify_api_key)])
def get_products():
    """
    GET /products — Read all products.
    Loads the full product catalog from products.csv and returns as JSON list.
    HTTP 200 on success.
    """
    return list(engine.products.values())


@app.get("/products/{sku}", tags=["Products"], dependencies=[Depends(verify_api_key)])
def get_product(sku: str):
    """
    GET /products/{sku} — Read one product by SKU.
    Returns HTTP 404 if the SKU does not exist in the catalog.
    """
    products = engine.products
    if sku not in products:
        # HTTP 404 = Not Found — standard REST response for missing resources
        raise HTTPException(status_code=404, detail=f"Product '{sku}' not found.")
    return products[sku]


@app.post("/products", status_code=201, tags=["Products"], dependencies=[Depends(verify_api_key)])
def add_product(payload: ProductCreate):
    """
    POST /products — Create a new product.
    Validates the payload with ProductCreate model, then saves to products.csv.
    Returns HTTP 201 Created on success.
    Returns HTTP 409 Conflict if the SKU already exists.
    """
    products = engine.products
    if payload.sku in products:
        # HTTP 409 = Conflict — the resource already exists
        raise HTTPException(status_code=409, detail=f"Product SKU '{payload.sku}' already exists.")
    try:
        engine.add_new_product_master_data(
            payload.sku, payload.name, payload.stock, payload.price_sek
        )
        return {"status": "created", "sku": payload.sku}
    except Exception as e:
        # HTTP 500 = Internal Server Error — something unexpected went wrong
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/products/{sku}", tags=["Products"], dependencies=[Depends(verify_api_key)])
def update_product(sku: str, payload: ProductUpdate):
    """
    PUT /products/{sku} — Full update of a product.
    REST convention: PUT means replace/update the full resource.
    Only the fields provided in the payload are changed.
    Persists changes back to products.csv.
    Returns HTTP 404 if SKU not found.
    """
    products = engine.products
    if sku not in products:
        raise HTTPException(status_code=404, detail=f"Product '{sku}' not found.")

    product = products[sku]

    # Only update fields that were actually sent in the request
    # None means the field was not included in the request body
    if payload.name is not None:
        product.name = payload.name
    if payload.stock is not None:
        product.stock = payload.stock
    if payload.price_sek is not None:
        product.price_sek = payload.price_sek

    # Write the updated catalog back to the CSV file
    engine.repository.save_all_products(products)

    return {
        "status": "updated",
        "sku": product.sku,
        "name": product.name,
        "stock": product.stock,
        "price_sek": product.price_sek
    }


@app.patch("/products/{sku}", tags=["Products"], dependencies=[Depends(verify_api_key)])
def patch_product(sku: str, payload: ProductUpdate):
    """
    PATCH /products/{sku} — Partial update of a product.
    REST convention: PATCH means update only the fields you send.
    Difference from PUT: PATCH is more explicit about partial intent.
    Example: send only {"price_sek": 19.99} to update just the price.
    """
    products = engine.products
    if sku not in products:
        raise HTTPException(status_code=404, detail=f"Product '{sku}' not found.")

    product = products[sku]

    # Apply only the fields the caller supplied — rest stays unchanged
    if payload.name is not None:
        product.name = payload.name
    if payload.stock is not None:
        product.stock = payload.stock
    if payload.price_sek is not None:
        product.price_sek = payload.price_sek

    # Persist changes to CSV
    engine.repository.save_all_products(products)

    return {
        "status": "patched",
        "sku": product.sku,
        "name": product.name,
        "stock": product.stock,
        "price_sek": product.price_sek
    }


@app.delete("/products/{sku}", tags=["Products"], dependencies=[Depends(verify_api_key)])
def delete_product(sku: str):
    """
    DELETE /products/{sku} — Remove a product from the catalog.
    Permanently deletes the product and saves the updated catalog to CSV.
    Returns HTTP 404 if the SKU does not exist.
    In a production ERP we would use soft-delete (mark as discontinued)
    to preserve order history — here we do a hard delete for simplicity.
    """
    products = engine.products
    if sku not in products:
        raise HTTPException(status_code=404, detail=f"Product '{sku}' not found.")

    # Remove the product from the dictionary
    del products[sku]

    # Save the updated product list back to CSV
    engine.repository.save_all_products(products)

    return {"status": "deleted", "sku": sku}


# =============================================================================
# CUSTOMER ENDPOINTS
# Customers are protected with API key.
# We support GET (list all) and POST (register new).
# We do NOT support DELETE for customers because deleting a customer would
# break historical order records — this is standard ERP practice.
# =============================================================================

@app.get("/customers", tags=["Customers"], dependencies=[Depends(verify_api_key)])
def get_customers():
    """
    GET /customers — Return all registered customers.
    Loads from customers.csv via the repository layer.
    """
    return list(engine.customers.values())


@app.post("/customers", status_code=201, tags=["Customers"], dependencies=[Depends(verify_api_key)])
def add_customer(payload: CustomerCreate):
    """
    POST /customers — Register a new customer.
    Validates discount_pct is between 0-100 via Pydantic.
    Returns HTTP 409 if the customer ID already exists.
    Appends the new customer to customers.csv.
    """
    if payload.customer_id in engine.customers:
        raise HTTPException(status_code=409, detail=f"Customer '{payload.customer_id}' already exists.")

    engine.add_new_customer_master_data(
        payload.customer_id, payload.name, payload.address, payload.discount_pct
    )
    return {"status": "created", "customer_id": payload.customer_id}


# =============================================================================
# ORDER ENDPOINTS
# Two endpoints: one for previewing an order, one for placing it.
# calculate-order: shows totals and discount WITHOUT saving — good for UX
# orders: actually places the order, deducts stock, and saves to orders.json
# =============================================================================

@app.post("/calculate-order", tags=["Orders"], dependencies=[Depends(verify_api_key)])
def calculate_order(payload: OrderRequest):
    """
    POST /calculate-order — Preview order totals without placing the order.
    Useful for showing the customer the total before they confirm.
    Does NOT deduct stock or save anything.
    Returns subtotal, discount amount, and total payable.
    """
    try:
        # Convert Pydantic models to plain dicts for the engine
        lines = [{"sku": l.sku, "qty": l.qty} for l in payload.lines]
        return engine.calculate_order(payload.customer_id, lines)
    except Exception as e:
        # HTTP 400 = Bad Request — invalid customer or product
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/orders", status_code=201, tags=["Orders"], dependencies=[Depends(verify_api_key)])
def place_order(payload: OrderRequest):
    """
    POST /orders — Place a real order.
    Validates customer exists, validates all SKUs exist,
    deducts stock from products.csv, and saves order to orders.json.
    Returns the generated order ID (e.g. ORD-5).
    Returns HTTP 400 if customer not found or insufficient stock.
    """
    try:
        lines = [{"sku": l.sku, "qty": l.qty} for l in payload.lines]
        order = engine.process_order_pipeline(payload.customer_id, lines)
        return {"status": "created", "order_id": order.order_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# STATIC FRONTEND
# This mounts our index.html as a static web page served from the same server.
# IMPORTANT: This must always be LAST — if mounted first, it would intercept
# all API routes before they can be matched by FastAPI.
# Access the frontend at: http://127.0.0.1:8003/
# Access the API docs at: http://127.0.0.1:8003/docs
# =============================================================================

app.mount("/", StaticFiles(directory=".", html=True), name="static")


# =============================================================================
# ENTRY POINT
# When running this file directly with python src/server.py, uvicorn starts.
# The preferred way is: python -m uvicorn src.server:app --port 8003 --reload
# --reload means the server restarts automatically when code changes are saved.
# =============================================================================

if __name__ == "__main__":
    uvicorn.run("src.server:app", host="127.0.0.1", port=8003, reload=True)