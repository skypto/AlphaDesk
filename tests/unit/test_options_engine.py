from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from packages.domain.options import (
    Greeks,
    LegSide,
    LiquidityPolicy,
    OptionContract,
    OptionLeg,
    OptionQuote,
    OptionType,
    StructureType,
    UnderlyingLeg,
)
from packages.options.engine import InvalidOptionStructure, build_structure, expiration_payoff
from packages.options.liquidity import evaluate_contract

AS_OF = datetime(2026, 9, 1, 14, tzinfo=UTC)
EXPIRY = date(2026, 9, 25)


def contract(
    option_type: OptionType,
    strike: str,
    *,
    bid: str = "2.00",
    ask: str = "2.20",
    quoted_at: datetime = AS_OF,
    open_interest: int | None = 500,
    greeks: Greeks | None = None,
) -> OptionContract:
    strike_decimal = Decimal(strike)
    suffix = "C" if option_type is OptionType.CALL else "P"
    return OptionContract(
        contract_id=f"id-{suffix}-{strike}",
        symbol=f"XYZ260925{suffix}{int(strike_decimal * 1000):08d}",
        underlying_symbol="XYZ",
        expiration=EXPIRY,
        strike=strike_decimal,
        option_type=option_type,
        tradable=True,
        quote=OptionQuote(
            bid=Decimal(bid),
            ask=Decimal(ask),
            bid_size=Decimal("20"),
            ask_size=Decimal("25"),
            quoted_at=quoted_at,
            open_interest=open_interest,
            volume=100,
            implied_volatility=Decimal("0.25"),
            greeks=greeks
            or Greeks(
                delta=Decimal("0.5"),
                gamma=Decimal("0.1"),
                theta=Decimal("-0.02"),
                vega=Decimal("0.15"),
            ),
        ),
    )


def leg(option_type: OptionType, strike: str, side: LegSide, price: str) -> OptionLeg:
    return OptionLeg(
        contract=contract(option_type, strike),
        side=side,
        entry_price=Decimal(price),
    )


@pytest.mark.parametrize(
    ("structure_type", "legs", "underlying", "max_loss", "max_profit", "break_even"),
    [
        (
            StructureType.LONG_CALL,
            (leg(OptionType.CALL, "100", LegSide.LONG, "5"),),
            None,
            "500",
            None,
            "105",
        ),
        (
            StructureType.LONG_PUT,
            (leg(OptionType.PUT, "100", LegSide.LONG, "4"),),
            None,
            "400",
            "9600",
            "96",
        ),
        (
            StructureType.BULL_CALL_DEBIT_SPREAD,
            (
                leg(OptionType.CALL, "100", LegSide.LONG, "5"),
                leg(OptionType.CALL, "110", LegSide.SHORT, "2"),
            ),
            None,
            "300",
            "700",
            "103",
        ),
        (
            StructureType.BEAR_PUT_DEBIT_SPREAD,
            (
                leg(OptionType.PUT, "110", LegSide.LONG, "8"),
                leg(OptionType.PUT, "100", LegSide.SHORT, "3"),
            ),
            None,
            "500",
            "500",
            "105",
        ),
        (
            StructureType.BULL_PUT_CREDIT_SPREAD,
            (
                leg(OptionType.PUT, "100", LegSide.SHORT, "5"),
                leg(OptionType.PUT, "90", LegSide.LONG, "2"),
            ),
            None,
            "700",
            "300",
            "97",
        ),
        (
            StructureType.BEAR_CALL_CREDIT_SPREAD,
            (
                leg(OptionType.CALL, "100", LegSide.SHORT, "5"),
                leg(OptionType.CALL, "110", LegSide.LONG, "2"),
            ),
            None,
            "700",
            "300",
            "103",
        ),
        (
            StructureType.PROTECTIVE_PUT,
            (leg(OptionType.PUT, "90", LegSide.LONG, "2"),),
            UnderlyingLeg(symbol="XYZ", shares=100, entry_price=Decimal("100")),
            "1200",
            None,
            "102",
        ),
        (
            StructureType.PROTECTIVE_PUT_SPREAD,
            (
                leg(OptionType.PUT, "95", LegSide.LONG, "3"),
                leg(OptionType.PUT, "85", LegSide.SHORT, "1"),
            ),
            UnderlyingLeg(symbol="XYZ", shares=100, entry_price=Decimal("100")),
            "9200",
            None,
            "102",
        ),
    ],
)
def test_all_approved_structures_have_deterministic_bounds(
    structure_type: StructureType,
    legs: tuple[OptionLeg, ...],
    underlying: UnderlyingLeg | None,
    max_loss: str,
    max_profit: str | None,
    break_even: str,
) -> None:
    structure = build_structure(structure_type, legs, underlying=underlying)

    assert structure.max_loss == Decimal(max_loss)
    assert structure.max_profit == (None if max_profit is None else Decimal(max_profit))
    assert structure.break_evens == (Decimal(break_even),)
    assert expiration_payoff(structure, structure.break_evens[0]) == 0


