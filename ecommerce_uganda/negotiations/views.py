from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import NegotiationSession
from .serializers import (
    NegotiationOfferSerializer,
    NegotiationSessionSerializer,
    StartNegotiationSerializer,
    SubmitOfferSerializer,
)
from .throttles import NegotiationRateThrottle


def _get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _owns(negotiation, request):
    if request.user.is_authenticated:
        return negotiation.user_id == request.user.id
    return negotiation.session_key == request.session.session_key


class StartNegotiationView(APIView):
    """Guests can negotiate, same as guest cart — permission mirrors CartView."""
    throttle_classes = [NegotiationRateThrottle]

    def get_permissions(self):
        return [AllowAny()]

    def post(self, request):
        serializer = StartNegotiationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data['product_id']

        if request.user.is_authenticated:
            negotiation = services.start_negotiation(product, user=request.user)
        else:
            session_key = _get_session_key(request)
            negotiation = services.start_negotiation(product, session_key=session_key)

        return Response(
            NegotiationSessionSerializer(negotiation).data,
            status=status.HTTP_201_CREATED,
        )


class SubmitOfferView(APIView):
    throttle_classes = [NegotiationRateThrottle]

    def get_permissions(self):
        return [AllowAny()]

    def post(self, request, pk):
        try:
            negotiation = NegotiationSession.objects.get(pk=pk)
        except NegotiationSession.DoesNotExist:
            return Response({"error": "Negotiation not found."}, status=status.HTTP_404_NOT_FOUND)

        if not _owns(negotiation, request):
            return Response({"error": "Not your negotiation."}, status=status.HTTP_403_FORBIDDEN)

        if negotiation.status != 'active':
            return Response(
                {"error": f"This negotiation is already {negotiation.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmitOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ai_turn = services.submit_customer_offer(negotiation, serializer.validated_data['amount'])

        negotiation.refresh_from_db()
        return Response({
            'negotiation': NegotiationSessionSerializer(negotiation).data,
            'latest_response': NegotiationOfferSerializer(ai_turn).data,
        })


class AcceptCounterView(APIView):
    """
    Finalizes at whatever price the AI's most recent COUNTER proposed,
    without another AI round-trip — see services.accept_current_counter
    for why. Ownership and status checks mirror SubmitOfferView exactly.
    """
    throttle_classes = [NegotiationRateThrottle]

    def get_permissions(self):
        return [AllowAny()]

    def post(self, request, pk):
        try:
            negotiation = NegotiationSession.objects.get(pk=pk)
        except NegotiationSession.DoesNotExist:
            return Response({"error": "Negotiation not found."}, status=status.HTTP_404_NOT_FOUND)

        if not _owns(negotiation, request):
            return Response({"error": "Not your negotiation."}, status=status.HTTP_403_FORBIDDEN)

        try:
            price = services.accept_current_counter(negotiation)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        negotiation.refresh_from_db()
        return Response({
            'negotiation': NegotiationSessionSerializer(negotiation).data,
            'agreed_price': price,
        })


class NegotiationDetailView(APIView):
    def get_permissions(self):
        return [AllowAny()]

    def get(self, request, pk):
        try:
            negotiation = NegotiationSession.objects.get(pk=pk)
        except NegotiationSession.DoesNotExist:
            return Response({"error": "Negotiation not found."}, status=status.HTTP_404_NOT_FOUND)

        if not _owns(negotiation, request):
            return Response({"error": "Not your negotiation."}, status=status.HTTP_403_FORBIDDEN)

        return Response(NegotiationSessionSerializer(negotiation).data)
