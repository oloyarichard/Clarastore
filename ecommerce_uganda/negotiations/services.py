import random
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from catalog.models import Product
from orders.models import CartItem, OrderItem

from .ai_providers.base import AIProviderError
from .models import MarketSnapshot, NegotiationOffer, NegotiationSession


def get_ai_provider():
    """Single place that decides which AIProvider implementation is
    active — swap this to change providers without touching anything
    else in the negotiation flow."""
    from .ai_providers.gemini_provider import GeminiProvider
    return GeminiProvider()


# ---------------------------------------------------------------------
# Market signals — internal-only for now, per the agreed priority order
# (internal volume first; exchange rate and seasonal signals are real
# fields on MarketSnapshot but intentionally left at neutral/0 until a
# real external source is wired in — see class docstring below).
# ---------------------------------------------------------------------

def calculate_market_snapshot(product: Product) -> MarketSnapshot:
    """
    Computes a fresh MarketSnapshot from real internal data only.
    Confidence is deliberately kept low/honest when there isn't much
    real history to base it on — per the spec's rule against pretending
    thin data is confident intelligence.
    """
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

    units_sold_recent = OrderItem.objects.filter(
        product=product,
        order__created_at__gte=thirty_days_ago,
        order__payment_status='paid',
    ).aggregate(total=Sum('quantity'))['total'] or 0

    sales_velocity = units_sold_recent / 30.0

    # Demand proxy: how many active cart entries currently reference this
    # product, relative to stock. Crude but real — not fabricated. A
    # proper "views" signal would need a ProductView model that doesn't
    # exist yet; noted as a clear improvement, not silently invented here.
    active_cart_count = CartItem.objects.filter(product=product).count()
    demand_score = min(1.0, active_cart_count / 10.0) if active_cart_count else 0.0

    inventory_pressure = 0.0
    if product.stock > 0:
        # Higher when demand is high relative to what's left in stock.
        inventory_pressure = min(1.0, (active_cart_count + units_sold_recent) / max(product.stock, 1))
    elif active_cart_count > 0:
        inventory_pressure = 1.0

    # Not wired to a live source yet — left neutral on purpose rather
    # than inventing a number, exactly per the "don't pretend it's live"
    # rule. Revisit once a real UGX/USD feed and a seasonal calendar are
    # actually connected.
    exchange_rate_signal = 0.0
    seasonal_signal = 0.0

    # Confidence reflects how much real signal actually exists — a brand
    # new product with zero sales history gets a low number, honestly.
    confidence = min(1.0, (units_sold_recent + active_cart_count) / 20.0)

    # Configurable weighting, not hardcoded math scattered everywhere —
    # matches the spec's request for a tunable scoring system.
    weights = getattr(settings, 'MARKET_SIGNAL_WEIGHTS', {
        'demand': 0.40,
        'inventory': 0.25,
        'velocity_bonus_cap': 0.20,  # extra nudge from raw sales velocity, capped
        'exchange_rate': 0.10,
        'seasonal': 0.05,
    })

    velocity_component = min(sales_velocity / 5.0, 1.0) * weights['velocity_bonus_cap']
    composite = (
        demand_score * weights['demand']
        + inventory_pressure * weights['inventory']
        + velocity_component
        + exchange_rate_signal * weights['exchange_rate']
        + seasonal_signal * weights['seasonal']
    )
    # composite is roughly 0-1; map it onto a price adjustment band
    # bounded to +/-15% of the listed price so a thin/noisy signal can
    # never produce an irrational jump (spec's MAX_PRICE_CHANGE control).
    max_adjustment = Decimal('0.15')
    adjustment = (Decimal(str(composite)) - Decimal('0.5')) * 2 * max_adjustment
    calculated_market_price = (product.price * (Decimal('1') + adjustment)).quantize(Decimal('0.01'))

    # Never let the calculated price fall below the floor, even before
    # any AI is involved — this is a second, independent layer of the
    # same safety rule, not a replacement for the one in services below.
    floor = product.seller_floor or product.minimum_allowed_floor
    if calculated_market_price < floor:
        calculated_market_price = floor

    snapshot = MarketSnapshot.objects.create(
        product=product,
        sales_velocity=sales_velocity,
        demand_score=demand_score,
        inventory_pressure=inventory_pressure,
        exchange_rate_signal=exchange_rate_signal,
        seasonal_signal=seasonal_signal,
        calculated_market_price=calculated_market_price,
        confidence=confidence,
        expires_at=timezone.now() + timezone.timedelta(hours=6),
    )
    return snapshot


