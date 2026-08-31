from django.urls import path

from . import views

app_name = 'webapp'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('download/', views.DownloadView.as_view(), name='download'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
    path('delivery-and-refunds/', views.DeliveryRefundsView.as_view(), name='delivery_refunds'),
    path('contact/', views.ContactView.as_view(), name='contact'),

    path('shop/', views.ShopView.as_view(), name='shop'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('cart/', views.CartView.as_view(), name='cart'),

    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),

    path('orders/', views.OrdersView.as_view(), name='orders'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),

    path('wallet/', views.WalletView.as_view(), name='wallet'),
    path('account/', views.AccountView.as_view(), name='account'),

    path('agent/dashboard/', views.AgentDashboardView.as_view(), name='agent_dashboard'),
    path('agent/topup-customer/', views.AgentTopupCustomerView.as_view(), name='agent_topup_customer'),
]
