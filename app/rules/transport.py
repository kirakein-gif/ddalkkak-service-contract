"""학교 통학차량·통학버스 용역 전용 규칙엔진.

현재 버전은 2026-07-27 이후 공고 예정 건을 기준으로 다음을 지원합니다.

- 1억원 이하: 지방계약 수의계약 기본 엔진과 결합
- 1억원 초과 5억원 미만: 여객 육상운송용역 적격심사 검토
- 통학대상에 따른 어린이통학버스 신고·안전요건 확인
- 전세버스운송사업 등록, 차량·보험·운전자·동승보호자 관련 체크리스트

학교별 과업지시서·특수조건에서 더 엄격한 차량연식/직영차량 등의 조건을
정할 수 있으므로 법정요건과 학교 선택조건을 구분하여 반환합니다.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.rules.engine import (
    ContractInput,
    DecisionStatus,
    RouteCode,
    evaluate_contract,
)


TRANSPORT_RULE_EFFECTIVE_FROM = date(2026, 7, 27)
PASSENGER_TRANSPORT_QUALIFICATION_CUTOFF = 500_000_000
PASSENGER_TRANSPORT_UNDER_500M_RATE = 0.87995
PASSENGER_TRANSPORT_PASS_SCORE = 88


class PassengerGroup(StrEnum):
    KINDERGARTEN = "KINDERGARTEN"
    ELEMENTARY = "ELEMENTARY"
    MIDDLE = "MIDDLE"
    HIGH = "HIGH"
    SPECIAL_MIXED = "SPECIAL_MIXED"
    MIXED = "MIXED"


class PricingMethod(StrEnum):
    TOTAL = "TOTAL"
    UNIT = "UNIT"


class TransportRouteCode(StrEnum):
    SMALL_VALUE = "TRANSPORT_SMALL_VALUE"
    COMPETITIVE_UNDER_500M = "TRANSPORT_COMPETITIVE_UNDER_500M"
    COMPETITIVE_500M_OR_MORE = "TRANSPORT_COMPETITIVE_500M_OR_MORE"
    HISTORICAL_REVIEW = "TRANSPORT_HISTORICAL_REVIEW"


@dataclass(slots=True)
class TransportInput:
    service_name: str
    estimated_price: int
    planned_date: date
    passenger_group: PassengerGroup
    vehicle_count: int
    seat_capacity_min: int
    pricing_method: PricingMethod = PricingMethod.TOTAL
    operation_days: int | None = None
    driver_included: bool = True
    attendant_included: bool = False
    regional_restriction_requested: bool = True


@dataclass(slots=True)
class TransportRuleResult:
    route_code: str
    contract_method: str
    status: DecisionStatus
    minimum_quote_rate: float | None = None
    qualification_score: int | None = None
    designated_system_required: bool = True
    child_school_bus_status: str = "검토 필요"
    required_industry_registration: str = "전세버스운송사업 등록"
    regional_restriction_status: str = "가능 여부 검토"
    pricing_method: str = "총액"
    reasons: list[str] = field(default_factory=list)
    legal_bases: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    required_documents: list[str] = field(default_factory=list)
    common_school_conditions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _child_bus_status(group: PassengerGroup) -> tuple[str, bool | None]:
    if group in {PassengerGroup.KINDERGARTEN, PassengerGroup.ELEMENTARY}:
        return "어린이통학버스 신고·요건 적용 확인 필요", True
    if group in {PassengerGroup.MIDDLE, PassengerGroup.HIGH}:
        return "통상 어린이통학버스 정의 비대상 — 실제 운송대상 연령 확인", False
    return "연령·학교급 혼합 — 13세 미만 운송 여부별 검토 필요", None


def _base_transport_checks(data: TransportInput, child_bus_required: bool | None) -> tuple[list[str], list[str], list[str]]:
    checks = [
        "나라장터 업종자격: 여객자동차운송사업(전세버스) 등록 여부 확인",
        "차량별 자동차등록증과 계약상대자의 차량 소유·사용관계 확인",
        "여객자동차 운수사업법령상 차령 및 차량충당연한 충족 여부 확인",
        "책임보험 및 종합보험(대인 무한배상 등 학교 특수조건) 가입 여부 확인",
        "운행노선·운행시간·운행일수·탑승예정인원과 차량 정원 적정성 확인",
        "학교가 별도로 요구하는 차량연식·주행거리·직영차량 조건의 필요성과 경쟁제한 적정성 확인",
    ]
    docs = [
        "전세버스운송사업 등록 관련 증빙",
        "차량별 자동차등록증",
        "차량별 보험가입증명서",
        "차량 정기검사·임시검사 등 관계 증빙",
        "운전자 운전면허 및 업체 재직관계 증빙",
        "운행노선표·운행시간표",
    ]
    common = [
        "지입차량 금지 또는 회사 직영차량 요구 여부",
        "고정 배차 및 대체차량 사전승인",
        "냉·난방, 좌석안전띠, 후방카메라 등 안전설비",
        "고장·사고 시 즉시 대체차량 투입",
        "유류비·정비비·보험료 등 운행 제경비의 계약금액 포함 여부",
        "운행개시 전 시험운행 또는 노선확인",
    ]

    if child_bus_required is True:
        checks.extend([
            "관할 경찰서 어린이통학버스 신고 및 신고증명서 비치 여부 확인",
            "도로교통법령상 어린이통학버스 구조·도색·표지·안전장치 요건 확인",
            "운전자·운영자·동승보호자의 어린이통학버스 안전교육 이수 여부 확인",
            "어린이 하차확인장치 설치·작동 요건 확인",
        ])
        docs.extend([
            "어린이통학버스 신고증명서",
            "어린이통학버스 안전교육 이수 관련 증빙",
            "어린이 하차확인장치 등 안전장치 관련 증빙",
        ])
    elif child_bus_required is None:
        checks.append("13세 미만 학생을 운송하는 차량이 있는지 확인하여 어린이통학버스 적용 차량을 분리")

    return checks, docs, common


def evaluate_transport(data: TransportInput) -> TransportRuleResult:
    if data.estimated_price <= 0:
        raise ValueError("추정가격은 0원보다 커야 합니다.")
    if data.vehicle_count <= 0:
        raise ValueError("차량 대수는 1대 이상이어야 합니다.")
    if data.seat_capacity_min <= 0:
        raise ValueError("최소 승차정원은 1명 이상이어야 합니다.")
    if data.operation_days is not None and data.operation_days <= 0:
        raise ValueError("운행일수는 1일 이상이어야 합니다.")

    child_status, child_required = _child_bus_status(data.passenger_group)
    checks, docs, common = _base_transport_checks(data, child_required)
    warnings: list[str] = []

    if data.planned_date < TRANSPORT_RULE_EFFECTIVE_FROM:
        return TransportRuleResult(
            route_code=TransportRouteCode.HISTORICAL_REVIEW,
            contract_method="과거 통학차량 기준 별도 확인",
            status=DecisionStatus.REVIEW,
            child_school_bus_status=child_status,
            pricing_method="단가" if data.pricing_method == PricingMethod.UNIT else "총액",
            reasons=["현재 통학차량 전용 규칙은 2026-07-27 이후 공고 예정 건을 기준으로 작성되었습니다."],
            required_checks=["공고 예정일 당시 지방계약·조달청 적격심사·교통안전 규정 확인"] + checks,
            required_documents=docs,
            common_school_conditions=common,
            warnings=["과거 공고를 현재 기준으로 재판정하지 마십시오."],
        )

    if not data.driver_included:
        warnings.append(
            "운전원이 포함되지 않으면 일반적인 '전세버스 운송용역'과 계약구조가 달라질 수 있으므로 차량임차/운송용역 구분을 다시 검토하십시오."
        )

    if child_required is True and not data.attendant_included:
        warnings.append(
            "유치원·초등학교 어린이통학버스는 도로교통법 제53조제3항의 성년 보호자 동승의무를 확인해야 합니다. 계약범위에 동승보호자를 포함하지 않는 경우 학교가 별도 배치하는지 확인하십시오."
        )

    if data.pricing_method == PricingMethod.UNIT:
        checks.append(
            "단가계약 추정가격은 추정단가 × 예정물량으로 산정되었는지 확인"
        )

    if data.regional_restriction_requested:
        checks.append(
            "지역제한을 둘 경우 지방계약법 시행령 제20조 및 시행규칙 제24조의 대상금액·지역범위 충족 여부 확인"
        )

    # 1억원 이하: 기존 수의계약 엔진을 그대로 사용하되 통학차량 요건을 추가한다.
    if data.estimated_price <= 100_000_000:
        base = evaluate_contract(
            ContractInput(
                service_name=data.service_name,
                estimated_price=data.estimated_price,
                planned_date=data.planned_date,
            )
        )
        return TransportRuleResult(
            route_code=TransportRouteCode.SMALL_VALUE,
            contract_method=f"통학차량 · {base.contract_method}",
            status=base.status,
            minimum_quote_rate=base.minimum_quote_rate,
            designated_system_required=base.designated_system_required,
            child_school_bus_status=child_status,
            regional_restriction_status="소액수의 지역제한·업종제한 조건 확인",
            pricing_method="단가" if data.pricing_method == PricingMethod.UNIT else "총액",
            reasons=base.reasons + [
                f"차량 {data.vehicle_count}대, 최소 {data.seat_capacity_min}인승 조건으로 입력되었습니다.",
            ],
            legal_bases=base.legal_bases + [
                "여객자동차 운수사업법 시행령 제3조·제4조(전세버스운송사업)",
                "여객자동차 운수사업법 시행령 제40조(자동차의 차령 등)",
                "도로교통법 제2조제23호·제52조·제53조(어린이통학버스 해당 시)",
            ],
            required_checks=base.required_checks + checks,
            required_documents=docs,
            common_school_conditions=common,
            warnings=base.warnings + warnings,
        )

    # 1억원 초과 5억원 미만: 학교 통학차량에서 빈번한 여객 육상운송 적격심사 구간.
    if data.estimated_price < PASSENGER_TRANSPORT_QUALIFICATION_CUTOFF:
        return TransportRuleResult(
            route_code=TransportRouteCode.COMPETITIVE_UNDER_500M,
            contract_method="경쟁입찰 + 여객 육상운송용역 적격심사 검토",
            status=DecisionStatus.CONDITIONAL,
            minimum_quote_rate=PASSENGER_TRANSPORT_UNDER_500M_RATE,
            qualification_score=PASSENGER_TRANSPORT_PASS_SCORE,
            designated_system_required=True,
            child_school_bus_status=child_status,
            regional_restriction_status="지역제한 가능 여부 확인 후 일반/제한경쟁 결정",
            pricing_method="단가" if data.pricing_method == PricingMethod.UNIT else "총액",
            reasons=[
                f"추정가격 {data.estimated_price:,}원은 일반적인 용역 수의계약 금액기준 1억원을 초과합니다.",
                "학교 통학차량 경쟁입찰 사례에서는 조달청 일반용역 적격심사 세부기준의 여객 육상운송용역 기준을 적용합니다.",
                "추정가격 5억원 미만 구간의 현행 사례에서 낙찰하한율 87.995%, 적격심사 통과점수 88점이 적용됩니다.",
            ],
            legal_bases=[
                "지방계약법 시행령 제42조(재정지출의 부담이 되는 입찰에서의 낙찰자 결정)",
                "조달청 일반용역 적격심사 세부기준 [별표 5] 여객 육상운송용역 적격심사",
                "지방계약법 시행규칙 제24조(지역제한입찰의 대상)",
                "여객자동차 운수사업법 시행령 제3조·제4조(전세버스운송사업)",
                "여객자동차 운수사업법 시행령 제40조(자동차의 차령 등)",
                "도로교통법 제2조제23호·제52조·제53조(어린이통학버스 해당 시)",
            ],
            required_checks=[
                "조달청 일반용역 적격심사 세부기준 [별표 5]의 최신 시행본 적용 여부 확인",
                "이행실적 평가 기준금액과 인정범위를 공고문에 명확히 기재",
                "경영상태·신인도·결격사유 등 적격심사 항목 확인",
                "지역제한입찰 적용 시 시행규칙 제24조의 금액 및 지역범위 확인",
            ] + checks,
            required_documents=docs + [
                "적격심사신청서",
                "적격심사 자기평가 및 심사표",
                "이행실적 증빙서류",
                "신용평가등급 확인서 등 경영상태 증빙",
                "신인도 관련 증빙(해당 시)",
            ],
            common_school_conditions=common,
            warnings=warnings,
        )

    return TransportRuleResult(
        route_code=TransportRouteCode.COMPETITIVE_500M_OR_MORE,
        contract_method="경쟁입찰 + 여객 육상운송용역 적격심사(5억원 이상 구간) 별도 검토",
        status=DecisionStatus.REVIEW,
        child_school_bus_status=child_status,
        regional_restriction_status="지역제한 가능 금액·국제입찰 적용 여부 별도 확인",
        pricing_method="단가" if data.pricing_method == PricingMethod.UNIT else "총액",
        reasons=[
            f"추정가격 {data.estimated_price:,}원은 여객 육상운송용역 적격심사 5억원 미만 구간을 벗어납니다.",
        ],
        legal_bases=[
            "조달청 일반용역 적격심사 세부기준 [별표 5] 여객 육상운송용역 적격심사",
            "지방계약법 시행규칙 제24조(지역제한입찰의 대상)",
        ],
        required_checks=[
            "5억원 이상 여객 육상운송용역 적격심사 배점·가격산식 확인",
            "지역제한 가능 여부 및 국제입찰 적용 여부 확인",
        ] + checks,
        required_documents=docs,
        common_school_conditions=common,
        warnings=warnings,
    )