def test_payoff_matches_declared_vertical_bounds() -> None:
    structure = build_structure(
        StructureType.BULL_CALL_DEBIT_SPREAD,
        (
            leg(OptionType.CALL, "100", LegSide.LONG, "5"),
            leg(OptionType.CALL, "110", LegSide.SHORT, "2"),
        ),
    )

    assert expiration_payoff(structure, Decimal("0")) == -structure.max_loss
    assert expiration_payoff(structure, Decimal("1000")) == structure.max_profit


def test_greeks_are_signed_scaled_and_include_protective_shares() -> None:
    long_put = leg(OptionType.PUT, "95", LegSide.LONG, "3")
    short_put = leg(OptionType.PUT, "85", LegSide.SHORT, "1")
    structure = build_structure(
        StructureType.PROTECTIVE_PUT_SPREAD,
        (long_put, short_put),
        quantity=2,
        underlying=UnderlyingLeg(symbol="XYZ", shares=200, entry_price=Decimal("100")),
    )

    assert structure.greeks.delta == Decimal("200")
    assert structure.greeks.gamma == 0
    assert structure.greeks.theta == 0
    assert structure.greeks.vega == 0


@pytest.mark.parametrize(
    ("structure_type", "legs", "message"),
    [
        (
            StructureType.LONG_CALL,
            (leg(OptionType.CALL, "100", LegSide.SHORT, "5"),),
            "one long leg",
        ),
        (
            StructureType.BULL_CALL_DEBIT_SPREAD,
            (
                leg(OptionType.CALL, "110", LegSide.LONG, "5"),
                leg(OptionType.CALL, "100", LegSide.SHORT, "2"),
            ),
            "bull call strikes",
        ),
        (
            StructureType.BULL_PUT_CREDIT_SPREAD,
            (
                leg(OptionType.PUT, "100", LegSide.LONG, "5"),
                leg(OptionType.PUT, "90", LegSide.SHORT, "2"),
            ),
            "credit must",
        ),
    ],
)
def test_undefined_or_malformed_structures_are_rejected(
    structure_type: StructureType, legs: tuple[OptionLeg, ...], message: str
) -> None:
    with pytest.raises(InvalidOptionStructure, match=message):
        build_structure(structure_type, legs)


def test_ratio_and_expiration_mismatches_are_rejected() -> None:
    ratio_leg = leg(OptionType.CALL, "100", LegSide.LONG, "5").model_copy(update={"ratio": 2})
    with pytest.raises(InvalidOptionStructure, match="ratio"):
        build_structure(StructureType.LONG_CALL, (ratio_leg,))

    later = leg(OptionType.CALL, "110", LegSide.SHORT, "2")
    later = later.model_copy(
        update={"contract": later.contract.model_copy(update={"expiration": date(2026, 10, 2)})}
    )
    with pytest.raises(InvalidOptionStructure, match="expiration mismatch"):
        build_structure(
            StructureType.BULL_CALL_DEBIT_SPREAD,
            (leg(OptionType.CALL, "100", LegSide.LONG, "5"), later),
        )


def test_contract_liquidity_eligibility_is_deterministic() -> None:
    policy = LiquidityPolicy(
        supported_underlyings=frozenset({"XYZ"}),
        min_dte=14,
        max_dte=45,
        max_spread_ratio=Decimal("0.15"),
        min_open_interest=100,
        max_quote_age_seconds=30,
    )
    eligible = evaluate_contract(
        contract(OptionType.CALL, "100"),
        underlying_price=Decimal("100"),
        policy=policy,
        as_of=AS_OF,
    )
    assert eligible.eligible
    assert eligible.reasons == ()

    bad = contract(
        OptionType.CALL,
        "150",
        bid="1",
        ask="2",
        quoted_at=datetime(2026, 9, 1, 13, 58, tzinfo=UTC),
        open_interest=None,
    )
    bad = bad.model_copy(update={"quote": bad.quote.model_copy(update={"greeks": None})})
    result = evaluate_contract(bad, underlying_price=Decimal("100"), policy=policy, as_of=AS_OF)
    assert not result.eligible
    assert set(result.reasons) == {
        "spread_too_wide",
        "open_interest_unavailable",
        "stale_quote",
        "strike_too_distant",
        "greeks_unavailable",
    }
