from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, District


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'forwarding_hub']
    list_filter = ['type']
    search_fields = ['name']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.type == 'hub':
            form.base_fields['forwarding_hub'].widget.attrs['disabled'] = True
        return form


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'phone', 'district', 'is_active']
    list_filter = ['role', 'is_active', 'district']
    search_fields = ['username', 'email', 'phone', 'first_name', 'last_name']

    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Platform Info'), {'fields': ('role', 'phone', 'district')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Platform Info'), {'fields': ('role', 'phone', 'district')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('district')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Limit district choices based on role context
        if obj and obj.role == 'agent':
            form.base_fields['district'].help_text = "Agent's home hub district."
        elif obj and obj.role == 'customer':
            form.base_fields['district'].help_text = "Customer's delivery district."
        return form
