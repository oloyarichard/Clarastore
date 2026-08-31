from abc import ABC, abstractmethod


class GatewayError(Exception):
    """Raised for any failure talking to a mobile money provider."""
    pass


class PaymentGateway(ABC):
    """
    Common interface for mobile money collection providers. Both MTN MoMo
    and Airtel Money are "request to pay" flows: you ask the provider to
    charge a customer's phone, the customer approves via a PIN prompt on
    their device, and you find out the result by polling or callback.
    """

    provider_name = None  # set by subclasses, must match TopUpRequest.PROVIDER_CHOICES

    @abstractmethod
    def request_payment(self, phone_number: str, amount, external_id: str, email: str = None) -> str:
        """
        Initiate a request-to-pay. Returns the provider's reference id,
        which must be stored on TopUpRequest.external_reference for later
        status checks. Raises GatewayError on failure to even submit the
        request (not to be confused with the customer declining it later).

        `email` is optional here since MTN/Airtel's own APIs don't need
        it — GosentePay's does, and requires it on every deposit.
        """
        raise NotImplementedError

    @abstractmethod
    def check_status(self, reference_id: str) -> str:
        """
        Poll the provider for the current status of a previously-initiated
        request. Must return one of: 'pending', 'successful', 'failed'.
        """
        raise NotImplementedError

    def disburse(self, phone_number: str, amount, email: str, reason: str, external_id: str) -> str:
        """
        Sends money OUT to a customer's mobile wallet — used for refund
        disbursements. Not every gateway in this codebase implements
        this (MTN/Airtel here were only ever wired for collection); the
        default raises clearly rather than silently doing nothing.
        Returns the provider's reference id for the disbursement.
        """
        raise NotImplementedError(f"{self.provider_name} does not support disbursement.")
