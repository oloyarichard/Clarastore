from django.urls import path
from .views import ProductListView, ProductDetailView, ProductCreateView, ProductCreateUpdateDestroyView

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('create/', ProductCreateView.as_view(), name='product-create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('<int:pk>/manage/', ProductCreateUpdateDestroyView.as_view(), name='product-manage'),
]
