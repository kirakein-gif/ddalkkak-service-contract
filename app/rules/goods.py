"""학교 물품 제조·구매 계약 기본 Rule Engine.

2026-07-01 행정안전부 예규 및 2026-06-03 지방계약법 시행령을 기준으로
학교에서 자주 쓰는 1인/2인 이상 견적 수의계약과 경쟁입찰 분기를 우선 구현한다.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

RULE_EFFECTIVE_FROM = date(2026, 7, 1)
ONE_PERSON_LIMIT = 20_000_000
SMALL_VALUE_GOODS_LIMIT = 100_000_000
DIRECT_PRODUCTION_THRESHOLD = 10_000_000


class GoodsRoute(StrEnum):
    ONE_PERSON = "GOODS_ONE_PERSON"
    TWO_PERSON = "GOODS_TWO_PERSON"
    COMPETITIVE = "GOODS_COMPETITIVE"
    HISTORICAL_REVIEW = "GOODS_HISTORICAL_REVIEW"


@dataclass(slots=True)
class GoodsInput:
    item_name: str
    estimated_price: int
    planned_date: date = RULE_EFFECTIVE_FROM
    is_sme_competition_product: bool = False
    direct_production_applicable: bool = False
    is_publication: bool = False
    unit_price_contract: bool = False


@dataclass(slots=True)
class GoodsResult:
    route_code: GoodsRoute
    contract_method: str
    status: str
    minimum_quote_rate: float | None = None
    quote_count_min: int | None = None
    designated_system_required: bool = False
    sme_competition_status: str = "해당 여부 확인"
    direct_production_status: str = "해당 여부 확인"
    reasons: list[str] = field(default_factory=list)
    legal_bases: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_goods(data: GoodsInput) -> GoodsResult:
    if data.estimated_price <= 0:
        raise ValueError("추정가격은 0원보다 커야 합니다.")

    if data.planned_date < RULE_EFFECTIVE_FROM:
        return GoodsResult(
            route_code=GoodsRoute.HISTORICAL_REVIEW,
            contract_method="과거 기준 별도 검토",
            status="검토필요",
            reasons=["현재 물품 Rule Engine은 2026-07-01 이후 예정 건을 기준으로 합니다."],
            warnings=["계약 예정일 당시 법령·예규를 확인하십시오."],
        )

    common_checks = [
        "추정가격은 부가가치세 제외 기준으로 산정되었는지 확인",
        "규격서·수량·납품장소·납품기한 확정",
        "특정 규격·상표 지정이 불필요한 경쟁제한이 되지 않는지 확인",
        "중소기업자간 경쟁제품·직접생산확인 대상 여부 확인",
        "수의계약 배제사유 및 이해충돌방지법상 제한 확인",
    ]
    if data.unit_price_contract:
        common_checks.append("단가계약 추정가격은 추정단가 × 예정물량으로 산정되었는지 확인")

    sme_status = (
        "중소기업자간 경쟁제품 — SMPP 최신 지정목록 확인"
        if data.is_sme_competition_product
        else "일반 물품 또는 지정 여부 미확인"
    )
    direct_status = "해당 없음/별도 확인"
    if data.is_sme_competition_product and data.direct_production_applicable:
        if data.estimated_price >= DIRECT_PRODUCTION_THRESHOLD:
            direct_status = "직접생산확인증명서 확인 필요"
        else:
            direct_status = "1천만원 미만 — 수의계약 직접생산 확인 금액기준 미만"

    if data.estimated_price <= ONE_PERSON_LIMIT:
        return GoodsResult(
            route_code=GoodsRoute.ONE_PERSON,
            contract_method="1인 견적 수의계약 가능",
            status="확정",
            minimum_quote_rate=None,
            quote_count_min=1,
            designated_system_required=False,
            sme_competition_status=sme_status,
            direct_production_status=direct_status,
            reasons=["추정가격이 2천만원 이하인 물품 제조·구매 계약입니다."],
            legal_bases=[
                "지방계약법 시행령 제25조제1항제5호나목",
                "지방계약법 시행령 제30조제1항제2호",
                "지방자치단체 입찰 및 계약 집행기준 제5장",
            ],
            checks=common_checks,
            warnings=["1인 견적은 가능 규정이며 경쟁견적을 금지하는 의미가 아닙니다."],
        )

    if data.estimated_price <= SMALL_VALUE_GOODS_LIMIT:
        rate = 0.90 if data.is_publication else 0.88
        return GoodsResult(
            route_code=GoodsRoute.TWO_PERSON,
            contract_method="2인 이상 견적 수의계약 검토",
            status="조건부",
            minimum_quote_rate=rate,
            quote_count_min=2,
            designated_system_required=True,
            sme_competition_status=sme_status,
            direct_production_status=direct_status,
            reasons=[
                "추정가격이 2천만원 초과 1억원 이하인 물품 제조·구매 구간입니다.",
                "소기업·소상공인 등 지방계약법 시행령 제25조의 요건 충족 여부를 확인해야 합니다.",
            ],
            legal_bases=[
                "지방계약법 시행령 제25조제1항제5호라목",
                "지방계약법 시행령 제30조",
                "지방자치단체 입찰 및 계약 집행기준 제5장",
            ],
            checks=["소기업·소상공인 확인 또는 법령상 예외 적용 여부 확인"] + common_checks,
            warnings=[
                "중소기업자간 경쟁제품은 별도의 중소기업제품 구매제도를 함께 확인하십시오.",
                "간행물은 출판문화산업 진흥법상 가격할인 제한을 별도로 확인하십시오.",
            ],
        )

    return GoodsResult(
        route_code=GoodsRoute.COMPETITIVE,
        contract_method="경쟁입찰 또는 조달제도 활용 검토",
        status="검토필요",
        designated_system_required=True,
        sme_competition_status=sme_status,
        direct_production_status=direct_status,
        reasons=["추정가격이 일반적인 물품 2인 이상 견적 수의계약 금액구간을 초과합니다."],
        legal_bases=[
            "지방계약법 시행령 제25조",
            "지방자치단체 입찰시 낙찰자 결정기준",
        ],
        checks=[
            "일반/제한경쟁 여부",
            "중소기업자간 경쟁제품 여부",
            "조달청 MAS·제3자단가계약 등 조달제도 활용 가능 여부",
            "물품 적격심사 적용 여부",
        ] + common_checks,
    )
