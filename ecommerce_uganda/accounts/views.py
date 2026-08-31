from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
from django.db import transaction

from .models import User, District
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    DistrictSerializer,
    AgentCreateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .permissions import IsAdmin
from .throttles import LoginRateThrottle, RegistrationRateThrottle, PasswordResetRateThrottle


def _set_auth_cookies(response, access=None, refresh=None, user=None):
    """
    Sets the real, httpOnly, security-bearing cookies (never readable by
    JS), plus small non-httpOnly companion cookies (user_role, user_id)
    the frontend reads only for UI decisions — which nav links to show,
    which page to redirect to. Those companions carry no security
    weight of their own; the actual access control always happens
    server-side against the httpOnly token, same as before.

    secure=not DEBUG: cookies are HTTPS-only in production, but that
    same flag would silently block them from ever being set during
    local development over plain HTTP — which is exactly the setup
    this project tests against day to day.
    """
    common = dict(httponly=True, samesite='Lax', secure=not settings.DEBUG, path='/')
    if access is not None:
        response.set_cookie(
            'access_token', access, max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            **common,
        )
    if refresh is not None:
        response.set_cookie(
            'refresh_token', refresh, max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            **common,
        )
    if user is not None:
        readable = dict(httponly=False, samesite='Lax', secure=not settings.DEBUG, path='/',
                         max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()))
        response.set_cookie('user_role', user.role, **readable)
        response.set_cookie('user_id', str(user.id), **readable)


def _clear_auth_cookies(response):
    for name in ('access_token', 'refresh_token', 'user_role', 'user_id'):
        response.delete_cookie(name, path='/')


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create wallet for new customer
        from wallets.models import Wallet
        Wallet.objects.get_or_create(user=user, defaults={'balance': 0})

        # Deferred until the transaction commits — this whole method
        # runs inside @transaction.atomic, so sending a welcome email
        # any earlier risks welcoming an account that could still roll
        # back due to a later error in this same request.
        from wallets.notifications import send_welcome_notification
        transaction.on_commit(lambda: send_welcome_notification(user))

        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully.'
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Tokens stay in the JSON body too — the Flutter app reads
            # them from there and stores them itself (flutter_secure_storage),
            # since it can't use browser cookies at all. The website's own
            # JS deliberately never stores anything from this body; the
            # cookies below are what it actually relies on.
            email = request.data.get('email')
            user = User.objects.filter(email=email).first()
            _set_auth_cookies(response, access=response.data.get('access'),
                               refresh=response.data.get('refresh'), user=user)
        return response


class RefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Prefer the httpOnly cookie; fall back to the request body for
        # API clients (Flutter) that never had a cookie to begin with.
        if not request.data.get('refresh') and request.COOKIES.get('refresh_token'):
            request.data['refresh'] = request.COOKIES.get('refresh_token')

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            _set_auth_cookies(
                response,
                access=response.data.get('access'),
                refresh=response.data.get('refresh'),  # present only if ROTATE_REFRESH_TOKENS
            )
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                # Already invalid/expired/blacklisted — logging out is
                # still a success either way, nothing left to revoke.
                pass

        response = Response({'detail': 'Logged out.'})
        _clear_auth_cookies(response)
        return response


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class DistrictListView(generics.ListAPIView):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [AllowAny]


class AgentCreateView(generics.CreateAPIView):
    queryset = User.objects.filter(role='agent')
    serializer_class = AgentCreateSerializer
    permission_classes = [IsAdmin]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = serializer.save()

        # Create wallet for new agent
        from wallets.models import Wallet
        Wallet.objects.get_or_create(user=agent, defaults={'balance': 0})

        return Response({
            'agent': UserSerializer(agent).data,
            'message': 'Agent created successfully.'
        }, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    """
    Always returns the same generic response regardless of whether the
    email actually matches an account — the alternative (a different
    response for "email not found") would let an attacker enumerate
    which emails have accounts on this platform, just like registration's
    own email-uniqueness check already deliberately avoids doing.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if user:
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from .notifications import send_password_reset_email

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.SITE_URL.rstrip('/')}/reset-password/?uid={uid}&token={token}"
            send_password_reset_email(user, reset_url)

        return Response(
            {"message": "If an account exists with that email, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from .notifications import send_password_changed_notification

        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "This reset link is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "This reset link is invalid or has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        send_password_changed_notification(user)

        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
