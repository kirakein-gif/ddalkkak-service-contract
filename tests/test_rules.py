from datetime import date

import pytest

from app.rules.engine import (
    ContractInput,
    DecisionStatus,
    RouteCode,
    VendorCategory,
    evaluate_contract,
)


def test_standard_one_person_quote_at_20m() -> None:
    result = evaluate_contract(
        ContractInput(service_name="소규모 점검용역", estimated_price=20_000_000)
    )
    assert result.route_code == RouteCode.ONE_PERSON_QUOTE
    assert result.status == DecisionStatus.CONFIRMED
    assert result.quote_count_min == 1


def test_two_person_quote_over_20m() -> None:
    result = evaluate_contract(
        ContractInput(service_name="일반용역", estimated_price=20_000_001)
    )
    assert result.route_code == RouteCode.TWO_PERSON_E_QUOTE
    assert result.minimum_quote_rate == 0.88
    assert result.designated_system_required is True
    assert result.minimum_announcement_days == 3


def test_special_entity_one_person_quote_at_50m() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="여성기업 대상 용역",
            estimated_price=50_000_000,
            vendor_category=VendorCategory.WOMEN,
        )
    )
    assert result.route_code == RouteCode.ONE_PERSON_QUOTE
    assert result.status == DecisionStatus.CONFIRMED


def test_special_entity_over_50m_moves_to_two_person_review() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="여성기업 대상 용역",
            estimated_price=50_000_001,
            vendor_category=VendorCategory.WOMEN,
        )
    )
    assert result.route_code == RouteCode.TWO_PERSON_E_QUOTE


def test_social_enterprise_requires_extra_confirmation() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="사회적기업 용역",
            estimated_price=40_000_000,
            vendor_category=VendorCategory.SOCIAL_ENTERPRISE,
            special_entity_requirements_confirmed=False,
        )
    )
    assert result.route_code == RouteCode.ONE_PERSON_QUOTE
    assert result.status == DecisionStatus.CONDITIONAL
    assert result.warnings


def test_service_at_100m_stays_in_small_value_review() -> None:
    result = evaluate_contract(
        ContractInput(service_name="통학차량 임차", estimated_price=100_000_000)
    )
    assert result.route_code == RouteCode.TWO_PERSON_E_QUOTE


def test_service_over_100m_moves_to_competitive_review() -> None:
    result = evaluate_contract(
        ContractInput(service_name="대규모 일반용역", estimated_price=100_000_001)
    )
    assert result.route_code == RouteCode.COMPETITIVE_REVIEW
    assert result.status == DecisionStatus.REVIEW


def test_special_knowledge_marks_small_business_exception_review() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="전문 안전진단",
            estimated_price=60_000_000,
            special_knowledge_or_qualification=True,
        )
    )
    assert result.route_code == RouteCode.TWO_PERSON_E_QUOTE
    assert result.small_business_restriction == "예외 검토"


def test_proposal_evaluation_takes_priority_over_amount() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="수학여행 위탁용역",
            estimated_price=49_000_000,
            requires_proposal_evaluation=True,
        )
    )
    assert result.route_code == RouteCode.TWO_STAGE_REVIEW


def test_technical_service_is_separated() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="감리용역",
            estimated_price=30_000_000,
            technical_service=True,
        )
    )
    assert result.route_code == RouteCode.TECHNICAL_SERVICE_REVIEW


def test_historical_date_requires_old_rule_review() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="과거 계약",
            estimated_price=10_000_000,
            planned_date=date(2026, 6, 30),
        )
    )
    assert result.route_code == RouteCode.HISTORICAL_RULE_REVIEW


def test_non_positive_estimated_price_is_invalid() -> None:
    with pytest.raises(ValueError):
        evaluate_contract(
            ContractInput(service_name="오류", estimated_price=0)
        )
