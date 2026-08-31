from django.contrib import admin

from .models import AgentCommission, RefundDisbursement, TopUpRequest, Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'updated_at']
    search_fields = ['user__username', 'user__email', 'user__phone']
    readonly_fields = ['created_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        # Wallets are never deletable, even by superusers — history must persist.
        return False

    def has_add_permission(self, request):
        # Wallets are always auto-created via get_or_create wherever
        # they're needed (commission crediting, refund clawback, etc.)
        # — manually adding one here risks a duplicate/orphaned wallet
        # with an arbitrary starting balance that bypasses the ledger
        # entirely. Balance itself stays fully editable on existing
        # wallets, which is deliberately the only way top-ups happen now.
        return False

    def save_model(self, request, obj, form, change):
        from wallets.notifications import send_wallet_adjustment_notification
        old_balance = None
        if change and 'balance' in form.changed_data:
            old_balance = Wallet.objects.get(pk=obj.pk).balance
        super().save_model(request, obj, form, change)
        if old_balance is not None and old_balance != obj.balance:
            send_wallet_adjustment_notification(obj.user, old_balance, obj.balance)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'type', 'amount', 'balance_after', 'reference', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['wallet__user__username', 'wallet__user__email', 'reference']
    readonly_fields = [f.name for f in WalletTransaction._meta.fields]

    def has_delete_permission(self, request, obj=None):
        # The ledger is permanent — no deletions, ever.
        return False

    def has_add_permission(self, request):
        # Transactions must only be created by services.py so the ledger
        # and wallet balance never drift apart.
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'phone_number', 'amount', 'status', 'created_at']
    list_filter = ['provider', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number', 'external_reference']
    readonly_fields = ['external_reference', 'raw_response', 'wallet_transaction', 'created_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        # Keep the record even for failed/expired attempts — useful for
        # reconciling with provider statements later.
        return False

    def has_add_permission(self, request):
        return False


@admin.register(AgentCommission)
class AgentCommissionAdmin(admin.ModelAdmin):
    list_display = ['agent', 'order_item', 'profit_amount', 'commission_amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['agent__username', 'agent__email']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RefundDisbursement)
class RefundDisbursementAdmin(admin.ModelAdmin):
    list_display = ['order', 'amount', 'status', 'external_reference', 'initiated_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__id', 'external_reference']
    readonly_fields = [f.name for f in RefundDisbursement._meta.fields]

    def has_delete_permission(self, request, obj=None):
        # Real money left the business for each of these — the record
        # must persist regardless of anything else.
        return False

    def has_add_permission(self, request):
        # Only ever created by wallets.services.process_refund, which
        # also handles the actual disbursement — never create one here
        # without money having actually moved.
        return False

    def has_change_permission(self, request, obj=None):
        return False
