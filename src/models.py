from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Customer:
    customer_id: str
    name: str
    address: str
    discount_pct: int
    email: str = ""
    phone: str = ""
    loyalty_points: int = 0

@dataclass
class Product:
    sku: str
    name: str
    stock: int
    price_sek: float

    def has_sufficient_stock(self, quantity: int) -> bool:
        return self.stock >= quantity

    def reduce_stock(self, quantity: int) -> None:
        if not self.has_sufficient_stock(quantity):
            raise ValueError(f"Incomplete stock for {self.name}. Requested: {quantity}, Available: {self.stock}")
        self.stock -= quantity

@dataclass
class OrderLine:
    sku: str
    qty: int

@dataclass
class Order:
    order_id: str
    customer_id: str
    lines: List[OrderLine] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "lines": [{"sku": line.sku, "qty": line.qty} for line in self.lines]
        }