import tempfile
import unittest
from pathlib import Path

from supplydesk.service import OrderService


def item(product_id, quantity):
    return {"product_id": product_id, "quantity": quantity}


class Task2Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def stock(self, product_id):
        return next(p["stock"] for p in self.service.catalog()
                    if p["product_id"] == product_id)

    # Normal behaviour Testing
    def test_normal_multi_item_student_order(self):
        order = self.service.place_order(
            "student", [item("hoodie", 1), item("mug", 1)], "pickup")
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["subtotal_cents"], 5500)
        self.assertEqual(order["discount_cents"], 550)
        self.assertEqual(order["total_cents"], 4950)
        self.assertEqual(self.stock("hoodie"), 4)
        self.assertEqual(self.stock("mug"), 7)

    # Boundary Behaviour Testing
    def test_boundary_student_discount_at_exactly_5000_cents(self):
        quote = self.service.quote("student", [item("notebook", 10)])
        self.assertEqual(quote["subtotal_cents"], 5000)
        self.assertEqual(quote["discount_cents"], 500)
        self.assertEqual(quote["total_cents"], 4500)

    # Invalid Behaviour Testing
    def test_invalid_duplicate_lines_exceed_stock_combined(self):
        items = [item("hoodie", 3), item("hoodie", 3)]   # stock is 5
        with self.assertRaises(ValueError):
            self.service.place_order("regular", items)
        self.assertEqual(self.stock("hoodie"), 5)
        self.assertEqual(self.service.list_orders(), [])

    # Important Behaviour to Preserve from Refactoring
    def test_preserve_quote_matches_placed_order(self):
        items = [item("hoodie", 2), item("mug", 1)]
        quote = self.service.quote("student", items, "delivery")
        order = self.service.place_order("student", items, "delivery")
        for key in quote:
            self.assertEqual(quote[key], order[key], key)


if __name__ == "__main__":
    unittest.main()