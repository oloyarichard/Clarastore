import re

from .airtel_money import AirtelMoneyGateway
from .base import GatewayError, PaymentGateway
from .gosentepay import GosentePayGateway
from .mtn_momo import MtnMomoGateway

# Uganda mobile prefixes (after normalizing to '0XXXXXXXXX' or '256XXXXXXXXX').
# MTN: 077, 078, 076, 039 | Airtel: 070, 075, 074, 020
# These shift occasionally as operators get new number ranges — treat this
# as a convenience default, not a guarantee; letting the user pick the
# provider explicitly at top-up time is safer than relying on this alone.
# No longer used by default now that GosentePay handles MTN/Airtel
# routing internally — kept available for the old direct-integration
# path, which still exists but isn't the active default.
MTN_PREFIXES = ('077', '078', '076', '039')
AIRTEL_PREFIXES = ('070', '075', '074', '020')

_GATEWAYS = {
    'gosentepay': GosentePayGateway,
    'mtn_momo': MtnMomoGateway,
    'airtel_money': AirtelMoneyGateway,
}


def get_gateway(provider: str) -> PaymentGateway:
    """Returns an instantiated gateway client for the given provider key."""
    gateway_cls = _GATEWAYS.get(provider)
    if not gateway_cls:
        raise GatewayError(f"Unknown payment provider: {provider}")
    return gateway_cls()


def detect_provider(phone_number: str) -> str:
    """
    Best-effort guess of MTN vs Airtel from a Ugandan phone number.
    Normalizes '+256...', '256...', and '0...' formats to a local prefix
    before matching. Raises GatewayError if it can't confidently tell —
    callers should fall back to asking the user to pick explicitly.
    """
    digits = re.sub(r'\D', '', phone_number)

    if digits.startswith('256'):
        local = '0' + digits[3:]
    elif digits.startswith('0'):
        local = digits
    else:
        local = '0' + digits

    prefix = local[:3]

    if prefix in MTN_PREFIXES:
        return 'mtn_momo'
    if prefix in AIRTEL_PREFIXES:
        return 'airtel_money'

    raise GatewayError(f"Could not determine provider for {phone_number} — ask the user to select one.")
