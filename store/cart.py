"""Session-based shopping cart.

The cart lives in the visitor's session as {"<product_id>": quantity}.
It survives login/logout of the same browser session and never trusts prices
sent from the browser - prices are always read from the database.
"""
from decimal import Decimal

from .models import Product

CART_SESSION_KEY = "cart"


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(CART_SESSION_KEY, {})

    def _save(self):
        self.session[CART_SESSION_KEY] = self.data
        self.session.modified = True

    def add(self, product, quantity=1, override=False):
        """Add/replace quantity, capped by stock. Returns (final_quantity, was_capped)."""
        key = str(product.pk)
        current = 0 if override else self.data.get(key, 0)
        wanted = current + quantity
        final = max(0, min(wanted, product.stock_quantity))
        if final == 0:
            self.data.pop(key, None)
        else:
            self.data[key] = final
        self._save()
        return final, wanted > product.stock_quantity

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.data.clear()
        self._save()

    def items(self):
        """List of dicts with product, quantity and subtotal (inactive/deleted products are dropped)."""
        ids = [int(pk) for pk in self.data]
        products = Product.objects.filter(pk__in=ids, is_active=True).select_related("category")
        result = []
        found = set()
        for product in products:
            qty = self.data[str(product.pk)]
            found.add(str(product.pk))
            result.append(
                {"product": product, "quantity": qty, "subtotal": product.price * qty}
            )
        stale = set(self.data) - found
        if stale:
            for key in stale:
                del self.data[key]
            self._save()
        return result

    @property
    def count(self):
        return sum(self.data.values())

    def total(self, items=None):
        items = self.items() if items is None else items
        return sum((i["subtotal"] for i in items), Decimal("0.00"))
