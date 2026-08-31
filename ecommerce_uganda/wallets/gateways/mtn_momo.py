import uuid

import requests
from django.conf import settings
from django.core.cache import cache

from .base import GatewayError, PaymentGateway

TOKEN_CACHE_KEY = "mtn_momo_access_token"


class MtnMomoGateway(PaymentGateway):
    """
    MTN MoMo Collections API (Request to Pay). Docs: momodeveloper.mtn.com
    Sandbox and production use the same endpoints, switched via the
    X-Target-Environment header and MOMO_BASE_URL.

    Required settings:
      MOMO_BASE_URL, MOMO_SUBSCRIPTION_KEY, MOMO_API_USER, MOMO_API_KEY,
      MOMO_TARGET_ENVIRONMENT ('sandbox' or a production environment name)
    """

    provider_name = 'mtn_momo'

    def __init__(self):
        self.base_url = settings.MOMO_BASE_URL.rstrip('/')
        self.subscription_key = settings.MOMO_SUBSCRIPTION_KEY
        self.api_user = settings.MOMO_API_USER
        self.api_key = settings.MOMO_API_KEY
        self.target_environment = settings.MOMO_TARGET_ENVIRONMENT

    def _get_access_token(self):
        """OAuth token via Basic auth (api_user:api_key). Cached until near expiry."""
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

        resp = requests.post(
            f"{self.base_url}/collection/token/",
            auth=(self.api_user, self.api_key),
            headers={"Ocp-Apim-Subscription-Key": self.subscription_key},
            timeout=15,
        )
        if resp.status_code != 200:
            raise GatewayError(f"MTN MoMo token request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        # cache slightly under actual expiry so we never use a stale token
        cache.set(TOKEN_CACHE_KEY, token, timeout=max(expires_in - 60, 60))
        return token

    def request_payment(self, phone_number: str, amount, external_id: str, email: str = None) -> str:
        token = self._get_access_token()
        reference_id = str(uuid.uuid4())

        resp = requests.post(
            f"{self.base_url}/collection/v1_0/requesttopay",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Reference-Id": reference_id,
                "X-Target-Environment": self.target_environment,
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Content-Type": "application/json",
            },
            json={
                "amount": str(amount),
                "currency": "UGX",
                "externalId": external_id,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number,
                },
                "payerMessage": "Wallet top-up",
                "payeeNote": "Wallet top-up",
            },
            timeout=15,
        )
        if resp.status_code != 202:
            raise GatewayError(f"MTN MoMo request-to-pay failed: {resp.status_code} {resp.text}")

        return reference_id

    def check_status(self, reference_id: str) -> str:
        token = self._get_access_token()

        resp = requests.get(
            f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Target-Environment": self.target_environment,
                "Ocp-Apim-Subscription-Key": self.subscription_key,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise GatewayError(f"MTN MoMo status check failed: {resp.status_code} {resp.text}")

        status = resp.json().get("status", "").upper()
        mapping = {"PENDING": "pending", "SUCCESSFUL": "successful", "FAILED": "failed"}
        return mapping.get(status, "pending")
