import sys
from pathlib import Path
from src.repository import ERPRepository
from src.engine import ERPEngine

def get_input(prompt: str, cast_type=str, condition=lambda x: True, error_msg="Invalid input."):
    """Reusable micro-utility to handle input collection, casting, and validation."""
    while True:
        try:
            val = cast_type(input(prompt).strip())
            if condition(val): return val
            print(f"❌ {error_msg}")
        except ValueError:
            print(f"❌ Invalid format. Expected {cast_type.__name__}.")

def print_invoice_receipt(order, engine: ERPEngine):
    """Generates a clean invoice receipt with discounts and sums."""
    cust = engine.customers[order.customer_id]
    print(f"\n{'='*48}\n       ORDER CONFIRMATION: {order.order_id}       \n{'='*48}")
    print(f"Customer Account : {cust.customer_id} - {cust.name}\nShipping Address : {cust.address}\nApplied Discount : {cust.discount_pct}%\n{'-'*48}")
    print(f"{'Item Description':<20} {'SKU':<8} {'Qty':<5} {'Gross':<10}\n{'-'*48}")
    total_gross = sum(engine.products[ln.sku].price_sek * ln.qty for ln in order.lines)
    for ln in order.lines:
        p = engine.products[ln.sku]
        print(f"{p.name:<20} {ln.sku:<8} {ln.qty:<5} {p.price_sek * ln.qty:>6.2f} SEK")
    discount = total_gross * (cust.discount_pct / 100)
    print(f"{'-'*48}\nSubtotal Gross: {total_gross:>14.2f} SEK\nDiscount:       -{discount:>14.2f} SEK\nTotal Payable:  {total_gross - discount:>14.2f} SEK\n{'='*48}\n")

def handle_interactive_order(engine: ERPEngine):
    """Collects sales orders dynamically through the terminal layout."""
    print("\n--- NEW INTERACTIVE TRANSACTION ---")
    cust_input = input("Enter Customer Name or ID: ").strip()
    try: engine.find_and_validate_customer(cust_input)
    except ValueError as e: return print(f"❌ {e}")
    raw_lines = []
    while (sku := input("Enter SKU (or hit 'Enter' to finish): ").strip()):
        if sku not in engine.products:
            print("❌ SKU not found."); continue
        qty = get_input(f"Enter quantity for '{engine.products[sku].name}': ", int, lambda x: x > 0, "Quantity must be > 0.")
        raw_lines.append({"sku": sku, "qty": qty})
    if not raw_lines: return print("⚠️ Basket is empty.")
    try: print_invoice_receipt(engine.process_order_pipeline(cust_input, raw_lines), engine)
    except ValueError as e: print(f"\n❌ TRANSACTION REJECTED:\n{e}\n")

def handle_file_order(engine: ERPEngine):
    """Processes bulk JSON batches smoothly using the core repository architecture."""
    path_str = input("Enter JSON order file path: ").strip()
    if not path_str:
        return print("⚠️ Operation canceled. No file path provided.")
    path = Path(path_str)
    if not path.exists():
        return print("❌ File path could not be resolved.")
    if path.is_dir():
        return print("❌ Target must be a specific JSON file, not a directory folder.")
    try:
        with open(path, "r", encoding="utf-8") as f:
            import json
            batch = json.load(f)
        for idx, entry in enumerate([batch] if isinstance(batch, dict) else batch, 1):
            try:
                cust_ref = entry.get("customer_id") or entry.get("customer")
                lines = [{"sku": ln["sku"], "qty": int(ln["qty"])} for ln in entry.get("lines", [])]
                print_invoice_receipt(engine.process_order_pipeline(cust_ref, lines), engine)
            except Exception as e: print(f"❌ Entry #{idx} Failed: {e}")
    except Exception as e: print(f"❌ Parsing Error: {e}")

def register_customer(engine: ERPEngine):
    """Registers a new master profile safely into database tables."""
    print("\n--- REGISTER NEW CUSTOMER ---")
    cid = input("New Customer ID: ").strip()
    name = input("Company Name: ").strip()
    addr = input("Shipping Address: ").strip()
    disc = get_input("Discount Tier % [0-100]: ", int, lambda x: 0 <= x <= 100, "Must be between 0 and 100.")
    try:
        engine.add_new_customer_master_data(cid, name, addr, disc)
        print(f"✅ Success: '{name}' registered.")
    except ValueError as e: print(f"❌ Failed: {e}")

