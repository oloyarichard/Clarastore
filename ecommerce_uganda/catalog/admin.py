from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'cost_price', 'seller_floor', 'stock', 'category', 'created_by', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    # created_by is never hand-picked — it's set automatically to whoever
    # is logged in when the product is created (see save_model below), so
    # it's readonly here rather than an editable dropdown.
    readonly_fields = ['created_by', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

    def save_model(self, request, obj, form, change):
        if not change:
            # Only set on first creation — editing an existing product
            # later shouldn't reassign who originally created it.
            obj.created_by = request.user
        # obj.clean() (called from Product.save()) enforces the minimum
        # margin rule — a validation error here surfaces as a normal
        # Django admin form error, not a silent save.
        super().save_model(request, obj, form, change)
