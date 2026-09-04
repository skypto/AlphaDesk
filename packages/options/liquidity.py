from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from packages.domain.options import (
    ZERO,
    EligibilityResult,
    LiquidityPolicy,
    OptionContract,
)


def evaluate_contract(
    contract: OptionContract,
    *,
    underlying_price: Decimal,
    policy: LiquidityPolicy,
    as_of: datetime,
) -> EligibilityResult:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    as_of = as_of.astimezone(UTC)
    reasons: list[str] = []
    quote = contract.quote
    dte = (contract.expiration - as_of.date()).days

    if contract.underlying_symbol not in policy.supported_underlyings:
        reasons.append("unsupported_underlying")
    if not contract.tradable:
        reasons.append("not_tradable")
    if not policy.min_dte <= dte <= policy.max_dte:
        reasons.append("dte_out_of_range")
    if quote.bid <= ZERO or quote.ask <= ZERO:
        reasons.append("non_executable_quote")
    spread_ratio = quote.spread_ratio
    if spread_ratio is None or spread_ratio > policy.max_spread_ratio:
        reasons.append("spread_too_wide")
    if quote.bid_size < policy.min_quote_size or quote.ask_size < policy.min_quote_size:
        reasons.append("quote_size_too_small")
    if policy.min_open_interest is not None:
        if quote.open_interest is None:
            reasons.append("open_interest_unavailable")
        elif quote.open_interest < policy.min_open_interest:
            reasons.append("open_interest_too_low")
    age = (as_of - quote.quoted_at.astimezone(UTC)).total_seconds()
    if age < 0 or age > policy.max_quote_age_seconds:
        reasons.append("stale_quote")
    if underlying_price <= ZERO:
        reasons.append("invalid_underlying_price")
    else:
        distance = abs(contract.strike - underlying_price) / underlying_price
        if distance > policy.max_strike_distance_ratio:
            reasons.append("strike_too_distant")
    if policy.require_greeks and quote.greeks is None:
        reasons.append("greeks_unavailable")

    return EligibilityResult(eligible=not reasons, reasons=tuple(reasons))
