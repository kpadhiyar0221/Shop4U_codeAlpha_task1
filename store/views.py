from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm, ContactForm, LoginForm, RegisterForm
from .models import Category, Order, OrderItem, Product

PAGE_SIZE = 8


def _active_products():
    return Product.objects.filter(is_active=True).select_related("category")


def _safe_next(request, default="cart"):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(default)


# ---------------------------------------------------------------- Public pages
def home(request):
    products = _active_products()
    context = {
        "featured": products.filter(stock_quantity__gt=0).order_by("-price")[:4],
        "new_arrivals": products.order_by("-created_at")[:4],
        "categories": Category.objects.annotate(
            n=Count("products", filter=Q(products__is_active=True))
        ),
    }
    return render(request, "home.html", context)


def product_list(request):
    products = _active_products()
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "")

    if q:
        products = products.filter(name__icontains=q)
    selected_category = None
    if category.isdigit():
        selected_category = Category.objects.filter(pk=int(category)).first()
        if selected_category:
            products = products.filter(category=selected_category)
    if sort == "price_asc":
        products = products.order_by("price", "name")
    elif sort == "price_desc":
        products = products.order_by("-price", "name")

    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "product_list.html",
        {
            "page": page,
            "q": q,
            "sort": sort,
            "categories": Category.objects.all(),
            "selected_category": selected_category,
            "querystring": params.urlencode(),
        },
    )


def categories(request):
    cats = Category.objects.annotate(n=Count("products", filter=Q(products__is_active=True)))
    return render(request, "categories.html", {"categories": cats})


def product_detail(request, pk):
    product = get_object_or_404(_active_products(), pk=pk)
    related = _active_products().filter(category=product.category).exclude(pk=pk)[:4]
    return render(request, "product_detail.html", {"product": product, "related": related})


def about(request):
    return render(request, "about.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        send_mail(
            f"[Shop4U contact] {d['subject']}",
            f"From: {d['name']} <{d['email']}>\n\n{d['message']}",
            None,
            ["support@shop4u.local"],
        )
        messages.success(request, "Thanks! Your message has been sent. We'll reply within 1-2 working days.")
        return redirect("contact")
    return render(request, "contact.html", {"form": form})


# ------------------------------------------------------------------------ Cart
def cart_view(request):
    cart = Cart(request)
    items = cart.items()
    return render(request, "cart.html", {"items": items, "total": cart.total(items)})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        qty = int(request.POST.get("quantity", 1))
    except ValueError:
        qty = 1
    if qty < 1:
        qty = 1
    if not product.in_stock:
        messages.error(request, f"Sorry, {product.name} is out of stock.")
        return _safe_next(request)
    final, capped = Cart(request).add(product, qty)
    if capped:
        messages.warning(
            request, f"Only {product.stock_quantity} of {product.name} available. Your cart now has {final}."
        )
    else:
        messages.success(request, f"Added {product.name} to your cart.")
    return _safe_next(request)


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        qty = int(request.POST.get("quantity", 1))
    except ValueError:
        qty = 1
    cart = Cart(request)
    if qty < 1:
        cart.remove(pk)
        messages.success(request, f"Removed {product.name} from your cart.")
    else:
        final, capped = cart.add(product, qty, override=True)
        if capped:
            messages.warning(request, f"Only {product.stock_quantity} of {product.name} in stock. Quantity set to {final}.")
        else:
            messages.success(request, "Cart updated.")
    return redirect("cart")


@require_POST
def cart_remove(request, pk):
    Cart(request).remove(pk)
    messages.success(request, "Item removed from your cart.")
    return redirect("cart")


# -------------------------------------------------------------------- Checkout
class StockError(Exception):
    pass


def place_order(user, cleaned_data, cart):
    """Create an order safely. Everything succeeds together or nothing is saved."""
    with transaction.atomic():
        ids = [int(pk) for pk in cart.data]
        locked = {
            p.pk: p
            for p in Product.objects.select_for_update().filter(pk__in=ids, is_active=True)
        }
        if not locked:
            raise StockError("Your cart is empty.")
        lines, total = [], Decimal("0.00")
        for key, qty in cart.data.items():
            product = locked.get(int(key))
            if product is None:
                raise StockError("A product in your cart is no longer available.")
            if qty > product.stock_quantity:
                raise StockError(
                    f"Only {product.stock_quantity} of '{product.name}' left in stock."
                    if product.stock_quantity
                    else f"'{product.name}' is out of stock."
                )
            subtotal = product.price * qty  # price comes from the database, never from the browser
            total += subtotal
            lines.append((product, qty, subtotal))

        order = Order.objects.create(
            user=user, total_amount=total, payment_method=Order.Payment.COD, **cleaned_data
        )
        for product, qty, subtotal in lines:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price_at_purchase=product.price,
                quantity=qty,
                subtotal=subtotal,
            )
            Product.objects.filter(pk=product.pk).update(stock_quantity=F("stock_quantity") - qty)
    return order


@login_required
def checkout(request):
    cart = Cart(request)
    items = cart.items()
    if not items:
        messages.info(request, "Your cart is empty. Add something before checking out.")
        return redirect("cart")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request.user, form.cleaned_data, cart)
            except StockError as exc:
                messages.error(request, f"We couldn't place your order. {exc} Please adjust your cart.")
                return redirect("cart")
            cart.clear()
            messages.success(request, "Order placed successfully. Thank you for shopping with Shop4U!")
            return redirect("order_confirmation", order_number=order.order_number)
    else:
        user = request.user
        form = CheckoutForm(
            initial={"full_name": user.get_full_name(), "email": user.email}
        )
    return render(request, "checkout.html", {"form": form, "items": items, "total": cart.total(items)})


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "order_confirmation.html", {"order": order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "order_detail.html", {"order": order})


@login_required
def account(request):
    return render(
        request,
        "account.html",
        {"order_count": Order.objects.filter(user=request.user).count()},
    )


# ------------------------------------------------------------ Authentication
def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Shop4U, {user.first_name}! Your account is ready.")
        return redirect("home")
    return render(request, "register.html", {"form": form})


class ShopLoginView(LoginView):
    template_name = "login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {form.get_user().first_name or form.get_user().username}!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Login failed. Check your username and password.")
        return super().form_invalid(form)


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")
