from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductListSerializer, ProductAdminSerializer
from accounts.permissions import IsAdmin


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # is_in_stock is a computed @property on the model, not a real DB field,
    # so django-filter can't build an automatic filter for it — filtering
    # stays on real columns only.
    filterset_fields = ['category']
    search_fields = ['name', 'description', 'category']
    ordering_fields = ['price', 'created_at', 'name']

    def get_permissions(self):
        # Allow anyone to list products
        return []


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer

    def get_permissions(self):
        return []


class ProductCreateUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductAdminSerializer
    permission_classes = [IsAdmin]


class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductAdminSerializer
    permission_classes = [IsAdmin]
