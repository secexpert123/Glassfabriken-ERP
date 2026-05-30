"""
run_tests.py — Glassfabriken ERP Full QA Test Suite
=====================================================
Covers both:
  1. Unit tests  — engine + repository (no server needed)
  2. API tests   — live HTTP endpoint tests (server must be running)

Usage:
  python run_tests.py          # runs all tests
  python run_tests.py --unit   # unit tests only
  python run_tests.py --api    # API tests only
"""
import sys
import time
import json
from pathlib import Path

# ── Setup path so src imports work ────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent))
from src.repository import ERPRepository
from src.engine import ERPEngine

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE    = "http://192.176.243.141:8003"
API_KEY     = "glassfabriken-secret-2025"
API_HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# ── Counters ──────────────────────────────────────────────────────────────────
passed = 0
failed = 0
skipped = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{'='*58}")
    print(f"  {title}")
    print(f"{'='*58}")

def ok(msg):
    global passed
    passed += 1
    print(f"  ✅ PASS — {msg}")

def fail(msg, error=""):
    global failed
    failed += 1
    err = f" ({error})" if error else ""
    print(f"  ❌ FAIL — {msg}{err}")

def skip(msg):
    global skipped
    skipped += 1
    print(f"  ⏭️  SKIP — {msg}")

def assert_equal(actual, expected, label):
    if actual == expected:
        ok(f"{label}: got {actual!r}")
    else:
        fail(f"{label}: expected {expected!r}, got {actual!r}")

def assert_true(condition, label):
    if condition:
        ok(label)
    else:
        fail(label)

def assert_raises(func, label):
    try:
        func()
        fail(f"{label} — expected exception but none raised")
    except Exception:
        ok(label)


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — UNIT TESTS (engine + repository, no server needed)
# ══════════════════════════════════════════════════════════════════════════════

