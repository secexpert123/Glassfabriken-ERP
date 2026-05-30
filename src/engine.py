from src.models import Customer, Product, Order, OrderLine

class ERPEngine:
    def __init__(self, repository):
        self.repository = repository

    @property
    def customers(self): return self.repository.load_customers()
    @property
    def products(self): return self.repository.load_products()

    def find_and_validate_customer(self, identifier: str):
        c_list = self.customers
        if identifier in c_list: return c_list[identifier]
        for cust in c_list.values():
            if cust.name.lower() == identifier.lower(): return cust
        raise ValueError(f"Customer '{identifier}' not found.")

    def calculate_order(self, customer_id: str, lines: list):
        cust = self.find_and_validate_customer(customer_id)
        prods = self.products
        subtotal = 0.0
        for l in lines:
            sku = l['sku']
            qty = l['qty']
            if sku in prods:
                subtotal += (prods[sku].price_sek * qty)
        discount = subtotal * (cust.discount_pct / 100)
        return {
            "customer": cust.name, "address": cust.address,
            "discount_pct": cust.discount_pct, "subtotal": subtotal,
            "discount_amount": discount, "total": subtotal - discount
        }

    def process_order_pipeline(self, customer_id: str, lines: list):
        cust = self.find_and_validate_customer(customer_id)
        prods = self.products

        # Validate SKUs and check stock BEFORE saving anything
        for l in lines:
            sku = l['sku']
            qty = l['qty']
            if sku not in prods:
                raise ValueError(f"SKU '{sku}' not found.")
            prods[sku].reduce_stock(qty)  # raises ValueError if stock too low

        # Persist deducted stock
        self.repository.save_all_products(prods)

        # Build and save the order
        order_lines = [OrderLine(l['sku'], l['qty']) for l in lines]
        order_id = f"ORD-{len(self.repository.load_orders()) + 1}"
        order = Order(order_id, cust.customer_id, order_lines)
        self.repository.save_order(order)
        return order

    def add_new_customer_master_data(self, cid, name, addr, disc):
        self.repository.save_customer_dict({"customer_id": cid, "name": name, "address": addr, "discount_pct": disc})

    def add_new_product_master_data(self, sku, name, stock, price):
        prods = self.products
        prods[sku] = Product(sku, name, stock, price)
        self.repository.save_all_products(prods)

    def edit_product(self, sku: str, new_price: float = None, new_stock: int = None):
        """Update price and/or stock for an existing product."""
        prods = self.products
        if sku not in prods:
            raise ValueError(f"Product SKU '{sku}' not found.")
        if new_price is not None:
            prods[sku].price_sek = new_price
        if new_stock is not None:
            prods[sku].stock = new_stock
        self.repository.save_all_products(prods)
        return prods[sku]

    def delete_product(self, sku: str):
        """Remove a product from the catalog permanently."""
        prods = self.products
        if sku not in prods:
            raise ValueError(f"Product SKU '{sku}' not found.")
        name = prods[sku].name
        del prods[sku]
        self.repository.save_all_products(prods)
        return name