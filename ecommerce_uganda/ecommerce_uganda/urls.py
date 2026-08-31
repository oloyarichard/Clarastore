from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/products/', include('catalog.urls')),
    path('api/cart/', include('orders.cart_urls')),
    path('api/orders/', include('orders.urls')),
    path('api/wallet/', include('wallets.urls')),
    path('api/negotiations/', include('negotiations.urls')),
    path('', include('webapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
