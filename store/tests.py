from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Order, OrderItem, Product

User = get_user_model()

CHECKOUT_DATA = {
    "full_name": "Asha Patel",
    "email": "asha@example.com",
    "phone": "+91 9876543210",
    "shipping_address": "12 Market Road, Near Clock Tower",
    "city": "Rajkot",
    "state": "Gujarat",
    "postal_code": "360001",
}


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Electronics")
        cls.cat2 = Category.objects.create(name="Fashion")
        cls.p1 = Product.objects.create(name="Headphones", description="Nice", price=Decimal("100.00"), stock_quantity=10, category=cls.cat)
        cls.p2 = Product.objects.create(name="T-Shirt", description="Soft", price=Decimal("50.50"), stock_quantity=3, category=cls.cat2)
        cls.hidden = Product.objects.create(name="Secret", description="x", price=Decimal("9.99"), stock_quantity=5, category=cls.cat, is_active=False)
        cls.user = User.objects.create_user("alice", "alice@example.com", "StrongPass123!", first_name="Alice")
        cls.other = User.objects.create_user("bob", "bob@example.com", "StrongPass123!")

    def add_to_cart(self, product, qty=1):
        return self.client.post(reverse("cart_add", args=[product.pk]), {"quantity": qty})


class AuthTests(BaseTestCase):
    def test_register_success_and_password_hashed(self):
        resp = self.client.post(reverse("register"), {
            "full_name": "Carol Singh", "username": "carol", "email": "carol@example.com",
            "password1": "VeryStrong#2026", "password2": "VeryStrong#2026"})
        self.assertRedirects(resp, reverse("home"))
        u = User.objects.get(username="carol")
        self.assertEqual((u.first_name, u.last_name), ("Carol", "Singh"))
        self.assertNotEqual(u.password, "VeryStrong#2026")
        self.assertTrue(u.password.startswith(("pbkdf2_", "argon2", "bcrypt", "scrypt")))
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_validation_errors(self):
        resp = self.client.post(reverse("register"), {
            "full_name": "", "username": "alice", "email": "alice@example.com",
            "password1": "VeryStrong#2026", "password2": "different"})
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        for field in ("full_name", "username", "email", "password2"):
            self.assertIn(field, form.errors)
        self.assertEqual(User.objects.filter(username="alice").count(), 1)

    def test_login_logout(self):
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "StrongPass123!"})
        self.assertRedirects(resp, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_wrong_password(self):
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "nope"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_protected_pages_redirect_anonymous(self):
        for name in ("checkout", "my_orders", "account"):
            resp = self.client.get(reverse(name))
            self.assertRedirects(resp, f"{reverse('login')}?next={reverse(name)}")


class CatalogueTests(BaseTestCase):
    def test_pages_load(self):
        for name in ("home", "product_list", "categories", "about", "contact", "cart", "login", "register"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_listing_hides_inactive_and_filters(self):
        resp = self.client.get(reverse("product_list"))
        self.assertContains(resp, "Headphones")
        self.assertNotContains(resp, "Secret")
        resp = self.client.get(reverse("product_list"), {"category": self.cat2.pk})
        self.assertContains(resp, "T-Shirt")
        self.assertNotContains(resp, "Headphones")
        resp = self.client.get(reverse("product_list"), {"q": "head"})
        self.assertContains(resp, "Headphones")
        self.assertNotContains(resp, "T-Shirt")

    def test_sorting(self):
        asc = list(self.client.get(reverse("product_list"), {"sort": "price_asc"}).context["page"].object_list)
        desc = list(self.client.get(reverse("product_list"), {"sort": "price_desc"}).context["page"].object_list)
        self.assertEqual(asc, [self.p2, self.p1])
        self.assertEqual(desc, [self.p1, self.p2])

    def test_empty_state(self):
        resp = self.client.get(reverse("product_list"), {"q": "zzzz"})
        self.assertContains(resp, "No products found")

    def test_pagination(self):
        for i in range(10):
            Product.objects.create(name=f"Extra {i}", description="d", price=Decimal("5"), stock_quantity=1, category=self.cat)
        resp = self.client.get(reverse("product_list"))
        self.assertTrue(resp.context["page"].has_next())
        self.assertEqual(len(resp.context["page"].object_list), 8)

    def test_detail(self):
        resp = self.client.get(reverse("product_detail", args=[self.p1.pk]))
        self.assertContains(resp, "Headphones")
        self.assertEqual(self.client.get(reverse("product_detail", args=[self.hidden.pk])).status_code, 404)


class CartTests(BaseTestCase):
    def test_add_update_remove_total(self):
        self.add_to_cart(self.p1, 2)
        self.add_to_cart(self.p2, 1)
        resp = self.client.get(reverse("cart"))
        self.assertEqual(resp.context["total"], Decimal("250.50"))
        self.assertEqual(self.client.session["cart"], {str(self.p1.pk): 2, str(self.p2.pk): 1})
        self.client.post(reverse("cart_update", args=[self.p1.pk]), {"quantity": 5})
        self.assertEqual(self.client.session["cart"][str(self.p1.pk)], 5)
        self.client.post(reverse("cart_remove", args=[self.p1.pk]))
        self.assertNotIn(str(self.p1.pk), self.client.session["cart"])

    def test_cannot_exceed_stock(self):
        self.add_to_cart(self.p2, 99)
        self.assertEqual(self.client.session["cart"][str(self.p2.pk)], 3)
        self.add_to_cart(self.p2, 1)
        self.assertEqual(self.client.session["cart"][str(self.p2.pk)], 3)

    def test_out_of_stock_cannot_be_added(self):
        self.p2.stock_quantity = 0
        self.p2.save()
        self.add_to_cart(self.p2)
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_cart_add_requires_post(self):
        self.assertEqual(self.client.get(reverse("cart_add", args=[self.p1.pk])).status_code, 405)

    def test_empty_cart_page(self):
        self.assertContains(self.client.get(reverse("cart")), "Your cart is empty")

    def test_cart_survives_login(self):
        self.add_to_cart(self.p1, 2)
        self.client.post(reverse("login"), {"username": "alice", "password": "StrongPass123!"})
        self.assertEqual(self.client.session["cart"], {str(self.p1.pk): 2})

    def test_open_redirect_blocked(self):
        resp = self.client.post(reverse("cart_add", args=[self.p1.pk]), {"quantity": 1, "next": "https://evil.example/"})
        self.assertRedirects(resp, reverse("cart"))


class CheckoutTests(BaseTestCase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_empty_cart_redirects(self):
        self.assertRedirects(self.client.get(reverse("checkout")), reverse("cart"))

    def test_checkout_validation(self):
        self.add_to_cart(self.p1, 1)
        bad = dict(CHECKOUT_DATA, phone="abc", postal_code="!!", email="not-an-email", city="")
        resp = self.client.post(reverse("checkout"), bad)
        self.assertEqual(resp.status_code, 200)
        for field in ("phone", "postal_code", "email", "city"):
            self.assertIn(field, resp.context["form"].errors)
        self.assertEqual(Order.objects.count(), 0)

    def test_successful_order(self):
        self.add_to_cart(self.p1, 2)
        self.add_to_cart(self.p2, 1)
        resp = self.client.post(reverse("checkout"), dict(CHECKOUT_DATA, total_amount="1"))
        order = Order.objects.get()
        self.assertRedirects(resp, reverse("order_confirmation", args=[order.order_number]))
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_amount, Decimal("250.50"))   # computed on the server
        self.assertEqual(order.status, "Pending")
        self.assertEqual(order.payment_method, "COD")
        self.assertEqual(order.items.count(), 2)
        item = order.items.get(product=self.p1)
        self.assertEqual((item.product_name, item.price_at_purchase, item.quantity, item.subtotal),
                         ("Headphones", Decimal("100.00"), 2, Decimal("200.00")))
        # inventory reduced, cart cleared
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock_quantity, self.p2.stock_quantity), (8, 2))
        self.assertEqual(self.client.session["cart"], {})
        self.assertContains(self.client.get(resp.url), order.order_number)

    def test_price_history_kept_after_price_change(self):
        self.add_to_cart(self.p1, 1)
        self.client.post(reverse("checkout"), CHECKOUT_DATA)
        self.p1.price = Decimal("999.00"); self.p1.save()
        self.assertEqual(OrderItem.objects.get().price_at_purchase, Decimal("100.00"))

    def test_insufficient_stock_blocks_order(self):
        self.add_to_cart(self.p2, 3)
        Product.objects.filter(pk=self.p2.pk).update(stock_quantity=1)   # someone else bought it
        resp = self.client.post(reverse("checkout"), CHECKOUT_DATA, follow=True)
        self.assertRedirects(resp, reverse("cart"))
        self.assertContains(resp, "Only 1 of")
        self.assertEqual(Order.objects.count(), 0)
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.stock_quantity, 1)

    def test_partial_failure_rolls_back(self):
        self.add_to_cart(self.p1, 2)
        self.add_to_cart(self.p2, 3)
        Product.objects.filter(pk=self.p2.pk).update(stock_quantity=0)
        self.client.post(reverse("checkout"), CHECKOUT_DATA)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)
        self.assertEqual(Order.objects.count(), 0)


