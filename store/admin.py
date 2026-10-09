from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "product_count")
    search_fields = ("name",)

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "category", "price", "stock_quantity", "is_active", "created_at")
    list_display_links = ("thumbnail", "name")
    list_editable = ("price", "stock_quantity", "is_active")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "description")
    list_per_page = 20

    @admin.display(description="Image")
    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:6px">', obj.image.url)
        return "-"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "product_name", "price_at_purchase", "quantity", "subtotal")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "full_name", "total_amount", "payment_method", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("order_number", "full_name", "email", "phone", "user__username")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "user", "total_amount", "payment_method", "created_at")
    list_per_page = 20


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "quantity", "price_at_purchase", "subtotal")
    search_fields = ("order__order_number", "product_name")
    list_filter = ("order__status",)
    readonly_fields = ("order", "product", "product_name", "price_at_purchase", "quantity", "subtotal")

    def has_add_permission(self, request):
        return False