def run_unit_tests():
    section("PART 1 — UNIT TESTS (Engine + Repository)")

    engine = ERPEngine(ERPRepository(Path(".")))

    # ── 1.1 Load Products ─────────────────────────────────────────────────────
    print("\n  [1.1] Product Loading")
    try:
        products = engine.products
        assert_true(len(products) > 0, f"Products loaded — found {len(products)} items")
        assert_true(all(hasattr(p, 'sku') for p in products.values()), "All products have SKU")
        assert_true(all(hasattr(p, 'price_sek') for p in products.values()), "All products have price_sek")
        assert_true(all(p.price_sek >= 0 for p in products.values()), "All prices are non-negative")
        assert_true(all(p.stock >= 0 for p in products.values()), "All stock values are non-negative")
    except Exception as e:
        fail("Product loading", str(e))

    # ── 1.2 Load Customers ────────────────────────────────────────────────────
    print("\n  [1.2] Customer Loading")
    try:
        customers = engine.customers
        assert_true(len(customers) > 0, f"Customers loaded — found {len(customers)} items")
        assert_true(all(hasattr(c, 'customer_id') for c in customers.values()), "All customers have customer_id")
        assert_true(all(0 <= c.discount_pct <= 100 for c in customers.values()), "All discounts are 0-100%")
    except Exception as e:
        fail("Customer loading", str(e))

    # ── 1.3 Customer Validation ───────────────────────────────────────────────
    print("\n  [1.3] Customer Validation")
    try:
        customers = engine.customers
        first_id = list(customers.keys())[0]
        first_name = customers[first_id].name

        # Valid lookup by ID
        c = engine.find_and_validate_customer(first_id)
        assert_equal(c.customer_id, first_id, "Lookup by ID")

        # Valid lookup by name
        c2 = engine.find_and_validate_customer(first_name)
        assert_equal(c2.name, first_name, "Lookup by name")

        # Invalid customer raises ValueError
        assert_raises(
            lambda: engine.find_and_validate_customer("INVALID-CUSTOMER-XYZ"),
            "Invalid customer raises ValueError"
        )
    except Exception as e:
        fail("Customer validation", str(e))

    # ── 1.4 Order Calculation ─────────────────────────────────────────────────
    print("\n  [1.4] Order Calculation")
    try:
        customers = engine.customers
        products  = engine.products
        if customers and products:
            cid  = list(customers.keys())[0]
            sku  = list(products.keys())[0]
            cust = customers[cid]
            prod = products[sku]

            result = engine.calculate_order(cid, [{"sku": sku, "qty": 2}])

            expected_subtotal  = prod.price_sek * 2
            expected_discount  = expected_subtotal * (cust.discount_pct / 100)
            expected_total     = expected_subtotal - expected_discount

            assert_equal(round(result["subtotal"], 2), round(expected_subtotal, 2), "Subtotal calculation")
            assert_equal(round(result["discount_amount"], 2), round(expected_discount, 2), "Discount calculation")
            assert_equal(round(result["total"], 2), round(expected_total, 2), "Total calculation")
        else:
            skip("Order calculation — no data available")
    except Exception as e:
        fail("Order calculation", str(e))

    # ── 1.5 Stock Protection ──────────────────────────────────────────────────
    print("\n  [1.5] Stock Over-Allocation Protection")
    try:
        customers = engine.customers
        products  = engine.products
        if customers and products:
            cid = list(customers.keys())[0]
            sku = list(products.keys())[0]
            assert_raises(
                lambda: engine.process_order_pipeline(cid, [{"sku": sku, "qty": 999999}]),
                "Excessive order correctly rejected"
            )
        else:
            skip("Stock protection — no data available")
    except Exception as e:
        fail("Stock protection", str(e))

    # ── 1.6 Add New Customer ──────────────────────────────────────────────────
    print("\n  [1.6] Customer Registration")
    test_cid = "C-AUTOTEST-001"
    try:
        customers_before = engine.customers
        if test_cid not in customers_before:
            engine.add_new_customer_master_data(test_cid, "Auto Test Customer", "Test St 1", 5)
        customers_after = engine.customers
        assert_true(test_cid in customers_after, f"Customer {test_cid} registered successfully")
    except Exception as e:
        fail("Customer registration", str(e))

    # ── 1.7 Add New Product ───────────────────────────────────────────────────
    print("\n  [1.7] Product Registration")
    test_sku = "AUTO-TEST-SKU"
    try:
        products_before = engine.products
        if test_sku not in products_before:
            engine.add_new_product_master_data(test_sku, "Auto Test Product", 100, 9.99)
        products_after = engine.products
        assert_true(test_sku in products_after, f"Product {test_sku} registered successfully")
        assert_equal(products_after[test_sku].price_sek, 9.99, "Price saved correctly")
        assert_equal(products_after[test_sku].stock, 100, "Stock saved correctly")
    except Exception as e:
        fail("Product registration", str(e))

    # ── 1.8 Edit Product ──────────────────────────────────────────────────────
    print("\n  [1.8] Product Edit")
    try:
        products = engine.products
        if test_sku in products:
            engine.edit_product(test_sku, new_price=19.99, new_stock=50)
            updated = engine.products[test_sku]
            assert_equal(updated.price_sek, 19.99, "Price updated correctly")
            assert_equal(updated.stock, 50, "Stock updated correctly")
        else:
            skip("Product edit — test SKU not found")
    except Exception as e:
        fail("Product edit", str(e))

    # ── 1.9 Delete Product ────────────────────────────────────────────────────
    print("\n  [1.9] Product Delete")
    try:
        products = engine.products
        if test_sku in products:
            engine.delete_product(test_sku)
            products_after = engine.products
            assert_true(test_sku not in products_after, f"Product {test_sku} deleted successfully")
        else:
            skip("Product delete — test SKU not found")
    except Exception as e:
        fail("Product delete", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — API TESTS (live HTTP endpoint tests)
# ══════════════════════════════════════════════════════════════════════════════

def run_api_tests():
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        fail("urllib not available")
        return

    section("PART 2 — API TESTS (Live HTTP Endpoints)")

    def api_get(path):
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            headers=API_HEADERS
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read()), res.status

    def api_post(path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=body,
            headers=API_HEADERS,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return json.loads(res.read()), res.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read()), e.code

    def api_put(path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=body,
            headers=API_HEADERS,
            method="PUT"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return json.loads(res.read()), res.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read()), e.code

    def api_patch(path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=body,
            headers=API_HEADERS,
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return json.loads(res.read()), res.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read()), e.code

    def api_delete(path):
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            headers=API_HEADERS,
            method="DELETE"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return json.loads(res.read()), res.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read()), e.code

    # ── Check server is reachable ─────────────────────────────────────────────
    print("\n  [2.0] Server Connectivity")
    try:
        req = urllib.request.Request(f"{API_BASE}/health")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            assert_equal(data.get("status"), "ok", "Health check")
    except Exception as e:
        fail("Server not reachable — make sure uvicorn is running", str(e))
        print("\n  ⚠️  Skipping all API tests — server offline.\n")
        return

    # ── 2.1 GET Products ──────────────────────────────────────────────────────
    print("\n  [2.1] GET /products")
    try:
        data, status = api_get("/products")
        assert_equal(status, 200, "Status code")
        assert_true(isinstance(data, list), "Returns a list")
        assert_true(len(data) > 0, f"Found {len(data)} products")
    except Exception as e:
        fail("GET /products", str(e))

    # ── 2.2 GET Single Product ────────────────────────────────────────────────
    print("\n  [2.2] GET /products/{sku}")
    try:
        data, status = api_get("/products/10001")
        assert_equal(status, 200, "Status code")
        assert_true("sku" in data, "Response has SKU field")
        assert_true("price_sek" in data, "Response has price_sek field")
    except Exception as e:
        fail("GET /products/10001", str(e))

    # ── 2.3 POST Create Product ───────────────────────────────────────────────
    print("\n  [2.3] POST /products")
    test_sku = "API-TEST-001"
    try:
        # Delete first in case it exists from previous run
        api_delete(f"/products/{test_sku}")
        data, status = api_post("/products", {
            "sku": test_sku, "name": "API Test Product",
            "stock": 25, "price_sek": 15.99
        })
        assert_equal(status, 201, "Status code 201 Created")
        assert_equal(data.get("status"), "created", "Response status")
        assert_equal(data.get("sku"), test_sku, "SKU in response")
    except Exception as e:
        fail("POST /products", str(e))

    # ── 2.4 PUT Update Product ────────────────────────────────────────────────
    print("\n  [2.4] PUT /products/{sku}")
    try:
        data, status = api_put(f"/products/{test_sku}", {
            "price_sek": 29.99, "stock": 50
        })
        assert_equal(status, 200, "Status code")
        assert_equal(data.get("price_sek"), 29.99, "Price updated")
        assert_equal(data.get("stock"), 50, "Stock updated")
    except Exception as e:
        fail("PUT /products", str(e))

    # ── 2.5 PATCH Partial Update ──────────────────────────────────────────────
    print("\n  [2.5] PATCH /products/{sku}")
    try:
        data, status = api_patch(f"/products/{test_sku}", {"price_sek": 9.99})
        assert_equal(status, 200, "Status code")
        assert_equal(data.get("price_sek"), 9.99, "Price patched")
        assert_equal(data.get("stock"), 50, "Stock unchanged after PATCH")
    except Exception as e:
        fail("PATCH /products", str(e))

    # ── 2.6 GET Customers ─────────────────────────────────────────────────────
    print("\n  [2.6] GET /customers")
    try:
        data, status = api_get("/customers")
        assert_equal(status, 200, "Status code")
        assert_true(isinstance(data, list), "Returns a list")
        assert_true(len(data) > 0, f"Found {len(data)} customers")
    except Exception as e:
        fail("GET /customers", str(e))

    # ── 2.7 POST Register Customer ────────────────────────────────────────────
    print("\n  [2.7] POST /customers")
    test_cid = "API-TEST-CUST"
    try:
        data, status = api_post("/customers", {
            "customer_id": test_cid,
            "name": "API Test Customer",
            "address": "Testgatan 1",
            "discount_pct": 10
        })
        if status == 409:
            ok("Customer already exists — duplicate protection working")
        else:
            assert_equal(status, 201, "Status code 201 Created")
            assert_equal(data.get("status"), "created", "Response status")
    except Exception as e:
        fail("POST /customers", str(e))

    # ── 2.8 POST Calculate Order ──────────────────────────────────────────────
    print("\n  [2.8] POST /calculate-order")
    try:
        data, status = api_post("/calculate-order", {
            "customer_id": "C1001",
            "lines": [{"sku": "10001", "qty": 2}]
        })
        assert_equal(status, 200, "Status code")
        assert_true("subtotal" in data, "Response has subtotal")
        assert_true("total" in data, "Response has total")
        assert_true("discount_amount" in data, "Response has discount_amount")
        assert_true(data["total"] <= data["subtotal"], "Total <= subtotal (discount applied)")
    except Exception as e:
        fail("POST /calculate-order", str(e))

    # ── 2.9 POST Place Order ──────────────────────────────────────────────────
    print("\n  [2.9] POST /orders")
    try:
        data, status = api_post("/orders", {
            "customer_id": "C1001",
            "lines": [{"sku": "10001", "qty": 1}]
        })
        assert_equal(status, 201, "Status code 201 Created")
        assert_true("order_id" in data, "Response has order_id")
        assert_true(data["order_id"].startswith("ORD-"), "Order ID has correct format")
    except Exception as e:
        fail("POST /orders", str(e))

    # ── 2.10 API Key Protection ───────────────────────────────────────────────
    print("\n  [2.10] API Key Security")
    try:
        req = urllib.request.Request(f"{API_BASE}/products")
        # No API key header — should get 403
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                fail("Endpoint should require API key but returned 200")
        except urllib.error.HTTPError as e:
            assert_equal(e.code, 403, "Blocked without API key (403 Forbidden)")
    except Exception as e:
        fail("API key security test", str(e))

    # ── 2.11 404 Not Found ────────────────────────────────────────────────────
    print("\n  [2.11] 404 Not Found")
    try:
        req = urllib.request.Request(
            f"{API_BASE}/products/NONEXISTENT-SKU-XYZ",
            headers=API_HEADERS
        )
        try:
            with urllib.request.urlopen(req, timeout=5):
                fail("Should return 404 for missing product")
        except urllib.error.HTTPError as e:
            assert_equal(e.code, 404, "Returns 404 for missing SKU")
    except Exception as e:
        fail("404 test", str(e))

    # ── 2.12 Cleanup — Delete test product ───────────────────────────────────
    print("\n  [2.12] Cleanup")
    try:
        data, status = api_delete(f"/products/{test_sku}")
        assert_equal(data.get("status"), "deleted", f"Test product {test_sku} cleaned up")
    except Exception as e:
        fail("Cleanup", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Run selected tests and print summary
# ══════════════════════════════════════════════════════════════════════════════

def print_summary():
    total = passed + failed + skipped
    print(f"\n{'='*58}")
    print(f"  QA SUITE COMPLETE")
    print(f"{'='*58}")
    print(f"  ✅ Passed  : {passed}")
    print(f"  ❌ Failed  : {failed}")
    print(f"  ⏭️  Skipped : {skipped}")
    print(f"  📊 Total   : {total}")
    if failed == 0:
        print(f"\n  🎉 ALL TESTS PASSED — System is nominal!")
    else:
        print(f"\n  ⚠️  {failed} test(s) failed — check output above.")
    print(f"{'='*58}\n")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

    print("\n" + "="*58)
    print("  GLASSFABRIKEN ERP — FULL QA TEST SUITE")
    print("="*58)

    start = time.time()

    if mode in ("--all", "--unit"):
        run_unit_tests()

    if mode in ("--all", "--api"):
        run_api_tests()

    elapsed = time.time() - start
    print(f"\n  ⏱️  Completed in {elapsed:.2f}s")
    print_summary()