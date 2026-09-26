"""여객 육상운송용역 적격심사 계산기.

현재 구현 범위:
- 2026-07-27 이후 최초 입찰공고
- 조달청 일반용역 적격심사 세부기준 [별표 5]
- 추정가격 5억원 미만 여객 육상운송용역

신인도는 [별표 11]의 세부항목이 많아 우선 사용자가 계산한 최종 가감점을 입력받는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum


PASS_SCORE = Decimal("88")
PERFORMANCE_CAP = Decimal("10")
BUSINESS_CAP = Decimal("10")
SAFETY_CAP = Decimal("10")
ABILITY_CAP = Decimal("30")
PRICE_CAP = Decimal("70")
MINIMUM_BID_RATE = Decimal("0.89995")
MAX_ESTIMATED_PRICE = 500_000_000


class CreditRating(StrEnum):
    A_MINUS_OR_BETTER = "A_MINUS_OR_BETTER"
    BBB_PLUS = "BBB_PLUS"
    BBB_ZERO = "BBB_ZERO"
    BBB_MINUS = "BBB_MINUS"
    BB_PLUS_OR_ZERO = "BB_PLUS_OR_ZERO"
    BB_MINUS = "BB_MINUS"
    B_RANGE = "B_RANGE"
    CCC_PLUS_OR_BELOW = "CCC_PLUS_OR_BELOW"


CREDIT_SCORES = {
    CreditRating.A_MINUS_OR_BETTER: Decimal("10"),
    CreditRating.BBB_PLUS: Decimal("9.8"),
    CreditRating.BBB_ZERO: Decimal("9.6"),
    CreditRating.BBB_MINUS: Decimal("9.4"),
    CreditRating.BB_PLUS_OR_ZERO: Decimal("9.2"),
    CreditRating.BB_MINUS: Decimal("9.0"),
    CreditRating.B_RANGE: Decimal("8.8"),
    CreditRating.CCC_PLUS_OR_BELOW: Decimal("7.0"),
}


class SafetyGrade(StrEnum):
    GRADE_1 = "GRADE_1"
    GRADE_2 = "GRADE_2"
    GRADE_3 = "GRADE_3"
    GRADE_4 = "GRADE_4"
    GRADE_5_OR_E = "GRADE_5_OR_E"


SAFETY_SCORES = {
    SafetyGrade.GRADE_1: Decimal("10"),
    SafetyGrade.GRADE_2: Decimal("8"),
    SafetyGrade.GRADE_3: Decimal("6"),
    SafetyGrade.GRADE_4: Decimal("4"),
    SafetyGrade.GRADE_5_OR_E: Decimal("2"),
}


@dataclass(slots=True)
class QualificationInput:
    estimated_price: int
    expected_price: int
    bid_price: int
    performance_base_amount: int
    equivalent_performance_amount: int = 0
    similar_performance_amount: int = 0
    credit_rating: CreditRating = CreditRating.A_MINUS_OR_BETTER
    safety_grade: SafetyGrade = SafetyGrade.GRADE_1
    reputation_score: Decimal = Decimal("0")
    disqualification_reason: bool = False


@dataclass(slots=True)
class QualificationResult:
    status: str
    passed: bool
    bid_rate_percent: float
    minimum_bid_rate_percent: float
    meets_minimum_bid_rate: bool
    performance_score: float
    equivalent_performance_ratio: float
    similar_performance_ratio: float
    business_score: float
    safety_score: float
    ability_score_before_reputation: float
    reputation_input: float
    reputation_applied: float
    ability_score_after_reputation: float
    price_score: float
    disqualification_penalty: float
    total_score: float
    pass_score: float = 88.0
    gap_to_pass: float = 0.0
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _round4(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _score_equivalent(ratio_percent: Decimal) -> Decimal:
    if ratio_percent >= 100:
        return Decimal("10")
    if ratio_percent >= 70:
        return Decimal("9")
    if ratio_percent >= 40:
        return Decimal("8")
    if ratio_percent >= 10:
        return Decimal("7")
    return Decimal("0")


def _score_similar(ratio_percent: Decimal) -> Decimal:
    if ratio_percent >= 100:
        return Decimal("3")
    if ratio_percent >= 70:
        return Decimal("2")
    if ratio_percent >= 40:
        return Decimal("1")
    if ratio_percent >= 10:
        return Decimal("0.5")
    return Decimal("0")


def calculate_performance_score(
    base_amount: int,
    equivalent_amount: int,
    similar_amount: int,
) -> tuple[Decimal, Decimal, Decimal]:
    if base_amount <= 0:
        raise ValueError("이행실적 평가 기준금액은 0원보다 커야 합니다.")
    if equivalent_amount < 0 or similar_amount < 0:
        raise ValueError("이행실적 금액은 음수일 수 없습니다.")

    base = Decimal(base_amount)
    equivalent_ratio = _round4(Decimal(equivalent_amount) / base * 100)
    similar_ratio = _round4(Decimal(similar_amount) / base * 100)

    score = _score_equivalent(equivalent_ratio) + _score_similar(similar_ratio)
    return min(PERFORMANCE_CAP, score), equivalent_ratio, similar_ratio


def calculate_price_score(expected_price: int, bid_price: int) -> tuple[Decimal, Decimal]:
    if expected_price <= 0:
        raise ValueError("예정가격은 0원보다 커야 합니다.")
    if bid_price <= 0:
        raise ValueError("투찰금액은 0원보다 커야 합니다.")

    raw_ratio = Decimal(bid_price) / Decimal(expected_price)
    rounded_ratio = _round4(raw_ratio)

    # 별표 5: 입찰가격/예정가격의 결과는 소수점 다섯째 자리에서 반올림.
    # 96% 이상은 96%일 때의 점수(58점)로 평가.
    formula_ratio = min(rounded_ratio, Decimal("0.9600"))
    score = PRICE_CAP - Decimal("4") * abs(
        Decimal("0.93") - formula_ratio
    ) * Decimal("100")
    return max(Decimal("0"), _round4(score)), raw_ratio


def calculate_transport_qualification(data: QualificationInput) -> QualificationResult:
    if data.estimated_price <= 0:
        raise ValueError("추정가격은 0원보다 커야 합니다.")
    if data.estimated_price >= MAX_ESTIMATED_PRICE:
        raise ValueError("현재 계산기는 추정가격 5억원 미만 구간만 지원합니다.")
    if data.expected_price <= 0 or data.bid_price <= 0:
        raise ValueError("예정가격과 투찰금액은 0원보다 커야 합니다.")
    if data.bid_price > data.expected_price:
        raise ValueError("투찰금액은 예정가격 이하이어야 합니다.")

    reputation = Decimal(str(data.reputation_score))
    if reputation < Decimal("-5") or reputation > Decimal("4.25"):
        raise ValueError("신인도 가감점은 -5.0점 이상 +4.25점 이하이어야 합니다.")

    performance_score, equivalent_ratio, similar_ratio = calculate_performance_score(
        data.performance_base_amount,
        data.equivalent_performance_amount,
        data.similar_performance_amount,
    )
    business_score = CREDIT_SCORES[data.credit_rating]
    safety_score = SAFETY_SCORES[data.safety_grade]

    ability_before = performance_score + business_score + safety_score

    # 신인도 가점은 수행능력 30점의 부족분 범위에서만 반영.
    if reputation > 0:
        reputation_applied = min(reputation, max(Decimal("0"), ABILITY_CAP - ability_before))
    else:
        reputation_applied = reputation

    ability_after = ability_before + reputation_applied

    price_score, raw_bid_ratio = calculate_price_score(
        data.expected_price,
        data.bid_price,
    )
    meets_floor = raw_bid_ratio >= MINIMUM_BID_RATE

    penalty = Decimal("-20") if data.disqualification_reason else Decimal("0")
    total = _round4(ability_after + price_score + penalty)
    passed = bool(meets_floor and total >= PASS_SCORE and not data.disqualification_reason)

    reasons = [
        f"이행실적 {float(performance_score):g}/10점",
        f"경영상태 {float(business_score):g}/10점",
        f"기술능력(안전성) {float(safety_score):g}/10점",
        f"입찰가격 {float(price_score):g}/70점",
    ]
    warnings: list[str] = []

    if not meets_floor:
        warnings.append("낙찰하한율 89.995% 미만으로 적격심사 대상가격에 미달합니다.")
    if data.disqualification_reason:
        warnings.append("결격사유가 있어 -20점이 적용됩니다.")
    if reputation > 0 and reputation_applied < reputation:
        warnings.append(
            "신인도 가점은 해당용역 수행능력 30점의 부족분까지만 반영되어 일부 가점이 적용되지 않았습니다."
        )
    if data.similar_performance_amount > 0:
        warnings.append(
            "유사용역 인정범위는 발주기관이 입찰공고에서 정한 범위와 일치하는지 반드시 확인하십시오."
        )

    gap = max(Decimal("0"), PASS_SCORE - total)

    return QualificationResult(
        status="적격통과 예상" if passed else "적격미달 예상",
        passed=passed,
        bid_rate_percent=float(_round4(raw_bid_ratio * 100)),
        minimum_bid_rate_percent=89.995,
        meets_minimum_bid_rate=meets_floor,
        performance_score=float(performance_score),
        equivalent_performance_ratio=float(equivalent_ratio),
        similar_performance_ratio=float(similar_ratio),
        business_score=float(business_score),
        safety_score=float(safety_score),
        ability_score_before_reputation=float(_round4(ability_before)),
        reputation_input=float(reputation),
        reputation_applied=float(reputation_applied),
        ability_score_after_reputation=float(_round4(ability_after)),
        price_score=float(price_score),
        disqualification_penalty=float(penalty),
        total_score=float(total),
        gap_to_pass=float(_round4(gap)),
        reasons=reasons,
        warnings=warnings,
    )
