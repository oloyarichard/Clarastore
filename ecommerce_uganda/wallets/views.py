from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAgent
from . import services
from .gateways import GatewayError, get_gateway
from .models import AgentCommission, RefundDisbursement, TopUpRequest, Wallet
from .serializers import (
    AgentCommissionSerializer,
    AgentTopUpSerializer,
    GatewayTopUpSerializer,
    TopUpRequestSerializer,
    WalletSerializer,
    WalletTransactionSerializer,
)


class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet.transactions.all()


from rest_framework.throttling import UserRateThrottle


from rest_framework.throttling import AnonRateThrottle


class WebhookRateThrottle(AnonRateThrottle):
    """
    The callback views (GatewayTopUpCallbackView, RefundCallbackView)
    are deliberately unauthenticated — GosentePay itself calls them,
    not a logged-in user — so a UserRateThrottle wouldn't work here at
    all (nothing to key by). That also means, without this, they were
    completely open to the internet with zero rate limiting: anyone
    could flood them with fake callback bodies, each one triggering a
    real, authenticated re-verification call back to GoSentePay's own
    API — wasted load at best, and a way to burn through whatever
    request budget exists with GoSentePay at worst. IP-based, since
    that's the only identifier available for an unauthenticated caller.
    """
    scope = 'webhook'


class TopUpRateThrottle(UserRateThrottle):
    """
    Without this, an authenticated attacker could enter ANY phone
    number — not necessarily their own — and repeatedly trigger real
    GoSentePay payment prompts on a stranger's phone. Rate-limiting by
    the authenticated user (not IP) means the attacker's own account
    gets throttled regardless of how many different victim numbers
    they try, which is the actual abuse pattern this closes.
    """
    scope = 'topup'


class GatewayTopUpInitiateView(APIView):
    """
    Starts a mobile money top-up via GoSentePay, funding the customer's
    own wallet — required for checkout, which pays directly out of
    wallet balance with no alternative payment path. Unlike agent-cash
    top-ups (disabled below — that's the trust-based, offline, harder
    to verify path), this one is a real, GoSentePay-confirmed payment
    and stays self-service.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [TopUpRateThrottle]

    def post(self, request):
        serializer = GatewayTopUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            topup_request = services.initiate_gateway_topup(
                user=request.user,
                amount=serializer.validated_data['amount'],
                phone_number=serializer.validated_data['phone_number'],
                provider=serializer.validated_data['provider'],
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TopUpRequestSerializer(topup_request).data, status=status.HTTP_201_CREATED)


class GatewayTopUpStatusView(APIView):
    """Client polls this with the TopUpRequest id to find out if a top-up succeeded."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        topup_request = get_object_or_404(TopUpRequest, pk=pk, user=request.user)
        try:
            topup_request = services.confirm_gateway_topup(topup_request)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TopUpRequestSerializer(topup_request).data)


class GosentePayCallbackView(APIView):
    """
    Single webhook receiver for every GoSentePay callback — deposits
    and withdrawals alike, since GoSentePay only actually has the one
    callback mechanism (this used to be two separate endpoints, split
    by an assumption that withdrawals had their own callback path,
    which turned out not to be the case).

    Looks up the reference against both TopUpRequest and
    RefundDisbursement and routes to whichever one actually matches —
    the caller doesn't need to know or declare which type of
    transaction this is.

    Same non-negotiable rule either way: the payload itself is never
    trusted. Every call re-verifies via the provider's own
    authenticated status-check before anything is recorded — a
    forged callback with a fabricated amount or status changes
    nothing, only what GoSentePay's own API actually confirms does.

    For a matched TopUpRequest: confirm_gateway_topup() re-checks and
    credits exactly once, safe to call repeatedly.

    For a matched RefundDisbursement: a confirmed match with what's
    already on file is a silent no-op. A genuine mismatch (GoSentePay
    now reporting something different than what we recorded when the
    disbursement first completed) is deliberately never auto-resolved
    — reversing an already-completed refund means un-refunding an
    order and reversing a commission clawback, which is a business
    decision, not something safe to automate silently. That case is
    flagged for admin review instead.
    """
    permission_classes = []
    authentication_classes = []
    throttle_classes = [WebhookRateThrottle]

    def post(self, request, provider):
        reference_id = (
            request.data.get('ref')
            or request.data.get('reference')
            or request.data.get('referenceId')
        )
        if not reference_id:
            return Response({"error": "Missing reference."}, status=status.HTTP_400_BAD_REQUEST)

        topup_request = TopUpRequest.objects.filter(external_reference=reference_id, provider=provider).first()
        if topup_request is not None:
            try:
                services.confirm_gateway_topup(topup_request)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Processed."}, status=status.HTTP_200_OK)

        refund = RefundDisbursement.objects.filter(external_reference=reference_id).first()
        if refund is not None:
            gateway = get_gateway(provider)
            try:
                verified_status = gateway.check_status(reference_id)
            except GatewayError as e:
                # Can't verify right now — do nothing rather than trust
                # the unverified payload. GoSentePay may retry later.
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if verified_status != 'successful' and refund.status == 'successful':
                refund.status = 'disputed'
                refund.save(update_fields=['status'])
                from wallets.notifications import send_refund_disputed_alert
                send_refund_disputed_alert(refund, verified_status)
            return Response({"message": "Processed."}, status=status.HTTP_200_OK)

        return Response({"error": "No matching transaction found for that reference."}, status=status.HTTP_404_NOT_FOUND)


class AgentTopUpCustomerView(APIView):
    """
    Disabled — wallet balances are now managed exclusively through
    Django admin, not via agent-collected cash top-ups. Kept in place
    rather than deleted, so restoring this later is a small, reversible
    change.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    def post(self, request):
        return Response(
            {"error": "Customer top-ups are currently managed by admin only."},
            status=status.HTTP_403_FORBIDDEN,
        )


class AgentCommissionListView(generics.ListAPIView):
    serializer_class = AgentCommissionSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        return AgentCommission.objects.filter(agent=self.request.user)