def get_fresh_snapshot(product: Product) -> MarketSnapshot:
    """Reuses the latest snapshot if still fresh, otherwise calculates a
    new one — this is the cache/cost-control boundary: negotiation calls
    never trigger signal recalculation themselves."""
    latest = product.market_snapshots.order_by('-generated_at').first()
    if latest and latest.is_fresh:
        return latest
    return calculate_market_snapshot(product)


# ---------------------------------------------------------------------
# THE absolute safety rule. Every AI response passes through this
# before anything is recorded, shown to a customer, or acted on.
# No code path may skip this function and act on raw AI output directly.
# ---------------------------------------------------------------------

# How many rounds it takes to actually reach the floor is randomized
# per negotiation, not fixed — a constant schedule (always reaching
# the floor on, say, exactly the 4th offer) is something a patient
# customer can simply learn and exploit every time. The target itself
# is derived deterministically from the negotiation's own id, so the
# SAME negotiation always computes the SAME target on every call
# (the price only ever moves toward the floor within one conversation,
# never confusingly back up), while DIFFERENT negotiations land on
# different targets — unpredictable from the outside, consistent from
# the inside.
_MIN_ROUNDS_TO_FLOOR = 2
_MAX_ROUNDS_TO_FLOOR = 5


def _graduated_floor_counter(current_ask, floor: Decimal, round_number: int, negotiation_id=None) -> Decimal:
    """
    A counter price between `current_ask` and `floor`, moving
    progressively closer to the floor as `round_number` increases,
    reaching it exactly by a per-negotiation randomized round — never
    later, so a determined customer always gets there eventually, and
    never a single fraction earlier, so the floor's neighborhood isn't
    revealed before it needs to be. Uses a separate, locally-seeded
    Random instance so this never disturbs unrelated randomness
    elsewhere (e.g. the fallback message variety), and a negotiation
    with no id yet (shouldn't normally happen) falls back to a fixed,
    reasonable target rather than raising.

    Once the target round is reached, a small amount of genuine
    per-call jitter is used instead of returning the bare floor number
    — a customer who keeps pushing and sees the exact same figure
    every single time has effectively been told "this is the floor"
    just as clearly as if the word had been used out loud. That jitter
    is explicitly bounded so it can never exceed whatever was quoted
    last round — an earlier version of this allowed the jittered price
    to occasionally tick back up between rounds (a random draw with no
    memory of the previous one can land higher by pure chance), which
    breaks the "always moves toward the floor" guarantee just as
    visibly as exact repetition breaks the "never reveal the floor"
    one. This version can never do either.
    """
    if current_ask is None or current_ask <= floor:
        # No real room between the asking price and the floor to
        # graduate through — still add jitter, bounded so it can never
        # exceed whatever was just quoted (current_ask, if any).
        return _bounded_floor_jitter(floor, ceiling=current_ask)
    seed = negotiation_id if negotiation_id is not None else 0
    target_rounds = random.Random(seed).randint(_MIN_ROUNDS_TO_FLOOR, _MAX_ROUNDS_TO_FLOOR)
    fraction = min(Decimal('1.0'), Decimal(round_number + 1) / Decimal(target_rounds))
    if fraction >= Decimal('1.0'):
        price = _bounded_floor_jitter(floor, ceiling=current_ask)
    else:
        price = current_ask - (current_ask - floor) * fraction
        # Round to the nearest 100 UGX for a cleaner-looking offer —
        # but never let that rounding push the result back below the
        # floor.
        price = (price / 100).quantize(Decimal('1')) * 100
    return max(price, floor)


