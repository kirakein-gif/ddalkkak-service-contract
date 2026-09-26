"""학교 실무 중심 물품유형 카탈로그."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class GoodsCategory(StrEnum):
    GENERAL_OFFICE = "GENERAL_OFFICE"
    FURNITURE = "FURNITURE"
    IT_EQUIPMENT = "IT_EQUIPMENT"
    EDUCATIONAL_EQUIPMENT = "EDUCATIONAL_EQUIPMENT"
    KITCHEN_EQUIPMENT = "KITCHEN_EQUIPMENT"
    FOOD_INGREDIENTS = "FOOD_INGREDIENTS"
    MILK = "MILK"
    BOOKS = "BOOKS"
    UNIFORM = "UNIFORM"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class GoodsCategoryProfile:
    code: GoodsCategory
    label: str
    purchase_method_hint: str
    legal_bases: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    default_unit_price_contract: bool = False
    default_publication: bool = False
    requires_two_stage: bool = False
    recommend_mas_check: bool = False
    recommend_sme_check: bool = True
    quantity_variable: bool = False


_BASE: dict[GoodsCategory, GoodsCategoryProfile] = {
    GoodsCategory.GENERAL_OFFICE: GoodsCategoryProfile(
        GoodsCategory.GENERAL_OFFICE,
        "일반 사무용품",
        "금액기준에 따른 수의계약·경쟁입찰",
        checks=("나라장터 종합쇼핑몰·단가계약 제품 여부 확인",),
        recommend_mas_check=True,
    ),
    GoodsCategory.FURNITURE: GoodsCategoryProfile(
        GoodsCategory.FURNITURE,
        "가구·집기",
        "종합쇼핑몰/MAS 또는 일반 구매 비교",
        checks=(
            "세부품명 기준 중소기업자간 경쟁제품 지정 여부 확인",
            "직접생산확인 대상 여부 확인",
            "나라장터 종합쇼핑몰·제3자단가계약 제품 여부 확인",
        ),
        recommend_mas_check=True,
    ),
    GoodsCategory.IT_EQUIPMENT: GoodsCategoryProfile(
        GoodsCategory.IT_EQUIPMENT,
        "컴퓨터·정보화기기",
        "종합쇼핑몰/MAS 우선 검토 후 일반 구매 비교",
        checks=(
            "조달청 종합쇼핑몰·다수공급자계약 여부 확인",
            "설치·이전·소프트웨어·유지보수 포함 여부를 물품과 용역으로 구분",
        ),
        recommend_mas_check=True,
    ),
    GoodsCategory.EDUCATIONAL_EQUIPMENT: GoodsCategoryProfile(
        GoodsCategory.EDUCATIONAL_EQUIPMENT,
        "교육·실험기자재",
        "규격 적합성 확인 후 일반 물품계약",
        checks=(
            "교육용·실험용 안전인증과 필수 성능규격 확인",
            "특정 모델 지정 시 동등이상 허용 여부와 지정사유 검토",
        ),
        recommend_mas_check=True,
    ),
    GoodsCategory.KITCHEN_EQUIPMENT: GoodsCategoryProfile(
        GoodsCategory.KITCHEN_EQUIPMENT,
        "급식기구·주방기기",
        "설치공사 포함 여부를 먼저 구분한 뒤 물품계약",
        checks=(
            "단순 납품인지 배관·전기·가스 등 설치공사가 포함되는지 확인",
            "위생·안전인증 및 급식실 현장규격 확인",
        ),
        recommend_mas_check=True,
    ),
    GoodsCategory.FOOD_INGREDIENTS: GoodsCategoryProfile(
        GoodsCategory.FOOD_INGREDIENTS,
        "학교급식 식재료",
        "급식 식재료 전용 자격·배제 확인을 포함한 물품계약",
        legal_bases=("학교급식법 제15조의2", "학교급식법 시행령 제12조의2"),
        checks=(
            "식품위생·축산물 위생·원산지 표시 관련 자격과 위반이력 확인",
            "학교급식 식재료 품질·안전기준과 원산지·등급 조건 확인",
            "식재료 구매계약 입찰참가 제한 또는 수의계약 배제 대상 여부 확인",
        ),
        quantity_variable=True,
    ),
    GoodsCategory.MILK: GoodsCategoryProfile(
        GoodsCategory.MILK,
        "학교급식 우유",
        "단가계약 + 예정수량 변동형 소액수의·입찰",
        legal_bases=("학교급식법",),
        checks=(
            "학사일정·희망인원 변동에 따라 예정수량이 증감할 수 있음을 공고에 명시",
            "냉장상태 유지·일일 분할납품·보관설비 등 학교 우유급식 특수조건 확인",
            "HACCP 등 공고에서 요구하는 위생·품질 증빙 확인",
        ),
        default_unit_price_contract=True,
        quantity_variable=True,
    ),
    GoodsCategory.BOOKS: GoodsCategoryProfile(
        GoodsCategory.BOOKS,
        "도서·간행물",
        "도서정가제를 반영한 물품구매",
        legal_bases=("출판문화산업 진흥법 제22조",),
        checks=(
            "도서정가제 적용 간행물인지 확인",
            "가격할인은 정가의 10% 이내인지 확인",
            "경제상 이익과 합산한 할인한도 등 현행 도서정가제 기준 확인",
        ),
        default_publication=True,
        recommend_sme_check=False,
    ),
    GoodsCategory.UNIFORM: GoodsCategoryProfile(
        GoodsCategory.UNIFORM,
        "교복·체육복",
        "2단계 규격·가격 동시입찰 검토",
        legal_bases=("지방계약법 시행령 제18조",),
        checks=(
            "제안서·견본품·제조사양·품질평가기준을 공고 전에 확정",
            "규격적격자에 한해 가격개찰하는 2단계 입찰 적용 여부 확인",
            "품목별 단가와 추가구매 조건을 특수조건에 명시",
        ),
        requires_two_stage=True,
    ),
    GoodsCategory.OTHER: GoodsCategoryProfile(
        GoodsCategory.OTHER,
        "기타 물품",
        "일반 물품계약",
        checks=("세부품명·구매방식·중소기업제품 여부를 개별 확인",),
    ),
}


def get_goods_profile(category: GoodsCategory, planned_date: date) -> GoodsCategoryProfile:
    profile = _BASE[category]
    if category == GoodsCategory.FOOD_INGREDIENTS and planned_date < date(2026, 8, 20):
        return GoodsCategoryProfile(
            code=profile.code,
            label=profile.label,
            purchase_method_hint=profile.purchase_method_hint,
            legal_bases=("학교급식법",),
            checks=tuple(
                check
                for check in profile.checks
                if "입찰참가 제한" not in check
            ),
            warnings=(
                "학교급식법 제15조의2 및 시행령 제12조의2는 2026-08-20 이후 공고·수의계약부터 적용됩니다.",
            ),
            quantity_variable=profile.quantity_variable,
        )
    return profile


def list_goods_profiles(planned_date: date | None = None) -> list[GoodsCategoryProfile]:
    target = planned_date or date.today()
    return [get_goods_profile(code, target) for code in GoodsCategory]