class OrderAccessTests(BaseTestCase):
    def make_order(self, user):
        o = Order.objects.create(user=user, total_amount=Decimal("100"), **CHECKOUT_DATA)
        OrderItem.objects.create(order=o, product=self.p1, product_name="Headphones", price_at_purchase=Decimal("100"), quantity=1, subtotal=Decimal("100"))
        return o

    def test_user_sees_only_own_orders(self):
        mine, theirs = self.make_order(self.user), self.make_order(self.other)
        self.client.force_login(self.user)
        resp = self.client.get(reverse("my_orders"))
        self.assertContains(resp, mine.order_number)
        self.assertNotContains(resp, theirs.order_number)
        self.assertEqual(self.client.get(reverse("order_detail", args=[mine.order_number])).status_code, 200)

    def test_cannot_open_another_users_order(self):
        theirs = self.make_order(self.other)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("order_detail", args=[theirs.order_number])).status_code, 404)
        self.assertEqual(self.client.get(reverse("order_confirmation", args=[theirs.order_number])).status_code, 404)

    def test_deleting_product_keeps_order_item(self):
        o = self.make_order(self.user)
        self.p1.delete()
        item = o.items.get()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, "Headphones")


class AdminAccessTests(BaseTestCase):
    def test_anonymous_redirected_to_admin_login(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp.url)

    def test_customer_cannot_use_admin(self):
        self.client.force_login(self.user)
        resp = self.client.get("/admin/store/product/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp.url)

    def test_staff_can_use_admin_and_change_status(self):
        admin = User.objects.create_superuser("root", "root@example.com", "AdminPass123!")
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/admin/store/product/").status_code, 200)
        o = Order.objects.create(user=self.user, total_amount=Decimal("1"), **CHECKOUT_DATA)
        self.assertEqual(self.client.get("/admin/store/order/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/store/order/{o.pk}/change/").status_code, 200)
