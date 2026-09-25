from datetime import date

from app.rules.engine import DecisionStatus
from app.rules.transport import (
    PassengerGroup,
    PricingMethod,
    TransportInput,
    TransportRouteCode,
    TransportServiceItem,
    evaluate_transport,
)


def make_transport(price: int, **kwargs) -> TransportInput:
    defaults = dict(
        service_name="2027학년도 통학차량 임차용역",
        estimated_price=price,
        planned_date=date(2026, 9, 25),
        passenger_group=PassengerGroup.ELEMENTARY,
        vehicle_count=1,
        seat_capacity_min=45,
        service_item=TransportServiceItem.SCHOOL_TRANSPORT,
        pricing_method=PricingMethod.TOTAL,
        operation_days=190,
        driver_included=True,
        attendant_included=True,
        regional_restriction_requested=True,
    )
    defaults.update(kwargs)
    return TransportInput(**defaults)


def test_transport_under_100m_uses_small_value_engine() -> None:
    result = evaluate_transport(make_transport(38_450_000))
    assert result.route_code == TransportRouteCode.SMALL_VALUE
    assert result.minimum_quote_rate == 0.88


def test_transport_at_100m_stays_small_value() -> None:
    result = evaluate_transport(make_transport(100_000_000))
    assert result.route_code == TransportRouteCode.SMALL_VALUE


def test_transport_over_100m_under_500m_uses_current_sme_rate() -> None:
    result = evaluate_transport(make_transport(151_200_000))
    assert result.route_code == TransportRouteCode.COMPETITIVE_UNDER_500M
    assert result.minimum_quote_rate == 0.89995
    assert result.qualification_score == 88
    assert result.status == DecisionStatus.CONDITIONAL


def test_transport_just_under_500m_uses_under_500m_band() -> None:
    result = evaluate_transport(make_transport(499_999_999))
    assert result.route_code == TransportRouteCode.COMPETITIVE_UNDER_500M
    assert result.minimum_quote_rate == 0.89995


def test_transport_at_500m_moves_to_large_band_review() -> None:
    result = evaluate_transport(make_transport(500_000_000))
    assert result.route_code == TransportRouteCode.COMPETITIVE_500M_OR_MORE
    assert result.status == DecisionStatus.REVIEW


def test_elementary_flags_child_school_bus_requirements() -> None:
    result = evaluate_transport(make_transport(50_000_000))
    assert "신고" in result.child_school_bus_status
    assert any("어린이통학버스 신고증명서" in item for item in result.required_documents)


def test_no_attendant_warns_for_elementary() -> None:
    result = evaluate_transport(make_transport(50_000_000, attendant_included=False))
    assert any("보호자" in warning for warning in result.warnings)


def test_high_school_does_not_auto_require_child_bus() -> None:
    result = evaluate_transport(
        make_transport(150_000_000, passenger_group=PassengerGroup.HIGH)
    )
    assert "비대상" in result.child_school_bus_status


def test_unit_contract_adds_estimated_price_check() -> None:
    result = evaluate_transport(
        make_transport(80_000_000, pricing_method=PricingMethod.UNIT)
    )
    assert any("추정단가" in item for item in result.required_checks)


def test_old_date_requires_historical_review() -> None:
    result = evaluate_transport(
        make_transport(80_000_000, planned_date=date(2026, 7, 26))
    )
    assert result.route_code == TransportRouteCode.HISTORICAL_REVIEW


def test_direct_production_required_at_10m() -> None:
    result = evaluate_transport(make_transport(10_000_000))
    assert result.direct_production_status == "직접생산확인증명서 필요"
    assert any("7811189902" in item for item in result.required_documents)


def test_direct_production_not_mandatory_below_10m_amount_threshold() -> None:
    result = evaluate_transport(make_transport(9_999_999))
    assert "1천만원 미만" in result.direct_production_status


def test_other_road_passenger_service_is_known_sme_competition_item() -> None:
    result = evaluate_transport(
        make_transport(
            120_000_000,
            service_item=TransportServiceItem.OTHER_ROAD_PASSENGER,
        )
    )
    assert result.service_item_code == "7811189904"
    assert result.minimum_quote_rate == 0.89995


def test_undetermined_item_does_not_auto_apply_89995() -> None:
    result = evaluate_transport(
        make_transport(
            120_000_000,
            service_item=TransportServiceItem.UNDETERMINED,
        )
    )
    assert result.minimum_quote_rate is None
    assert any("89.995" in warning for warning in result.warnings)
