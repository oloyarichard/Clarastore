from django.urls import path

from .views import (
    AgentCommissionListView,
    AgentTopUpCustomerView,
    GosentePayCallbackView,
    GatewayTopUpInitiateView,
    GatewayTopUpStatusView,
    WalletDetailView,
    WalletTransactionListView,
)

urlpatterns = [
    path('', WalletDetailView.as_view(), name='wallet-detail'),
    path('transactions/', WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('topup/', GatewayTopUpInitiateView.as_view(), name='wallet-topup'),
    path('topup/<int:pk>/status/', GatewayTopUpStatusView.as_view(), name='wallet-topup-status'),
    # Single callback for everything GoSentePay-related — deposits and
    # withdrawals both land here, since GoSentePay only has the one
    # callback mechanism (this used to be two separate URLs, split on
    # an incorrect assumption about withdrawals having their own).
    path('callback/<str:provider>/', GosentePayCallbackView.as_view(), name='wallet-callback'),
    path('agent/topup-customer/', AgentTopUpCustomerView.as_view(), name='agent-topup-customer'),
    path('agent/commissions/', AgentCommissionListView.as_view(), name='agent-commissions'),
]
