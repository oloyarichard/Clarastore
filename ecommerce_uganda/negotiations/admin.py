from django.contrib import admin

from .models import MarketSnapshot, NegotiationOffer, NegotiationSession


class NegotiationOfferInline(admin.TabularInline):
    model = NegotiationOffer
    extra = 0
    readonly_fields = [f.name for f in NegotiationOffer._meta.fields]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(NegotiationSession)
class NegotiationSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'owner_display', 'status', 'agreed_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['product__name', 'user__email', 'session_key']
    inlines = [NegotiationOfferInline]
    readonly_fields = [f.name for f in NegotiationSession._meta.fields]

    def owner_display(self, obj):
        return obj.user.email if obj.user else f"guest:{obj.session_key[:8]}"
    owner_display.short_description = 'Customer'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(admin.ModelAdmin):
    list_display = ['product', 'calculated_market_price', 'demand_score', 'confidence', 'generated_at']
    list_filter = ['generated_at']
    search_fields = ['product__name']
    readonly_fields = [f.name for f in MarketSnapshot._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
