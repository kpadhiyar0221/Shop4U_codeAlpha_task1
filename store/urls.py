from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("categories/", views.categories, name="categories"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("orders/<str:order_number>/confirmation/", views.order_confirmation, name="order_confirmation"),
    path("account/", views.account, name="account"),
    path("register/", views.register, name="register"),
    path("login/", views.ShopLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
