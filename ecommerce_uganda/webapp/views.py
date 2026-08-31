from django.views.generic import TemplateView


class ActivePageMixin:
    """Injects active_page so base.html can highlight the right nav item."""
    active_page = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = self.active_page
        return context


class HomeView(ActivePageMixin, TemplateView):
    template_name = 'webapp/index.html'
    active_page = 'home'


class DownloadView(ActivePageMixin, TemplateView):
    template_name = 'webapp/download.html'
    active_page = 'download'


class PrivacyPolicyView(TemplateView):
    template_name = 'webapp/privacy_policy.html'


class TermsOfServiceView(TemplateView):
    template_name = 'webapp/terms_of_service.html'


class DeliveryRefundsView(ActivePageMixin, TemplateView):
    template_name = 'webapp/delivery_refunds.html'
    active_page = 'delivery'


class ContactView(ActivePageMixin, TemplateView):
    template_name = 'webapp/contact.html'
    active_page = 'contact'


class ShopView(ActivePageMixin, TemplateView):
    template_name = 'webapp/shop.html'
    active_page = 'shop'


class ProductDetailView(TemplateView):
    """pk is passed straight to the template; the page's own JS fetches
    the actual product data from the API using it."""
    template_name = 'webapp/product_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pk'] = kwargs['pk']
        return context


class CartView(ActivePageMixin, TemplateView):
    template_name = 'webapp/cart.html'
    active_page = 'cart'


class LoginView(TemplateView):
    template_name = 'webapp/login.html'


class SignupView(TemplateView):
    template_name = 'webapp/signup.html'


class ForgotPasswordView(TemplateView):
    template_name = 'webapp/forgot_password.html'


class ResetPasswordView(TemplateView):
    template_name = 'webapp/reset_password.html'


class CheckoutView(TemplateView):
    template_name = 'webapp/checkout.html'


class OrdersView(TemplateView):
    template_name = 'webapp/orders.html'


class OrderDetailView(TemplateView):
    template_name = 'webapp/order_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pk'] = kwargs['pk']
        return context


class WalletView(TemplateView):
    template_name = 'webapp/wallet.html'


class AccountView(TemplateView):
    template_name = 'webapp/account.html'


class AgentDashboardView(TemplateView):
    template_name = 'webapp/agent_dashboard.html'


class AgentTopupCustomerView(TemplateView):
    template_name = 'webapp/agent_topup_customer.html'