def _bounded_floor_jitter(floor: Decimal, ceiling: Decimal = None) -> Decimal:
    """
    A price at or above the floor, never higher than `ceiling`
    (typically the price quoted last round, keeping the sequence
    monotonic), that tries to avoid exactly repeating `ceiling` when
    there's genuinely still room to.

    Draws from a FIXED range every time (0 to ~3% of the floor,
    floored at one real 100-UGX step) rather than a range derived from
    `ceiling` itself — an earlier version bounded the draw's own range
    by the previous quote, which compounds: each round's range only
    ever shrank, and the whole sequence collapsed into forced,
    permanent repetition within just two or three rounds — a worse
    problem than the one being fixed. Drawing from a constant range
    and clamping only the final result avoids that collapse; real
    variety persists for much longer, and only gives way to repetition
    once the sequence has genuinely, unavoidably reached the floor
    with zero room left — which is realistic negotiator behavior
    (a genuine final price does eventually get repeated if a customer
    keeps pushing past it), not a giveaway on its own.
    """
    cap_steps = max(1, int((floor * Decimal('0.03')) // 100))
    for _ in range(8):  # a handful of tries is more than enough given the range
        draw = Decimal(random.randint(0, cap_steps)) * 100
        candidate = floor + draw
        if ceiling is not None:
            candidate = min(candidate, (ceiling / 100).quantize(Decimal('1')) * 100)
        candidate = max(candidate, floor)
        if ceiling is None or candidate != ceiling:
            return candidate
    # Only reached when every retry happened to collide — this means
    # ceiling is already at or extremely close to the floor, so there
    # is no real room left; repeating it here is the mathematically
    # correct, unavoidable outcome, not a bug.
    return candidate


_REJECT_FALLBACK_TEMPLATES = (
    "That specific offer doesn't quite work, but I can do {price} UGX.",
    "I can't do that exact number, but how about {price} UGX?",
    "Let's meet somewhere better — would {price} UGX work for you?",
    "That's a bit of a stretch for us, but {price} UGX is doable.",
    "Not quite, but I can bring it down to {price} UGX for you.",
)


def _fallback_message(decision: str) -> str:
    """
    The safe, generic message shown whenever the AI's own message can't
    be trusted — empty, unparseable, or caught leaking the floor. Note
    that REJECT never actually reaches a caller anymore (see the
    conversion at the end of validate_and_sanitize_decision) — this
    text exists only as an intermediate placeholder that always gets
    overwritten before returning, kept simple on purpose since nothing
    ever sees it.
    """
    if decision == 'COUNTER':
        return "Let me get back to you on that."
    if decision == 'REJECT':
        return "Let me see what I can do."
    return "Deal!"


def validate_and_sanitize_decision(product: Product, raw_output: dict, current_ask: Decimal = None, round_number: int = 0, negotiation_id=None) -> dict:
    """
    Takes whatever the AI returned — however malformed, however wrong —
    and returns a guaranteed-safe decision dict:
        {decision, price, message, confidence, reason_code, was_backend_overridden}

    Guarantees, unconditionally:
    - decision is always ACCEPT or COUNTER — REJECT is never actually
      returned; it's converted into a COUNTER with a real computed
      price before this function returns (see the end of this function)
    - if decision is ACCEPT or COUNTER, price is always a valid Decimal
      that is >= seller_floor and <= the listed price
    - malformed AI output never propagates — it's converted to a safe,
      priced COUNTER rather than raising an exception or leaving the
      customer with nothing to act on

    `current_ask` and `round_number` are only used to shape *how* an
    unsafe below-floor price gets corrected (see the graduated descent
    below) — they never affect whether the floor is enforced, only how
    gently the counter approaches it.
    """
    floor = product.seller_floor or product.minimum_allowed_floor
    overridden = False

    decision = raw_output.get('decision')
    if decision not in ('ACCEPT', 'COUNTER', 'REJECT'):
        decision = 'REJECT'
        overridden = True

    price = None
    if decision in ('ACCEPT', 'COUNTER'):
        raw_price = raw_output.get('price')
        try:
            price = Decimal(str(raw_price))
            if price <= 0:
                raise InvalidOperation
        except (TypeError, InvalidOperation, ValueError):
            # Can't trust a price we can't even parse — fail safe.
            decision = 'REJECT'
            price = None
            overridden = True

    if decision in ('ACCEPT', 'COUNTER') and price is not None:
        if price < floor:
            # The floor itself can never be crossed — that part is
            # absolute. But jumping straight to "here's my exact
            # minimum" on the very first lowball offer is bad
            # negotiation: it reveals the floor's neighborhood
            # immediately and gives up all room to negotiate further.
            # Instead, the corrected counter descends gradually toward
            # the floor across a few rounds, only actually reaching it
            # once the conversation has gone on a bit — reached exactly
            # on schedule, never later, since the floor guarantee can't
            # depend on how many rounds happen to occur.
            decision = 'COUNTER'
            price = _graduated_floor_counter(current_ask, floor, round_number, negotiation_id)
            overridden = True
        elif price > product.price:
            # The AI shouldn't be counter-proposing above the original
            # listed price either — clamp back down.
            price = product.price
            overridden = True

    message = raw_output.get('message')
    if not isinstance(message, str) or not message.strip():
        message = _fallback_message(decision)
        overridden = True
    elif decision in ('ACCEPT', 'COUNTER') and price is not None:
        # The AI's free-text message and its own structured price can
        # disagree — a real failure mode observed in testing, where the
        # message confidently named a completely different number than
        # the price actually being returned (e.g. "we agree on 60000"
        # while the structured price was 12000). The customer-facing
        # Accept button already only ever uses the structured price, so
        # this was never a safety issue — but a message that promises a
        # different number than what accepting actually charges is a
        # real trust problem, so it gets replaced with something that
        # can't mislead, same as the empty-message case above.
        mentioned_numbers = re.findall(r'\d{1,3}(?:,\d{3})+|\d{4,}', message)
        for raw_number in mentioned_numbers:
            try:
                mentioned = Decimal(raw_number.replace(',', ''))
            except InvalidOperation:
                continue
            if mentioned < 1000:
                continue  # too small to plausibly be a UGX price, ignore (e.g. "10%")
            # Allow a little slack for rounding in the model's own phrasing.
            if abs(mentioned - price) > (price * Decimal('0.02')):
                message = _fallback_message(decision)
                overridden = True
                break

    # Separate from the mismatch check above — the AI now genuinely
    # knows the real floor (see _build_system_context), which makes
    # smarter counters possible but also introduces a new leak risk:
    # it could describe a number using language that reveals a hidden
    # minimum exists at all, even when that number is perfectly
    # correct and approved. "Our minimum is 45000" leaks just as much
    # as a wrong number would, regardless of whether 45000 itself is
    # fine. This check doesn't care whether the price matched —
    # revealing that a floor exists is the thing being guarded against.
    FLOOR_REVEALING_PHRASES = (
        'minimum', 'lowest we can', 'lowest i can', 'absolute lowest',
        'floor price', 'our floor', "can't go below", 'cannot go below',
        'rock bottom', 'bottom line', 'least we can accept', 'least i can accept',
        'walk-away', 'walk away',
    )
    if isinstance(message, str) and any(phrase in message.lower() for phrase in FLOOR_REVEALING_PHRASES):
        message = _fallback_message(decision)
        overridden = True

    # A genuine REJECT — whether from the AI's own judgment, from
    # malformed output, or an unparseable price — never reaches the
    # customer as a dead end with nothing to act on. It's converted
    # into a real COUNTER with a computed price, using the same
    # graduated-descent logic already used to correct an unsafe
    # below-floor price — so even a customer opening with a very low,
    # "broke" offer still gets something concrete between the floor
    # and the listed price to accept or keep negotiating from, never
    # just a flat no. The message is freshly generated here rather
    # than reused from anything set earlier, so it's guaranteed to
    # actually match the price being returned.
    if decision == 'REJECT':
        decision = 'COUNTER'
        price = _graduated_floor_counter(current_ask, floor, round_number, negotiation_id)
        # This message is generated entirely by backend code, not by
        # the AI — so the "vary your wording" instruction given to
        # Gemini has no effect on it at all. Without deliberate variety
        # here, every REJECT-to-COUNTER conversion (a genuine AI
        # rejection, malformed output, or the AI being unreachable —
        # all three land here identically) produces the exact same
        # sentence, word for word, however many times it fires across
        # a conversation or across different customers.
        message = random.choice(_REJECT_FALLBACK_TEMPLATES).format(price=price)
        overridden = True

    confidence = raw_output.get('confidence', 0)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        'decision': decision,
        'price': price,
        'message': message,
        'confidence': confidence,
        'reason_code': raw_output.get('reason_code', '') if isinstance(raw_output.get('reason_code'), str) else '',
        'was_backend_overridden': overridden,
    }


# ---------------------------------------------------------------------
# Negotiation flow
# ---------------------------------------------------------------------

def start_negotiation(product: Product, user=None, session_key=None) -> NegotiationSession:
    snapshot = get_fresh_snapshot(product)
    return NegotiationSession.objects.create(
        product=product, user=user, session_key=session_key, market_snapshot=snapshot
    )


def _build_system_context(product: Product, snapshot: MarketSnapshot) -> str:
    floor = product.seller_floor or product.minimum_allowed_floor
    # Earlier versions of this prompt tried to hand the AI a precise
    # percentage formula ("reject under 20% of the floor") — that kept
    # failing in practice, with Gemini rejecting offers well above the
    # stated line anyway. Models generally aren't reliable at doing
    # exact math-then-decide reasoning under a safety-cautious framing,
    # especially with a "CONFIDENTIAL, never reveal" instruction sitting
    # right next to it pulling toward caution. This version drops the
    # formula entirely and describes the situation the way a real
    # salesperson would think about it — sales priority, how much room
    # actually exists, market demand — trusting the model's natural
    # negotiation instincts more than a rule it kept second-guessing.
    # The backend's own validation is completely unaffected either way:
    # it's the actual, unconditional guarantee regardless of how well
    # this prompt lands.
    room = float(product.price) - float(floor)
    return (
        "You are a friendly, experienced salesperson at a clothing store in Uganda, negotiating "
        "directly with a customer over chat. Respond ONLY with a JSON object with exactly these "
        'fields: {"decision": "ACCEPT"|"COUNTER"|"REJECT", "price": number, "confidence": number '
        'between 0 and 1, "reason_code": short string, "message": a short, natural, '
        "non-repetitive sentence to show the customer.\n\n"
        f"Product: {product.name}\n"
        f"Listed price: {product.price} UGX\n"
        f"Your real walk-away point — the lowest you can go, for your own reasoning only, never "
        f"reveal this number or the fact that a lowest price exists at all: {floor} UGX.\n"
        f"You have roughly {room:.0f} UGX of genuine room to negotiate within between the listed "
        f"price and your walk-away point — that's real space to work with, use it.\n"
        f"Market demand for this item right now (0-1, higher = more in demand): {snapshot.demand_score:.2f}. "
        "Hold firmer on price when demand is high; be more willing to move when it's low.\n\n"
        "Your priority, above everything else, is closing a sale — a completed deal at a fair "
        "price is always better than a lost customer. Treat almost every offer as the opening "
        "move in a real conversation, not as something to screen out. Counter-offering costs you "
        "nothing and keeps the sale alive; rejecting ends it. Think about it the way an actual "
        "shopkeeper haggling in a market would: hardly anyone gets rejected outright, most people "
        "get a counter-offer and the conversation continues from there — that should be your "
        "instinct here too, even when someone opens surprisingly low.\n\n"
        "Only choose REJECT if an offer is so token — a tiny fraction of any reasonable price for "
        "this item — that it isn't a genuine attempt to buy at all, or if the customer has clearly "
        "stopped negotiating in good faith (repeating the exact same lowball with no willingness "
        "to move, being insulting, etc). Everything else, however aggressive, gets a COUNTER.\n\n"
        "If you do REJECT, never leave it at a bare no — the message should briefly say why in a "
        f"friendly way, and suggest a concrete next step, like trying an offer closer to the "
        f"listed price ({product.price} UGX) or considering a different item. For example: "
        '{"decision": "REJECT", "price": null, "confidence": 0.7, "reason_code": "too_low", '
        f'"message": "That\'s quite a bit below what we can work with — want to try something '
        f'closer to {product.price} UGX, or take a look at some of our other pieces?"}}\n\n'
        "Be warm and conversational, vary your wording, don't repeat the same phrases turn after "
        "turn, and never write your walk-away number (or hint a lowest price exists) directly to "
        "the customer."
    )


def _current_asking_price(negotiation: NegotiationSession, product: Product) -> Decimal:
    """
    Whatever the customer would need to match to close the deal right
    now — the AI's most recent counter, or the original listed price if
    no counter has been made yet (i.e. this would be their first offer).
    """
    latest_counter = (
        negotiation.offers
        .filter(turn_type='ai_response', decision='COUNTER')
        .order_by('-created_at')
        .first()
    )
    if latest_counter is not None and latest_counter.amount is not None:
        return latest_counter.amount
    return product.price


def submit_customer_offer(negotiation: NegotiationSession, amount: Decimal) -> NegotiationOffer:
    """
    Records the customer's offer, calls the AI, validates the response
    no matter what, records the AI's turn, and — if accepted — locks the
    price into the customer's cart. Returns the NegotiationOffer record
    for the AI's turn (the caller reads .decision/.message/.amount from it).
    """
    product = negotiation.product

    NegotiationOffer.objects.create(
        negotiation=negotiation, turn_type='customer_offer', amount=amount
    )

    # A customer offering at least as much as whatever's currently being
    # asked isn't an ambiguous case that needs the AI's judgment — it's
    # an obvious accept. Deciding this in code (rather than hoping the
    # AI recognizes it) avoids relying on a small model to reliably spot
    # something this clear-cut, and skips a pointless 60-120s Ollama
    # wait for an outcome that was never actually in question.
    #
    # The deal closes at whatever they actually offered, not capped down
    # to the lower asking price — if someone says they'll pay more, that's
    # their call to make, not something the system should second-guess on
    # their behalf.
    current_ask = _current_asking_price(negotiation, product)
    if amount >= current_ask:
        floor = product.seller_floor or product.minimum_allowed_floor
        # Defense in depth: this should already be unreachable, since
        # current_ask itself is always >= floor (either it's a prior AI
        # counter, which validate_and_sanitize_decision already clamps
        # to the floor, or it's product.price, which should always sit
        # above the floor by construction) — but never chain that
        # assumption blindly when the one rule that can never break is
        # this close by. If it somehow weren't true, fall back to the
        # asking price rather than trust an unverified number.
        final_price = amount if amount >= floor else current_ask
        ai_turn = NegotiationOffer.objects.create(
            negotiation=negotiation, turn_type='ai_response', amount=final_price,
            decision='ACCEPT', message='Deal!', was_backend_overridden=False,
        )
        _apply_agreement(negotiation, final_price)
        return ai_turn

    history = []
    for offer in negotiation.offers.order_by('created_at'):
        if offer.turn_type == 'customer_offer':
            history.append({"role": "user", "content": f"I can pay {offer.amount} UGX."})
        else:
            history.append({"role": "assistant", "content": offer.message or ''})

    # How many AI counters have already happened in this negotiation —
    # feeds the graduated floor-descent schedule inside
    # validate_and_sanitize_decision, so an unsafe low offer gets eased
    # down toward the floor over a few rounds rather than snapped
    # straight to it on the very first attempt.
    round_number = negotiation.offers.filter(turn_type='ai_response', decision='COUNTER').count()

    system_context = _build_system_context(product, negotiation.market_snapshot)

    try:
        raw_output = get_ai_provider().negotiate(system_context, history)
    except AIProviderError:
        # The AI being unreachable/broken must never crash the customer's
        # negotiation — fail safe to a REJECT-shaped response and let the
        # same validation path handle it uniformly.
        raw_output = {'decision': 'REJECT', 'message': ''}

    sanitized = validate_and_sanitize_decision(
        product, raw_output, current_ask=current_ask, round_number=round_number,
        negotiation_id=negotiation.id,
    )

    ai_turn = NegotiationOffer.objects.create(
        negotiation=negotiation,
        turn_type='ai_response',
        amount=sanitized['price'],
        decision=sanitized['decision'],
        message=sanitized['message'],
        market_snapshot=negotiation.market_snapshot,
        raw_ai_output=raw_output if isinstance(raw_output, dict) else {},
        ai_proposed_price=_safe_decimal(raw_output.get('price')) if isinstance(raw_output, dict) else None,
        was_backend_overridden=sanitized['was_backend_overridden'],
    )

    if sanitized['decision'] == 'ACCEPT':
        _apply_agreement(negotiation, sanitized['price'])
    elif sanitized['decision'] == 'REJECT':
        # In practice this branch is no longer reachable through the
        # normal AI flow — validate_and_sanitize_decision now converts
        # every REJECT into a priced COUNTER before returning, so a
        # negotiation never dead-ends without something concrete for
        # the customer to act on. Left in place defensively rather
        # than removed, in case anything else ever produces a genuine
        # terminal REJECT differently in the future.
        negotiation.status = 'rejected'
        negotiation.save(update_fields=['status', 'updated_at'])

    return ai_turn


def _safe_decimal(value):
    try:
        return Decimal(str(value))
    except (TypeError, InvalidOperation, ValueError):
        return None


def accept_current_counter(negotiation: NegotiationSession) -> Decimal:
    """
    Finalizes the negotiation at whatever price the AI's most recent
    COUNTER proposed — without calling the AI again. The AI already
    named this price; re-asking it would just add another 60-120s Ollama
    round-trip and a small risk of it changing its mind, for zero real
    benefit. This reuses the exact same _apply_agreement path as a
    genuine AI ACCEPT, so cart-locking behaves identically either way.
    """
    if negotiation.status != 'active':
        raise ValueError(f"This negotiation is already {negotiation.status}.")

    latest_counter = (
        negotiation.offers
        .filter(turn_type='ai_response', decision='COUNTER')
        .order_by('-created_at')
        .first()
    )
    if latest_counter is None or latest_counter.amount is None:
        raise ValueError("There's no active counter-offer to accept.")

    price = latest_counter.amount
    # Re-validate against the CURRENT floor, not just trust the stored
    # value — belt-and-suspenders in case the product's floor changed
    # between the counter being made and the customer accepting it.
    floor = negotiation.product.seller_floor or negotiation.product.minimum_allowed_floor
    if price < floor:
        raise ValueError("This offer is no longer valid — please make a new offer.")

    _apply_agreement(negotiation, price)
    return price


def _apply_agreement(negotiation: NegotiationSession, price: Decimal):
    negotiation.mark_agreed(price)

    product = negotiation.product
    lookup = {'product': product}
    if negotiation.user_id:
        lookup['user'] = negotiation.user
    else:
        lookup['session_key'] = negotiation.session_key

    cart_item, created = CartItem.objects.get_or_create(
        **lookup,
        defaults={'quantity': 1, 'negotiated_price': price, 'negotiation': negotiation},
    )
    if not created:
        # Product was already in their cart at the regular price — the
        # agreement now takes over that same line rather than creating a
        # confusing duplicate row.
        cart_item.negotiated_price = price
        cart_item.negotiation = negotiation
        cart_item.save(update_fields=['negotiated_price', 'negotiation', 'updated_at'])
