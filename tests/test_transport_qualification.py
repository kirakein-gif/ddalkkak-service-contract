from decimal import Decimal

import pytest

from app.rules.transport_qualification import (
    CreditRating,
    QualificationInput,
    SafetyGrade,
    calculate_performance_score,
    calculate_price_score,
    calculate_transport_qualification,
)


def make_input(**kwargs):
    data = dict(
        estimated_price=150_000_000,
        expected_price=165_000_000,
        bid_price=148_491_750,  # 89.995%
        performance_base_amount=150_000_000,
        equivalent_performance_amount=150_000_000,
        similar_performance_amount=0,
        credit_rating=CreditRating.A_MINUS_OR_BETTER,
        safety_grade=SafetyGrade.GRADE_1,
        reputation_score=Decimal("0"),
        disqualification_reason=False,
    )
    data.update(kwargs)
    return QualificationInput(**data)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (150_000_000, 10),
        (105_000_000, 9),
        (60_000_000, 8),
        (15_000_000, 7),
        (14_999_999, 0),
    ],
)
def test_equivalent_performance_grades(amount, expected):
    score, _, _ = calculate_performance_score(150_000_000, amount, 0)
    assert float(score) == expected


def test_similar_performance_can_supplement_but_total_is_capped():
    score, _, _ = calculate_performance_score(
        100_000_000,
        70_000_000,
        100_000_000,
    )
    assert float(score) == 10


def test_price_score_at_89995_is_58_after_ratio_rounding():
    score, raw_ratio = calculate_price_score(100_000_000, 89_995_000)
    assert float(score) == 58
    assert raw_ratio == Decimal("0.89995")


def test_price_score_at_93_percent_is_full_70():
    score, _ = calculate_price_score(100_000_000, 93_000_000)
    assert float(score) == 70


def test_price_score_at_or_above_96_percent_is_capped_at_58():
    score, _ = calculate_price_score(100_000_000, 98_000_000)
    assert float(score) == 58


def test_full_ability_and_floor_bid_passes_at_88():
    result = calculate_transport_qualification(make_input())
    assert result.passed is True
    assert result.total_score == 88
    assert result.price_score == 58


def test_below_floor_fails_even_if_score_rounds_close():
    result = calculate_transport_qualification(
        make_input(bid_price=148_491_000)
    )
    assert result.passed is False
    assert result.meets_minimum_bid_rate is False


def test_credit_rating_mapping():
    result = calculate_transport_qualification(
        make_input(credit_rating=CreditRating.BBB_ZERO)
    )
    assert result.business_score == 9.6


def test_safety_grade_mapping():
    result = calculate_transport_qualification(
        make_input(safety_grade=SafetyGrade.GRADE_4)
    )
    assert result.safety_score == 4


def test_positive_reputation_only_fills_ability_cap():
    result = calculate_transport_qualification(
        make_input(
            equivalent_performance_amount=105_000_000,
            reputation_score=Decimal("4.25"),
        )
    )
    assert result.ability_score_before_reputation == 29
    assert result.reputation_applied == 1
    assert result.ability_score_after_reputation == 30


def test_negative_reputation_reduces_ability():
    result = calculate_transport_qualification(
        make_input(reputation_score=Decimal("-2"))
    )
    assert result.ability_score_after_reputation == 28
    assert result.passed is False


def test_disqualification_penalty_makes_result_fail():
    result = calculate_transport_qualification(
        make_input(disqualification_reason=True)
    )
    assert result.disqualification_penalty == -20
    assert result.passed is False


def test_500m_or_more_not_supported_yet():
    with pytest.raises(ValueError):
        calculate_transport_qualification(
            make_input(estimated_price=500_000_000)
        )
