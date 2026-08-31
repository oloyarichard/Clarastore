from django.urls import path

from .views import AcceptCounterView, NegotiationDetailView, StartNegotiationView, SubmitOfferView

urlpatterns = [
    path('start/', StartNegotiationView.as_view(), name='negotiation-start'),
    path('<int:pk>/', NegotiationDetailView.as_view(), name='negotiation-detail'),
    path('<int:pk>/offer/', SubmitOfferView.as_view(), name='negotiation-offer'),
    path('<int:pk>/accept-counter/', AcceptCounterView.as_view(), name='negotiation-accept-counter'),
]
