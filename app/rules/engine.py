"""학교 용역계약 규칙엔진.

현재 버전은 2026-07-01 시행 기준으로 학교에서 자주 발생하는
1인 견적 및 2인 이상 견적 수의계약의 1차 판정을 지원합니다.

중요:
- 결과는 '가능/조건부/검토필요'를 구분합니다.
- 금액 기준은 추정가격(부가가치세 제외)을 사용합니다.
- 수학여행·방과후 등 제안서 평가형 용역과 기술용역/PQ는 별도 검토 대상으로 돌립니다.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


RULE_EFFECTIVE_FROM = date(2026, 7, 1)
STANDARD_ONE_PERSON_LIMIT = 20_000_000
SPECIAL_ONE_PERSON_LIMIT = 50_000_000
SMALL_VALUE_SERVICE_LIMIT = 100_000_000


class DecisionStatus(StrEnum):
    CONFIRMED = "확정"
    CONDITIONAL = "조건부"
    REVIEW = "검토필요"


class RouteCode(StrEnum):
    ONE_PERSON_QUOTE = "ONE_PERSON_QUOTE"
    TWO_PERSON_E_QUOTE = "TWO_PERSON_E_QUOTE"
    TWO_STAGE_REVIEW = "TWO_STAGE_REVIEW"
    TECHNICAL_SERVICE_REVIEW = "TECHNICAL_SERVICE_REVIEW"
    COMPETITIVE_REVIEW = "COMPETITIVE_REVIEW"
    HISTORICAL_RULE_REVIEW = "HISTORICAL_RULE_REVIEW"


class VendorCategory(StrEnum):
    NONE = "NONE"
    YOUTH_STARTUP = "YOUTH_STARTUP"
    WOMEN = "WOMEN"
    DISABLED = "DISABLED"
    SOCIAL_ENTERPRISE = "SOCIAL_ENTERPRISE"
    SOCIAL_COOP = "SOCIAL_COOP"
    SELF_SUPPORT = "SELF_SUPPORT"
    VILLAGE_ENTERPRISE = "VILLAGE_ENTERPRISE"


SPECIAL_ONE_PERSON_CATEGORIES = {
    VendorCategory.YOUTH_STARTUP,
    VendorCategory.WOMEN,
    VendorCategory.DISABLED,
    VendorCategory.SOCIAL_ENTERPRISE,
    VendorCategory.SOCIAL_COOP,
    VendorCategory.SELF_SUPPORT,
    VendorCategory.VILLAGE_ENTERPRISE,
}

CATEGORIES_REQUIRING_EXTRA_CONFIRMATION = {
    VendorCategory.SOCIAL_ENTERPRISE,
    VendorCategory.SOCIAL_COOP,
    VendorCategory.SELF_SUPPORT,
    VendorCategory.VILLAGE_ENTERPRISE,
}


@dataclass(slots=True)
class ContractInput:
    service_name: str
    estimated_price: int
    planned_date: date = RULE_EFFECTIVE_FROM
    service_type: str = "일반용역"
    region: str | None = None
    vendor_category: VendorCategory = VendorCategory.NONE
    special_entity_requirements_confirmed: bool = False
    special_knowledge_or_qualification: bool = False
    technical_service: bool = False
    requires_proposal_evaluation: bool = False


@dataclass(slots=True)
class RuleResult:
    route_code: RouteCode
    contract_method: str
    status: DecisionStatus
    quote_count_min: int | None = None
    designated_system_required: bool = False
    minimum_quote_rate: float | None = None
    announcement_days: int | None = None
    small_business_restriction: str = "해당없음"
    reasons: list[str] = field(default_factory=list)
    legal_bases: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _common_checks() -> list[str]:
    return [
        "추정가격 산정이 적정한지 확인",
        "계약 분할로 수의계약 기준을 회피하는 경우가 아닌지 확인",
        "해당 용역 수행에 필요한 면허·등록·자격요건 확인",
        "공직자의 이해충돌 방지법상 수의계약 체결 제한 대상 여부 확인",
    ]


def evaluate_contract(data: ContractInput) -> RuleResult:
    if data.estimated_price <= 0:
        raise ValueError("추정가격은 0원보다 커야 합니다.")

    if data.planned_date < RULE_EFFECTIVE_FROM:
        return RuleResult(
            route_code=RouteCode.HISTORICAL_RULE_REVIEW,
            contract_method="과거 기준 별도 확인",
            status=DecisionStatus.REVIEW,
            reasons=[
                "현재 규칙 데이터는 2026-07-01 시행 기준부터 지원합니다.",
            ],
            required_checks=["계약/공고 예정일에 적용되던 법령·예규 버전 확인"],
            warnings=["현재 규칙으로 과거 계약을 판정하지 마십시오."],
        )

    if data.technical_service:
        return RuleResult(
            route_code=RouteCode.TECHNICAL_SERVICE_REVIEW,
            contract_method="기술용역 별도 검토",
            status=DecisionStatus.REVIEW,
            reasons=[
                "기술용역·설계·감리·PQ 대상은 일반 학교용역과 낙찰기준이 달라 별도 엔진으로 분리합니다.",
            ],
            required_checks=_common_checks()
            + ["PQ·사업수행능력평가·기술용역 적격심사 적용 여부 확인"],
        )

    if data.requires_proposal_evaluation:
        return RuleResult(
            route_code=RouteCode.TWO_STAGE_REVIEW,
            contract_method="2단계 입찰 등 제안서 평가 방식 검토",
            status=DecisionStatus.REVIEW,
            reasons=[
                "가격 외에 규격·기술·제안서 평가가 필요한 용역으로 표시되었습니다.",
                "수학여행·방과후·늘봄 등은 금액만으로 소액수의 여부를 자동 확정하지 않습니다.",
            ],
            legal_bases=[
                "지방계약법 시행령 제18조(2단계 입찰)",
            ],
            required_checks=_common_checks()
            + ["제안서 평가 필요성 및 평가기준 확인", "학교 내부 심의·운영계획 절차 확인"],
        )

    price = data.estimated_price

    # 1. 일반적인 2천만원 이하 1인 견적 가능
    if price <= STANDARD_ONE_PERSON_LIMIT:
        return RuleResult(
            route_code=RouteCode.ONE_PERSON_QUOTE,
            contract_method="1인 견적 수의계약 가능",
            status=DecisionStatus.CONFIRMED,
            quote_count_min=1,
            designated_system_required=False,
            minimum_quote_rate=None,
            small_business_restriction="원칙적 소기업·소상공인 제한 없음",
            reasons=[
                f"추정가격 {price:,}원은 2천만원 이하입니다.",
                "법령상 1인으로부터 받은 견적서에 의할 수 있습니다.",
                "다만 필요하면 2인 이상 전자견적 방식으로 집행할 수 있습니다.",
            ],
            legal_bases=[
                "지방계약법 시행령 제25조제1항제5호나목",
                "지방계약법 시행령 제30조제1항제2호",
            ],
            required_checks=_common_checks()
            + ["1인 견적을 선택하는 경우 가격 적정성 검토 근거 확보"],
            warnings=[
                "2인 이상 견적으로 집행하는 경우 예정가격 대비 90% 이상 최저가격 기준을 적용하는 현행 수의계약 운영요령을 확인하십시오.",
            ],
        )

    # 2. 특정기업과의 계약은 5천만원 이하까지 1인 견적 가능
    if (
        price <= SPECIAL_ONE_PERSON_LIMIT
        and data.vendor_category in SPECIAL_ONE_PERSON_CATEGORIES
    ):
        extra_required = data.vendor_category in CATEGORIES_REQUIRING_EXTRA_CONFIRMATION
        confirmed = (not extra_required) or data.special_entity_requirements_confirmed

        checks = _common_checks() + [
            "계약상대자가 입력한 특별기업 유형에 실제 해당하는지 유효한 확인서로 검증",
        ]
        warnings: list[str] = []
        if extra_required and not confirmed:
            checks.append(
                "사회적기업·사회적협동조합·자활기업·마을기업에 필요한 취약계층 고용비율 등 추가 요건 확인"
            )
            warnings.append("추가 법정요건 확인 전에는 1인 견적 가능 여부를 확정할 수 없습니다.")

        return RuleResult(
            route_code=RouteCode.ONE_PERSON_QUOTE,
            contract_method="특정기업 1인 견적 수의계약 가능",
            status=DecisionStatus.CONFIRMED if confirmed else DecisionStatus.CONDITIONAL,
            quote_count_min=1,
            designated_system_required=False,
            minimum_quote_rate=None,
            small_business_restriction="특정기업 자격 확인 필요",
            reasons=[
                f"추정가격 {price:,}원은 5천만원 이하입니다.",
                f"계약상대자 유형이 {data.vendor_category.value}로 입력되었습니다.",
                "법령이 정한 특정기업과의 계약은 5천만원 이하에서 1인 견적이 가능할 수 있습니다.",
            ],
            legal_bases=[
                "지방계약법 시행령 제25조제1항제5호다목·바목",
                "지방계약법 시행령 제30조제1항제2호 각 목",
            ],
            required_checks=checks,
            warnings=warnings,
        )

    # 3. 2천만원 초과 1억원 이하 2인 이상 전자견적 수의계약
    if price <= SMALL_VALUE_SERVICE_LIMIT:
        if data.special_knowledge_or_qualification:
            small_business = "예외 검토"
            basis = "지방계약법 시행령 제25조제1항제5호마목"
            extra_reason = (
                "특수한 지식·기술 또는 자격을 요구하는 용역으로 입력되어 "
                "소기업·소상공인 제한 예외 적용 가능성을 별도 확인해야 합니다."
            )
        elif data.vendor_category in SPECIAL_ONE_PERSON_CATEGORIES:
            small_business = "특정기업 자격 기준 검토"
            basis = "지방계약법 시행령 제25조제1항제5호바목"
            extra_reason = "특정기업과 체결하는 수의계약 사유 적용 여부를 확인해야 합니다."
        else:
            small_business = "원칙적으로 소기업·소상공인 확인 필요"
            basis = "지방계약법 시행령 제25조제1항제5호라목"
            extra_reason = (
                "일반적인 2천만원 초과 1억원 이하 물품·용역 수의계약은 "
                "소기업 또는 소상공인 여부 확인이 기본 분기입니다."
            )

        return RuleResult(
            route_code=RouteCode.TWO_PERSON_E_QUOTE,
            contract_method="2인 이상 견적제출 수의계약 검토",
            status=DecisionStatus.CONDITIONAL,
            quote_count_min=2,
            designated_system_required=True,
            minimum_quote_rate=0.88,
            announcement_days=3,
            small_business_restriction=small_business,
            reasons=[
                f"추정가격 {price:,}원은 2천만원 초과 1억원 이하입니다.",
                "금액기준 소액수의 대상 범위에 해당할 수 있으며 2인 이상 견적 절차를 적용합니다.",
                extra_reason,
            ],
            legal_bases=[
                basis,
                "지방계약법 시행령 제30조제1항·제2항",
                "지방자치단체 입찰 및 계약 집행기준 제5장 수의계약 운영요령",
            ],
            required_checks=_common_checks()
            + [
                "소기업·소상공인 제한 또는 예외사유 적용 여부 확인",
                "지역제한·업종·면허 등 참가자격 확인",
                "나라장터 등 지정정보처리장치에 수의계약 안내공고",
                "수의계약 배제사유 확인",
                "동일가격 견적자 발생 시 전자추첨 절차 확인",
            ],
            warnings=[
                "수의계약 안내공고는 원칙적으로 일정기간 게시해야 하며 현재 엔진은 최소 3일을 기본값으로 둡니다.",
                "특별법·교육청 지침·학교업무 유형별 조건이 있으면 해당 기준을 추가 적용해야 합니다.",
            ],
        )

    return RuleResult(
        route_code=RouteCode.COMPETITIVE_REVIEW,
        contract_method="경쟁입찰 등 별도 계약방법 검토",
        status=DecisionStatus.REVIEW,
        reasons=[
            f"추정가격 {price:,}원은 일반적인 물품·용역 금액기준 수의계약 상한 1억원을 초과합니다.",
        ],
        legal_bases=[
            "지방계약법 시행령 제25조제1항제5호",
        ],
        required_checks=_common_checks()
        + [
            "일반경쟁·제한경쟁 여부 확인",
            "적격심사·2단계 입찰·협상에 의한 계약 등 낙찰방법 확인",
        ],
        warnings=[
            "다른 법정 수의계약 사유가 존재하는 경우 별도 검토가 필요합니다.",
        ],
    )
