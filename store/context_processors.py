from .models import Category


def cart_info(request):
    """Makes the cart item count and category list available in every template."""
    cart = request.session.get("cart", {})
    return {
        "cart_count": sum(cart.values()),
        "nav_categories": Category.objects.all(),
    }
