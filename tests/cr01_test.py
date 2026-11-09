import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from supplydesk import menu
from supplydesk.cli import main
from supplydesk.service import OrderService


def item(product_id, quantity):
    return {"product_id": product_id, "quantity": quantity}


class ExpressTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    # Normal behaviour Testing
    def test_normal_regular_express_quote(self):
        quote = self.service.quote("regular", [item("notebook", 2)], "express")
        self.assertEqual(quote["fulfillment"], "express")
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 2200)

    def test_normal_student_express_quote(self):
        quote = self.service.quote("student", [item("hoodie", 2)], "express")
        self.assertEqual(quote["subtotal_cents"], 8000)
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 8400)

    # Boundary Behaviour Testing
    def test_boundary_express_fee_not_waived_over_free_delivery_threshold(self):
        standard = self.service.quote("regular", [item("hoodie", 3)], "delivery")
        express = self.service.quote("regular", [item("hoodie", 3)], "express")
        self.assertEqual(standard["delivery_cents"], 0)
        self.assertEqual(standard["total_cents"], 12000)
        self.assertEqual(express["delivery_cents"], 1200)
        self.assertEqual(express["total_cents"], 13200)

    # Invalid Behaviour Testing
    def test_invalid_other_fulfillment_values_still_rejected(self):
        for bad in ("Express", "overnight", "", None):
            with self.subTest(fulfillment=bad):
                with self.assertRaises(ValueError):
                    self.service.quote("regular", [item("notebook", 1)], bad)
                with self.assertRaises(ValueError):
                    self.service.place_order("regular", [item("notebook", 1)], bad)
        self.assertFalse(self.path.exists())

    # Important Behaviour to Preserve
    def test_preserve_pickup_and_standard_delivery_unchanged(self):
        pickup = self.service.quote("regular", [item("notebook", 2)], "pickup")
        delivery = self.service.quote("regular", [item("notebook", 2)], "delivery")
        self.assertEqual(pickup["delivery_cents"], 0)
        self.assertEqual(delivery["delivery_cents"], 600)

    def test_preserve_express_quote_matches_placed_order(self):
        items = [item("hoodie", 2), item("mug", 1)]
        quote = self.service.quote("student", items, "express")
        order = self.service.place_order("student", items, "express")
        for key in quote:
            self.assertEqual(quote[key], order[key], key)

    def test_preserve_express_order_after_reopen_and_cancel(self):
        order = self.service.place_order("student", [item("hoodie", 2)], "express")
        reopened = OrderService(self.path).get_order(order["order_id"])
        self.assertEqual(reopened, order)
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        for key in ("fulfillment", "items", "discount_cents",
                    "delivery_cents", "total_cents"):
            self.assertEqual(cancelled[key], order[key], key)

    # Interfaces: command line and menu
    def test_command_line_accepts_express(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = main(["--data", str(self.path), "quote", "--customer", "student",
                           "--fulfillment", "express", "--item", "hoodie:2"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out.getvalue())["total_cents"], 8400)

    def test_menu_prompt_offers_express_and_accepts_it(self):
        out = io.StringIO()
        inputs = ["2", "", "notebook", "2", "", "express", "0"]
        with mock.patch("builtins.input", side_effect=inputs), \
                contextlib.redirect_stdout(out):
            menu.run_menu(self.service)
        self.assertIn("express", out.getvalue())
        self.assertIn("Total: $22.00", out.getvalue())


if __name__ == "__main__":
    unittest.main()