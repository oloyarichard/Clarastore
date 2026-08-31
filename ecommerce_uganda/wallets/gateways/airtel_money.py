import uuid

import requests
from django.conf import settings
from django.core.cache import cache

from .base import GatewayError, PaymentGateway

TOKEN_CACHE_KEY = "airtel_money_access_token"


class AirtelMoneyGateway(PaymentGateway):
    """
    Airtel Money Collections API (Request to Pay / "push"). Docs:
    developers.airtel.africa

    Required settings:
      AIRTEL_BASE_URL, AIRTEL_CLIENT_ID, AIRTEL_CLIENT_SECRET, AIRTEL_COUNTRY
      (e.g. 'UG'), AIRTEL_CURRENCY (e.g. 'UGX')
    """

    provider_name = 'airtel_money'

    def __init__(self):
        self.base_url = settings.AIRTEL_BASE_URL.rstrip('/')
        self.client_id = settings.AIRTEL_CLIENT_ID
        self.client_secret = settings.AIRTEL_CLIENT_SECRET
        self.country = settings.AIRTEL_COUNTRY
        self.currency = settings.AIRTEL_CURRENCY

    def _get_access_token(self):
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

        resp = requests.post(
            f"{self.base_url}/auth/oauth2/token",
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise GatewayError(f"Airtel Money token request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        cache.set(TOKEN_CACHE_KEY, token, timeout=max(expires_in - 60, 60))
        return token

    def _headers(self, token):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "X-Country": self.country,
            "X-Currency": self.currency,
        }

    def request_payment(self, phone_number: str, amount, external_id: str, email: str = None) -> str:
        token = self._get_access_token()
        # Airtel wants the MSISDN without country code / leading zero in most
        # deployments (e.g. "771234567" not "+256771234567") — normalize
        # upstream before calling this, or adjust here once confirmed against
        # sandbox behaviour.
        transaction_id = str(uuid.uuid4())

        resp = requests.post(
            f"{self.base_url}/merchant/v1/payments/",
            headers=self._headers(token),
            json={
                "reference": external_id,
                "subscriber": {
                    "country": self.country,
                    "currency": self.currency,
                    "msisdn": phone_number,
                },
                "transaction": {
                    "amount": str(amount),
                    "country": self.country,
                    "currency": self.currency,
                    "id": transaction_id,
                },
            },
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            raise GatewayError(f"Airtel Money request-to-pay failed: {resp.status_code} {resp.text}")

        return transaction_id

    def check_status(self, reference_id: str) -> str:
        token = self._get_access_token()

        resp = requests.get(
            f"{self.base_url}/standard/v1/payments/{reference_id}",
            headers=self._headers(token),
            timeout=15,
        )
        if resp.status_code != 200:
            raise GatewayError(f"Airtel Money status check failed: {resp.status_code} {resp.text}")

        data = resp.json()
        status = data.get("data", {}).get("transaction", {}).get("status", "").upper()
        mapping = {"TIP": "pending", "SUCCESS": "successful", "FAILED": "failed"}
        return mapping.get(status, "pending")
