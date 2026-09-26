"""학교 실무 기준 용역 세부유형 카탈로그.

용역은 계약방법만으로는 문서의 품질이 나지 않는다. 학교에서 먼저 고르는
업무유형과, 그 뒤에 확인할 면허·절차·문서세트를 분리해 관리한다. 이 파일의
값은 자동 확정값이 아니라 공고 전 검토 목록을 만드는 기준 데이터다.
"""

from dataclasses import dataclass
from enum import StrEnum


class SchoolServiceType(StrEnum):
    TRANSPORT = "TRANSPORT"
    TRAVEL = "TRAVEL"
    AFTER_SCHOOL = "AFTER_SCHOOL"
    FACILITY_MAINTENANCE = "FACILITY_MAINTENANCE"
    STATUTORY_INSPECTION = "STATUTORY_INSPECTION"
    CLEANING = "CLEANING"
    DISINFECTION = "DISINFECTION"
    GENERAL = "GENERAL"


@dataclass(frozen=True, slots=True)
class ServiceCategoryProfile:
    code: SchoolServiceType
    label: str
    group_label: str
    document_route: str
    contract_method_hint: str
    legal_bases: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


SERVICE_PROFILES: dict[SchoolServiceType, ServiceCategoryProfile] = {
    SchoolServiceType.TRANSPORT: ServiceCategoryProfile(
        SchoolServiceType.TRANSPORT, "통학차량·통학버스", "용역", "transport",
        "추정가격·중소기업제품 여부에 따른 수의계약 또는 경쟁입찰",
        legal_bases=("여객자동차 운수사업법", "도로교통법", "지방계약 관계법령"),
        checks=("전세버스운송사업 등록", "어린이통학버스 적용 여부", "SMPP 세부품명·직접생산", "차량·보험·운전자·노선"),
    ),
    SchoolServiceType.TRAVEL: ServiceCategoryProfile(
        SchoolServiceType.TRAVEL, "수학여행·현장체험학습", "용역", "travel",
        "제안서 평가가 필요한 경우 2단계 규격·가격 동시입찰 우선 검토",
        legal_bases=("지방계약법 시행령 제18조", "관광진흥법", "학교 현장체험학습 안전 관련 지침"),
        checks=("여행업 등록", "숙박·식사·운송 안전조건", "제안요청서·평가기준", "참가인원 증감 정산"),
        warnings=("80점 등 제안서 통과점수는 법정 고정값이 아니며 학교가 공고 전에 확정합니다.",),
    ),
    SchoolServiceType.AFTER_SCHOOL: ServiceCategoryProfile(
        SchoolServiceType.AFTER_SCHOOL, "방과후·늘봄", "용역", "program",
        "운영능력·강사·프로그램 평가가 필요한 경우 2단계 입찰 우선 검토",
        legal_bases=("지방계약법 시행령 제18조",),
        checks=("제안서·평가기준", "강사 자격·결격 확인", "학생수·차시 변동 정산", "교재·재료비 부담"),
    ),
    SchoolServiceType.FACILITY_MAINTENANCE: ServiceCategoryProfile(
        SchoolServiceType.FACILITY_MAINTENANCE, "시설 유지관리", "용역", "facility",
        "일반 유지관리와 설계·감리·기술용역을 먼저 구분",
        checks=("시설별 등록·면허", "기술인력·장비", "점검범위·보고서", "긴급대응·손해배상"),
        warnings=("설계·감리·PQ 대상은 일반 유지관리용역 Rule Engine으로 확정하지 않습니다.",),
    ),
    SchoolServiceType.STATUTORY_INSPECTION: ServiceCategoryProfile(
        SchoolServiceType.STATUTORY_INSPECTION, "법정점검", "용역", "facility",
        "시설별 개별 법령상 등록·점검주기 확인 후 계약방법 판정",
        checks=("개별 법령", "점검기관 등록", "기술인력", "법정 점검·보고 기한"),
        warnings=("소방·승강기·전기·가스 등 법정점검은 시설분야별 법령을 반드시 지정해야 합니다.",),
    ),
    SchoolServiceType.CLEANING: ServiceCategoryProfile(
        SchoolServiceType.CLEANING, "청소", "용역", "labor",
        "단순노무용역의 원가·근로조건을 반영해 수의계약 또는 경쟁입찰 검토",
        checks=("최저임금·4대보험·퇴직급여", "투입인원·근로시간", "작업구역·소모품", "근로자 보호"),
    ),
    SchoolServiceType.DISINFECTION: ServiceCategoryProfile(
        SchoolServiceType.DISINFECTION, "방역·소독", "용역", "labor",
        "단순노무 조건과 소독업 등 개별 자격을 함께 검토",
        legal_bases=("감염병의 예방 및 관리에 관한 법률",),
        checks=("소독업 신고 등 자격", "약품·장비", "학생 동선 안전", "작업기록·결과보고"),
    ),
    SchoolServiceType.GENERAL: ServiceCategoryProfile(
        SchoolServiceType.GENERAL, "기타 학교 일반용역", "용역", "general",
        "수의계약 금액기준과 해당 과업의 면허·자격을 함께 검토",
        checks=("과업지시서", "참가자격", "중소기업제품·직접생산", "안전·개인정보·정산 조건"),
    ),
}
def get_service_profile(code: SchoolServiceType) -> ServiceCategoryProfile:
    return SERVICE_PROFILES[code]
def list_service_profiles() -> list[ServiceCategoryProfile]:
    return list(SERVICE_PROFILES.values())
