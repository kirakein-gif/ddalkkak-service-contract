"""학교 실무 중심 공사유형 카탈로그.

사용자가 학교에서 익숙한 공사명을 고르면 법정 공사구분·추천 업종·주력분야를
뒤에서 연결한다. 추천값은 공사범위에 따라 달라질 수 있으므로 최종 확정이 아니라
계약담당자의 업종 검토를 돕는 용도다.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from app.rules.works import WorksType


class SchoolWorkType(StrEnum):
    GENERAL_BUILDING = "GENERAL_BUILDING"
    INTERIOR = "INTERIOR"
    PAINT = "PAINT"
    WET_WATERPROOF = "WET_WATERPROOF"
    WINDOW_METAL = "WINDOW_METAL"
    ROOF_ASSEMBLY = "ROOF_ASSEMBLY"
    DEMOLITION_SCAFFOLD = "DEMOLITION_SCAFFOLD"
    PAVING_EARTH = "PAVING_EARTH"
    WATER_SEWER = "WATER_SEWER"
    LANDSCAPE = "LANDSCAPE"
    MECHANICAL = "MECHANICAL"
    ELECTRICAL = "ELECTRICAL"
    TELECOM = "TELECOM"
    FIRE = "FIRE"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class WorksCategoryProfile:
    code: SchoolWorkType
    label: str
    works_type: WorksType
    recommended_industry: str
    recommended_main_field: str = ""
    examples: tuple[str, ...] = ()
    legal_bases: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _p(
    code: SchoolWorkType,
    label: str,
    works_type: WorksType,
    industry: str,
    main_field: str = "",
    *,
    examples: tuple[str, ...] = (),
    legal_bases: tuple[str, ...] = (),
    checks: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> WorksCategoryProfile:
    return WorksCategoryProfile(
        code=code,
        label=label,
        works_type=works_type,
        recommended_industry=industry,
        recommended_main_field=main_field,
        examples=examples,
        legal_bases=legal_bases,
        checks=checks,
        warnings=warnings,
    )


WORKS_PROFILES: dict[SchoolWorkType, WorksCategoryProfile] = {
    SchoolWorkType.GENERAL_BUILDING: _p(
        SchoolWorkType.GENERAL_BUILDING,
        "종합 건축공사",
        WorksType.GENERAL,
        "건축공사업",
        examples=("증축", "대규모 개축", "여러 전문공종을 종합 관리하는 건축공사"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("전문공사 단독 발주로 가능한 범위인지 먼저 검토",),
    ),
    SchoolWorkType.INTERIOR: _p(
        SchoolWorkType.INTERIOR,
        "교실·특별실 리모델링 / 실내건축",
        WorksType.SPECIALIZED,
        "실내건축공사업",
        "실내건축공사",
        examples=("교실 바닥·천장·벽체 마감", "특별실 리모델링", "붙박이 집기 설치"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("도장공사나 석공사만으로 시공되는 단일공종인지 확인",),
    ),
    SchoolWorkType.PAINT: _p(
        SchoolWorkType.PAINT,
        "도장",
        WorksType.SPECIALIZED,
        "도장·습식·방수·석공사업",
        "도장공사",
        examples=("교사동 내·외부 도장", "재도장", "차선·주차선 도색"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
    ),
    SchoolWorkType.WET_WATERPROOF: _p(
        SchoolWorkType.WET_WATERPROOF,
        "방수·미장·타일·조적",
        WorksType.SPECIALIZED,
        "도장·습식·방수·석공사업",
        "습식·방수공사",
        examples=("옥상 방수", "화장실 방수", "미장", "타일", "벽돌·블록 조적"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("공사내역이 도장 주력인지 습식·방수 주력인지 구분",),
    ),
    SchoolWorkType.WINDOW_METAL: _p(
        SchoolWorkType.WINDOW_METAL,
        "창호·금속·캐노피",
        WorksType.SPECIALIZED,
        "금속·창호·지붕·건축물조립공사업",
        "금속구조물·창호·온실공사",
        examples=("알루미늄·PVC 창호", "금속난간", "캐노피", "금속구조물"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
    ),
    SchoolWorkType.ROOF_ASSEMBLY: _p(
        SchoolWorkType.ROOF_ASSEMBLY,
        "지붕·판금·건축물조립",
        WorksType.SPECIALIZED,
        "금속·창호·지붕·건축물조립공사업",
        "지붕판금·건축물조립공사",
        examples=("지붕판금", "패널", "조립식 건축물"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
    ),
    SchoolWorkType.DEMOLITION_SCAFFOLD: _p(
        SchoolWorkType.DEMOLITION_SCAFFOLD,
        "철거·비계",
        WorksType.SPECIALIZED,
        "구조물해체·비계공사업",
        "구조물해체·비계공사",
        examples=("건축물·구조물 철거", "비계 설치·해체"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("해체계획서·해체허가 또는 신고 대상 여부 별도 확인",),
    ),
    SchoolWorkType.PAVING_EARTH: _p(
        SchoolWorkType.PAVING_EARTH,
        "운동장·포장·토공",
        WorksType.SPECIALIZED,
        "지반조성·포장공사업",
        "토공사 또는 포장공사",
        examples=("아스콘·콘크리트 포장", "운동장 정비", "토공"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("토공사와 포장공사 중 주된 공종 확인",),
    ),
    SchoolWorkType.WATER_SEWER: _p(
        SchoolWorkType.WATER_SEWER,
        "급배수·상하수도",
        WorksType.SPECIALIZED,
        "상·하수도설비공사업",
        "상하수도설비공사",
        examples=("급수관", "배수관", "하수관", "맨홀"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
    ),
    SchoolWorkType.LANDSCAPE: _p(
        SchoolWorkType.LANDSCAPE,
        "조경·놀이시설·외부시설",
        WorksType.SPECIALIZED,
        "조경식재·시설물공사업",
        "조경식재공사 또는 조경시설물설치공사",
        examples=("수목 식재", "조경 유지관리", "조경시설물", "학교숲"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("식재 중심인지 시설물 설치 중심인지 주력분야 확인",),
    ),
    SchoolWorkType.MECHANICAL: _p(
        SchoolWorkType.MECHANICAL,
        "기계설비·냉난방",
        WorksType.SPECIALIZED,
        "기계설비·가스공사업",
        "기계설비공사",
        examples=("냉난방 설비", "배관", "기계실 설비", "자동제어"),
        legal_bases=("건설산업기본법 시행령 제7조·별표 1",),
        checks=("가스공사 포함 시 가스시설공사 주력분야를 별도 확인",),
    ),
    SchoolWorkType.ELECTRICAL: _p(
        SchoolWorkType.ELECTRICAL,
        "전기공사",
        WorksType.OTHER,
        "전기공사업",
        examples=("조명", "분전반", "전원", "전기배선"),
        legal_bases=("전기공사업법",),
        checks=("건설산업기본법 전문공사와 혼동하지 않고 전기공사업 등록 여부 확인",),
    ),
    SchoolWorkType.TELECOM: _p(
        SchoolWorkType.TELECOM,
        "정보통신공사",
        WorksType.OTHER,
        "정보통신공사업",
        examples=("LAN", "방송", "CCTV", "통신배선"),
        legal_bases=("정보통신공사업법",),
        checks=("정보통신공사업 등록과 공사범위의 적합성 확인",),
    ),
    SchoolWorkType.FIRE: _p(
        SchoolWorkType.FIRE,
        "소방시설공사",
        WorksType.OTHER,
        "공사범위에 맞는 소방시설공사업",
        examples=("감지기", "수신기", "소화설비", "스프링클러"),
        legal_bases=("소방시설공사업법",),
        checks=("전문소방시설공사업·일반소방시설공사업 등 공사범위에 맞는 등록종류 확인",),
    ),
    SchoolWorkType.OTHER: _p(
        SchoolWorkType.OTHER,
        "기타 공사",
        WorksType.SPECIALIZED,
        "[공사범위에 맞는 업종 확인 필요]",
        checks=("설계내역의 주된 공종을 기준으로 업종·주력분야를 별도 검토",),
        warnings=("복합공종은 단순 키워드로 업종을 확정하지 않습니다.",),
    ),
}


def get_works_profile(code: SchoolWorkType) -> WorksCategoryProfile:
    return WORKS_PROFILES[code]


def list_works_profiles() -> list[WorksCategoryProfile]:
    return list(WORKS_PROFILES.values())
