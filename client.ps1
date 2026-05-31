# =============================================================================
#  Glassfabriken ERP — PowerShell REST Client
#  Calls the FastAPI server running on http://127.0.0.1:8003
#  All protected endpoints require the X-API-Key header.
#  Usage: .\client.ps1
# =============================================================================

$base = "http://127.0.0.1:8003"

# API key — must match the key defined in server.py
$headers = @{"X-API-Key" = "glassfabriken-secret-2025"}

function Write-Header($title) {
    Write-Host "`n$('='*55)" -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "$('='*55)" -ForegroundColor Cyan
}
function Write-Ok($msg)   { Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "➡  $msg" -ForegroundColor Yellow }


# -----------------------------------------------------------------------------
# 1. HEALTH CHECK — public endpoint, no API key needed
# -----------------------------------------------------------------------------
Write-Header "1. Health Check"
try {
    $health = Invoke-RestMethod "$base/health" -Method GET
    Write-Ok "Server is running — status: $($health.status)"
} catch {
    Write-Err "Server not reachable. Make sure uvicorn is running on port 8003."
    exit
}


# -----------------------------------------------------------------------------
# 2. GET ALL PRODUCTS
# -----------------------------------------------------------------------------
Write-Header "2. GET All Products"
try {
    $products = Invoke-RestMethod "$base/products" -Method GET -Headers $headers
    Write-Ok "Found $($products.Count) products:"
    $products | Format-Table sku, name, stock, price_sek -AutoSize
} catch {
    Write-Err "Could not fetch products: $_"
}


# -----------------------------------------------------------------------------
# 3. GET ONE PRODUCT BY SKU
# -----------------------------------------------------------------------------
Write-Header "3. GET Single Product (SKU: 10001)"
try {
    $product = Invoke-RestMethod "$base/products/10001" -Method GET -Headers $headers
    Write-Ok "Product found:"
    $product | Format-List
} catch {
    Write-Err "Could not fetch product 10001: $_"
}


# -----------------------------------------------------------------------------
# 4. POST — CREATE A NEW PRODUCT
# -----------------------------------------------------------------------------
Write-Header "4. POST — Create New Product"
$newProduct = @{
    sku       = "10099"
    name      = "PowerShell Parfait"
    stock     = 42
    price_sek = 34.50
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod "$base/products" -Method POST -Headers $headers -Body $newProduct -ContentType "application/json"
    Write-Ok "Product created — SKU: $($result.sku), Status: $($result.status)"
} catch {
    Write-Err "Could not create product (may already exist): $_"
}


# -----------------------------------------------------------------------------
# 5. PUT — FULL UPDATE PRODUCT
# -----------------------------------------------------------------------------
Write-Header "5. PUT — Update Product 10099 (price + stock)"
$updateData = @{
    price_sek = 39.99
    stock     = 100
} | ConvertTo-Json

try {
    $updated = Invoke-RestMethod "$base/products/10099" -Method PUT -Headers $headers -Body $updateData -ContentType "application/json"
    Write-Ok "Product updated:"
    Write-Info "  Name      : $($updated.name)"
    Write-Info "  New Price : $($updated.price_sek) SEK"
    Write-Info "  New Stock : $($updated.stock) units"
} catch {
    Write-Err "Could not update product 10099: $_"
}


# -----------------------------------------------------------------------------
# 6. PATCH — PARTIAL UPDATE (price only)
# -----------------------------------------------------------------------------
Write-Header "6. PATCH — Update Only Price of 10099"
$patchData = @{ price_sek = 29.99 } | ConvertTo-Json

try {
    $patched = Invoke-RestMethod "$base/products/10099" -Method PATCH -Headers $headers -Body $patchData -ContentType "application/json"
    Write-Ok "Product patched:"
    Write-Info "  New Price : $($patched.price_sek) SEK"
    Write-Info "  Stock unchanged : $($patched.stock) units"
} catch {
    Write-Err "Could not patch product 10099: $_"
}


# -----------------------------------------------------------------------------
# 7. GET ALL CUSTOMERS
# -----------------------------------------------------------------------------
Write-Header "7. GET All Customers"
try {
    $customers = Invoke-RestMethod "$base/customers" -Method GET -Headers $headers
    Write-Ok "Found $($customers.Count) customers:"
    $customers | Format-Table customer_id, name, discount_pct -AutoSize
} catch {
    Write-Err "Could not fetch customers: $_"
}


# -----------------------------------------------------------------------------
# 8. POST — REGISTER A NEW CUSTOMER
# -----------------------------------------------------------------------------
Write-Header "8. POST — Register New Customer"
$newCustomer = @{
    customer_id  = "C9001"
    name         = "PowerShell Handels AB"
    address      = "Skriptgatan 7"
    discount_pct = 15
} | ConvertTo-Json

try {
    $custResult = Invoke-RestMethod "$base/customers" -Method POST -Headers $headers -Body $newCustomer -ContentType "application/json"
    Write-Ok "Customer registered — ID: $($custResult.customer_id), Status: $($custResult.status)"
} catch {
    Write-Err "Could not register customer (may already exist): $_"
}


# -----------------------------------------------------------------------------
# 9. POST — CALCULATE ORDER PREVIEW (no stock deducted)
# -----------------------------------------------------------------------------
Write-Header "9. POST — Calculate Order Preview"
$orderPreview = @{
    customer_id = "C1001"
    lines = @(
        @{ sku = "10001"; qty = 3 },
        @{ sku = "10002"; qty = 2 }
    )
} | ConvertTo-Json -Depth 3

try {
    $calc = Invoke-RestMethod "$base/calculate-order" -Method POST -Headers $headers -Body $orderPreview -ContentType "application/json"
    Write-Ok "Order preview for customer: $($calc.customer)"
    Write-Info "  Subtotal  : $($calc.subtotal) SEK"
    Write-Info "  Discount  : $($calc.discount_amount) SEK ($($calc.discount_pct)%)"
    Write-Info "  Total     : $($calc.total) SEK"
} catch {
    Write-Err "Could not calculate order: $_"
}


# -----------------------------------------------------------------------------
# 10. POST — PLACE A REAL ORDER (stock is deducted)
# -----------------------------------------------------------------------------
Write-Header "10. POST — Place Real Order"
$realOrder = @{
    customer_id = "C1001"
    lines = @(
        @{ sku = "10001"; qty = 1 }
    )
} | ConvertTo-Json -Depth 3

try {
    $order = Invoke-RestMethod "$base/orders" -Method POST -Headers $headers -Body $realOrder -ContentType "application/json"
    Write-Ok "Order placed! Order ID: $($order.order_id)"
} catch {
    Write-Err "Could not place order: $_"
}


# -----------------------------------------------------------------------------
# 11. DELETE — REMOVE THE TEST PRODUCT
# -----------------------------------------------------------------------------
Write-Header "11. DELETE — Remove Test Product 10099"
try {
    $deleted = Invoke-RestMethod "$base/products/10099" -Method DELETE -Headers $headers
    Write-Ok "Product deleted — SKU: $($deleted.sku), Status: $($deleted.status)"
} catch {
    Write-Err "Could not delete product 10099: $_"
}


# -----------------------------------------------------------------------------
# DONE
# -----------------------------------------------------------------------------
Write-Host "`n$('='*55)" -ForegroundColor Cyan
Write-Host "  All API tests completed!" -ForegroundColor Cyan
Write-Host "$('='*55)`n" -ForegroundColor Cyan