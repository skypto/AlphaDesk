from __future__ import annotations

from decimal import Decimal

from packages.domain.options import (
    ZERO,
    Greeks,
    LegSide,
    OptionLeg,
    OptionStructure,
    OptionType,
    StructureType,
    UnderlyingLeg,
)


class InvalidOptionStructure(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidOptionStructure(message)


def _validate_common(legs: tuple[OptionLeg, ...]) -> tuple[str, Decimal]:
    _require(bool(legs), "at least one option leg is required")
    first = legs[0].contract
    for leg in legs:
        _require(leg.ratio == 1, "ratio structures are not supported")
        _require(leg.contract.underlying_symbol == first.underlying_symbol, "underlying mismatch")
        _require(leg.contract.expiration == first.expiration, "expiration mismatch")
        _require(leg.contract.multiplier == first.multiplier, "multiplier mismatch")
    return first.underlying_symbol, Decimal(first.multiplier)


def _premium(legs: tuple[OptionLeg, ...]) -> Decimal:
    return sum((leg.side.sign * leg.entry_price * leg.ratio for leg in legs), ZERO)


def aggregate_greeks(
    legs: tuple[OptionLeg, ...], *, quantity: int, underlying: UnderlyingLeg | None
) -> Greeks:
    totals = {name: ZERO for name in ("delta", "gamma", "theta", "vega")}
    for leg in legs:
        greeks = leg.contract.quote.greeks
        _require(greeks is not None, f"Greeks unavailable for {leg.contract.symbol}")
        scale = leg.side.sign * leg.ratio * quantity * leg.contract.multiplier
        for name in totals:
            totals[name] += getattr(greeks, name) * scale
    if underlying is not None:
        totals["delta"] += Decimal(underlying.shares)
    return Greeks(**totals)


def build_structure(
    structure_type: StructureType,
    legs: tuple[OptionLeg, ...],
    *,
    quantity: int = 1,
    underlying: UnderlyingLeg | None = None,
) -> OptionStructure:
    symbol, multiplier = _validate_common(legs)
    _require(quantity >= 1, "quantity must be positive")
    premium = _premium(legs)
    scale = multiplier * quantity
    strikes = [leg.contract.strike for leg in legs]
    max_profit: Decimal | None

    if structure_type in {StructureType.LONG_CALL, StructureType.LONG_PUT}:
        wanted = OptionType.CALL if structure_type is StructureType.LONG_CALL else OptionType.PUT
        _require(len(legs) == 1 and legs[0].side is LegSide.LONG, "requires one long leg")
        _require(legs[0].contract.option_type is wanted, f"requires one long {wanted.value}")
        _require(underlying is None, "underlying leg is not allowed")
        _require(premium > ZERO, "long option must be a debit")
        max_loss = premium * scale
        if wanted is OptionType.CALL:
            max_profit = None
            break_evens = (strikes[0] + premium,)
        else:
            max_profit = max((strikes[0] - premium) * scale, ZERO)
            break_evens = (strikes[0] - premium,)
    elif structure_type in {
        StructureType.BULL_CALL_DEBIT_SPREAD,
        StructureType.BEAR_PUT_DEBIT_SPREAD,
        StructureType.BULL_PUT_CREDIT_SPREAD,
        StructureType.BEAR_CALL_CREDIT_SPREAD,
    }:
        _require(len(legs) == 2, "vertical spread requires exactly two legs")
        _require(
            {leg.side for leg in legs} == {LegSide.LONG, LegSide.SHORT},
            "requires long and short legs",
        )
        _require(underlying is None, "underlying leg is not allowed")
        wanted = (
            OptionType.CALL
            if structure_type
            in {StructureType.BULL_CALL_DEBIT_SPREAD, StructureType.BEAR_CALL_CREDIT_SPREAD}
            else OptionType.PUT
        )
        _require(all(leg.contract.option_type is wanted for leg in legs), "option type mismatch")
        long_leg = next(leg for leg in legs if leg.side is LegSide.LONG)
        short_leg = next(leg for leg in legs if leg.side is LegSide.SHORT)
        width = abs(long_leg.contract.strike - short_leg.contract.strike)
        _require(width > ZERO, "spread width must be positive")
        is_debit = structure_type in {
            StructureType.BULL_CALL_DEBIT_SPREAD,
            StructureType.BEAR_PUT_DEBIT_SPREAD,
        }
        if is_debit:
            _require(premium > ZERO and premium < width, "debit must be positive and below width")
            if structure_type is StructureType.BULL_CALL_DEBIT_SPREAD:
                _require(
                    long_leg.contract.strike < short_leg.contract.strike,
                    "bull call strikes invalid",
                )
                break_evens = (long_leg.contract.strike + premium,)
            else:
                _require(
                    long_leg.contract.strike > short_leg.contract.strike, "bear put strikes invalid"
                )
                break_evens = (long_leg.contract.strike - premium,)
            max_loss = premium * scale
            max_profit = (width - premium) * scale
        else:
            credit = -premium
            _require(credit > ZERO and credit < width, "credit must be positive and below width")
            if structure_type is StructureType.BULL_PUT_CREDIT_SPREAD:
                _require(
                    short_leg.contract.strike > long_leg.contract.strike, "bull put strikes invalid"
                )
                break_evens = (short_leg.contract.strike - credit,)
            else:
                _require(
                    short_leg.contract.strike < long_leg.contract.strike,
                    "bear call strikes invalid",
                )
                break_evens = (short_leg.contract.strike + credit,)
            max_loss = (width - credit) * scale
            max_profit = credit * scale
    elif structure_type in {StructureType.PROTECTIVE_PUT, StructureType.PROTECTIVE_PUT_SPREAD}:
        _require(underlying is not None, "protective structure requires an underlying leg")
        assert underlying is not None
        _require(underlying.symbol == symbol, "underlying symbol mismatch")
        _require(
            underlying.shares == int(multiplier) * quantity,
            "protective shares must match contracts",
        )
        _require(
            all(leg.contract.option_type is OptionType.PUT for leg in legs), "requires put legs"
        )
        _require(premium > ZERO, "protective structure must be a net debit")
        if structure_type is StructureType.PROTECTIVE_PUT:
            _require(len(legs) == 1 and legs[0].side is LegSide.LONG, "requires one long put")
            floor = legs[0].contract.strike
        else:
            _require(len(legs) == 2, "protective put spread requires two legs")
            _require(
                {leg.side for leg in legs} == {LegSide.LONG, LegSide.SHORT},
                "requires long and short puts",
            )
            long_leg = next(leg for leg in legs if leg.side is LegSide.LONG)
            short_leg = next(leg for leg in legs if leg.side is LegSide.SHORT)
            _require(
                long_leg.contract.strike > short_leg.contract.strike,
                "protective put spread strikes invalid",
            )
            floor = long_leg.contract.strike - short_leg.contract.strike
        max_loss = max((underlying.entry_price + premium - floor) * scale, ZERO)
        max_profit = None
        break_evens = (underlying.entry_price + premium,)
    else:  # pragma: no cover - enum makes this defensive only
        raise InvalidOptionStructure("unsupported structure")

    _require(max_loss >= ZERO, "worst-case loss must be bounded")
    return OptionStructure(
        structure_type=structure_type,
        quantity=quantity,
        legs=legs,
        underlying=underlying,
        net_premium_per_share=premium,
        max_loss=max_loss,
        max_profit=max_profit,
        break_evens=break_evens,
        greeks=aggregate_greeks(legs, quantity=quantity, underlying=underlying),
    )


def expiration_payoff(structure: OptionStructure, underlying_price: Decimal) -> Decimal:
    _require(underlying_price >= ZERO, "underlying price cannot be negative")
    payoff = ZERO
    for leg in structure.legs:
        strike = leg.contract.strike
        intrinsic = (
            max(underlying_price - strike, ZERO)
            if leg.contract.option_type is OptionType.CALL
            else max(strike - underlying_price, ZERO)
        )
        payoff += (
            leg.side.sign * intrinsic * leg.ratio * leg.contract.multiplier * structure.quantity
        )
        payoff -= (
            leg.side.sign
            * leg.entry_price
            * leg.ratio
            * leg.contract.multiplier
            * structure.quantity
        )
    if structure.underlying is not None:
        payoff += (
            underlying_price - structure.underlying.entry_price
        ) * structure.underlying.shares
    return payoff