def register_product(engine: ERPEngine):
    """Registers a new physical inventory stock unit configurations safely."""
    print("\n--- REGISTER NEW PRODUCT ---")
    sku = input("Product SKU: ").strip()
    name = input("Ice-Cream Name: ").strip()
    stock = get_input("Initial Warehouse Stock: ", int, lambda x: x >= 0, "Stock cannot be negative.")
    price = get_input("Wholesale Unit Price (SEK): ", float, lambda x: x >= 0, "Price cannot be negative.")
    try:
        engine.add_new_product_master_data(sku, name, stock, price)
        print(f"✅ Success: '{name}' added to catalog.")
    except ValueError as e: print(f"❌ Failed: {e}")

def edit_product(engine: ERPEngine):
    """Edit price and/or stock of an existing product."""
    print("\n--- EDIT PRODUCT ---")
    # Show current products so user can pick
    prods = engine.products
    if not prods:
        return print("❌ No products found.")
    print(f"\n{'SKU':<12} {'Name':<20} {'Price (SEK)':<14} {'Stock'}")
    print("-" * 55)
    for p in prods.values():
        print(f"{p.sku:<12} {p.name:<20} {p.price_sek:<14.2f} {p.stock}")
    print()

    sku = input("Enter SKU to edit: ").strip()
    if sku not in prods:
        return print(f"❌ SKU '{sku}' not found.")

    current = prods[sku]
    print(f"\nEditing: {current.name} | Current Price: {current.price_sek} SEK | Current Stock: {current.stock}")
    print("(Press Enter to keep current value)\n")

    # Price — optional
    price_input = input(f"New price [{current.price_sek}]: ").strip()
    new_price = float(price_input) if price_input else None

    # Stock — optional
    stock_input = input(f"New stock [{current.stock}]: ").strip()
    new_stock = int(stock_input) if stock_input else None

    if new_price is None and new_stock is None:
        return print("⚠️ No changes made.")

    try:
        updated = engine.edit_product(sku, new_price, new_stock)
        print(f"\n✅ Product updated successfully!")
        print(f"   {updated.name} | Price: {updated.price_sek} SEK | Stock: {updated.stock}")
    except ValueError as e:
        print(f"❌ Failed: {e}")

def delete_product(engine: ERPEngine):
    """Delete a product from the catalog."""
    print("\n--- DELETE PRODUCT ---")
    prods = engine.products
    if not prods:
        return print("❌ No products found.")

    print(f"\n{'SKU':<12} {'Name':<20} {'Price (SEK)':<14} {'Stock'}")
    print("-" * 55)
    for p in prods.values():
        print(f"{p.sku:<12} {p.name:<20} {p.price_sek:<14.2f} {p.stock}")
    print()

    sku = input("Enter SKU to delete: ").strip()
    if sku not in prods:
        return print(f"❌ SKU '{sku}' not found.")

    name = prods[sku].name
    confirm = input(f"⚠️  Are you sure you want to delete '{name}' ({sku})? (yes/no): ").strip().lower()
    if confirm != "yes":
        return print("⚠️  Deletion cancelled.")

    try:
        engine.delete_product(sku)
        print(f"✅ '{name}' has been deleted from the catalog.")
    except ValueError as e:
        print(f"❌ Failed: {e}")

def run_main_app_loop():
    """Main execution manager loop powered by a clean dictionary dispatch mechanism."""
    engine = ERPEngine(ERPRepository(Path(__file__).resolve().parent.parent))

    menu_actions = {
        "1": lambda: handle_interactive_order(engine),
        "2": lambda: handle_file_order(engine),
        "3": lambda: register_customer(engine),
        "4": lambda: register_product(engine),
        "5": lambda: edit_product(engine),
        "6": lambda: delete_product(engine),
        "7": lambda: (print("\nShutting down... Goodbye."), sys.exit(0))
    }

    while True:
        print("=" * 40 + "\n   GLASSFABRIKEN INDUSTRIAL ERP SYSTEM   \n" + "=" * 40)
        print("1. Process Order via Terminal UI")
        print("2. Batch Process Orders via JSON File")
        print("3. Register New Customer (VG)")
        print("4. Register New Product (VG)")
        print("5. Edit Product Price / Stock (VG)")
        print("6. Delete Product (VG)")
        print("7. Terminate System Operations")
        print("-" * 40)

        choice = input("Select operation [1-7]: ").strip()
        if choice in menu_actions:
            menu_actions[choice]()
        else:
            print("❌ Invalid selection. Try again.")

if __name__ == "__main__":
    run_main_app_loop()