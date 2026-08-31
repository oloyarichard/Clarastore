from django.urls import path
from .views import CartView, MergeCartView

urlpatterns = [
    path('', CartView.as_view(), name='cart'),
    path('merge/', MergeCartView.as_view(), name='cart-merge'),
]
