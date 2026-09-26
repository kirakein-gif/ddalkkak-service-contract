"""학교 공사계약 기본 Rule Engine."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

RULE_EFFECTIVE_FROM = date(2026, 7, 1)
ONE_PERSON_LIMIT = 20_000_000


class WorksType(StrEnum):
    GENERAL = "GENERAL"          # 건설산업기본법상 종합공사
    SPECIALIZED = "SPECIALIZED"  # 건설산업기본법상 전문공사
    OTHER = "OTHER"              # 전기·정보통신·소방 등 기타 공사 관련 법령


WORKS_SMALL_VALUE_LIMIT = {
    WorksType.GENERAL: 400_000_000,
    WorksType.SPECIALIZED: 200_000_000,
    WorksType.OTHER: 160_000_000,
}


class WorksRoute(StrEnum):
    ONE_PERSON = "WORKS_ONE_PERSON"
    TWO_PERSON = "WORKS_TWO_PERSON"
    COMPETITIVE = "WORKS_COMPETITIVE"
    HISTORICAL_REVIEW = "WORKS_HISTORICAL_REVIEW"


@dataclass(slots=True)
class WorksInput:
    work_name: str
    estimated_price: int
    works_type: WorksType
    planned_date: date = RULE_EFFECTIVE_FROM
    required_industry: str = ""
    region_restriction_requested: bool = True


@dataclass(slots=True)
class WorksResult:
    route_code: WorksRoute
    contract_method: str
    status: str
    small_value_limit: int | None = None
    minimum_quote_rate: float | None = None
    quote_count_min: int | None = None
    designated_system_required: bool = False
    reasons: list[str] = field(default_factory=list)
    legal_bases: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_works(data: WorksInput) -> WorksResult:
    if data.estimated_price <= 0:
        raise ValueError("추정가격은 0원보다 커야 합니다.")

    if data.planned_date < RULE_EFFECTIVE_FROM:
        return WorksResult(
            route_code=WorksRoute.HISTORICAL_REVIEW,
            contract_method="과거 공사계약 기준 별도 검토",
            status="검토필요",
            reasons=["현재 공사 Rule Engine은 2026-07-01 이후 예정 건을 기준으로 합니다."],
        )

    limit = WORKS_SMALL_VALUE_LIMIT[data.works_type]
    common_checks = [
        "추정가격 산정 시 관급자재로 공급될 부분의 가격 제외 여부 확인",
        "설계서·내역서·시방서 확정",
        "공사종류와 요구 업종·주력분야의 적정성 확인",
        "건설업 등록기준·기술인력 보유 여부 확인",
        "국민연금·건강보험·퇴직공제·산업안전보건관리비·안전관리비·품질관리비 등 법정경비 반영",
        "건설근로자 임금·하도급·산업안전 관련 의무 확인",
        "수의계약 배제사유 및 이해충돌방지법상 제한 확인",
    ]
    if data.required_industry:
        common_checks.insert(2, f"요구 업종: {data.required_industry}")
    if data.region_restriction_requested:
        common_checks.append("지역제한 적용 가능 범위와 소재지 기준 확인")

    if data.estimated_price <= ONE_PERSON_LIMIT:
        return WorksResult(
            route_code=WorksRoute.ONE_PERSON,
            contract_method="1인 견적 수의계약 가능",
            status="확정",
            small_value_limit=limit,
            quote_count_min=1,
            designated_system_required=False,
            reasons=["추정가격이 2천만원 이하인 공사입니다."],
            legal_bases=[
                "지방계약법 시행령 제30조제1항제2호",
                "지방자치단체 입찰 및 계약 집행기준 제5장",
            ],
            checks=common_checks,
            warnings=["공사는 설계·내역·법정경비 검토를 금액판정보다 먼저 완료해야 합니다."],
        )

    if data.estimated_price <= limit:
        return WorksResult(
            route_code=WorksRoute.TWO_PERSON,
            contract_method="2인 이상 견적 수의계약 검토",
            status="조건부",
            small_value_limit=limit,
            minimum_quote_rate=0.89745,
            quote_count_min=2,
            designated_system_required=True,
            reasons=[
                f"{data.works_type.value} 공사의 현행 금액기준 수의계약 상한 {limit:,}원 이하입니다.",
                "2인 이상 견적제출 및 배제사유 확인이 필요한 구간입니다.",
            ],
            legal_bases=[
                "지방계약법 시행령 제25조제1항제5호가목",
                "지방계약법 시행령 제30조",
                "지방자치단체 입찰 및 계약 집행기준 제5장",
            ],
            checks=[
                "공사 수의계약 견적률 산정 시 예정가격과 견적가격에서 법정 보험료·안전관리비 등 정해진 금액을 각각 제외해 비교",
            ] + common_checks,
            warnings=[
                "89.745%는 공사 소액수의 현행 집행기준의 기본 견적률이며, 공고일 기준 최신 예규를 재확인하십시오.",
            ],
        )

    return WorksResult(
        route_code=WorksRoute.COMPETITIVE,
        contract_method="경쟁입찰 + 공사 적격심사 검토",
        status="검토필요",
        small_value_limit=limit,
        designated_system_required=True,
        reasons=[f"해당 공사유형의 금액기준 수의계약 상한 {limit:,}원을 초과합니다."],
        legal_bases=[
            "지방계약법 시행령 제25조",
            "지방자치단체 입찰시 낙찰자 결정기준",
        ],
        checks=[
            "공사규모별 적격심사 평가기준과 낙찰하한율 확인",
            "종합·전문 상호시장 진출 및 업종·주력분야 적용 여부 확인",
            "지역제한 가능 여부 확인",
        ] + common_checks,
    )
