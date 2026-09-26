"""학교 시설공사 공고문 및 계약문서 세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.works import WorksResult, WorksRoute


@dataclass(slots=True)
class WorksDocumentData:
    school_name: str
    work_name: str
    location: str
    start_date: date | None
    completion_days: int
    estimated_price: int
    base_amount: int | None = None
    budget_amount: int | None = None
    scope_text: str = "[공사범위 입력 필요]"
    required_industry: str = ""
    design_summary: str = "[설계·내역 요약 입력 필요]"
    safety_text: str = "산업안전보건법 등 관계법령에 따른 안전조치"
    notice_number: str = ""
    bid_start: str = "[입력 필요]"
    bid_end: str = "[입력 필요]"
    bid_open: str = "[입력 필요]"
    region_limit: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    a_value_total: int | None = None
    insurance_breakdown_text: str = "[국민연금·건강보험·퇴직공제·산업안전보건관리비 등 세부금액 입력 필요]"
    site_explanation: str = "별도의 현장설명은 생략하고 설계서·내역서 열람으로 갈음"
    joint_supply_allowed: bool = False
    rebid_allowed: bool = True


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def _value(value: str, fallback: str = "[입력 필요]") -> str:
    return value.strip() if value and value.strip() else fallback


def _notice_title(data: WorksDocumentData, rule: WorksResult) -> str:
    if rule.route_code == WorksRoute.ONE_PERSON:
        return f"{data.work_name} 수의계약 견적요청서"
    if rule.route_code == WorksRoute.TWO_PERSON:
        return f"{data.work_name} 수의계약 견적제출 안내공고"
    return f"{data.work_name} 공사 입찰공고"


def _award_text(data: WorksDocumentData, rule: WorksResult) -> str:
    if rule.route_code == WorksRoute.ONE_PERSON:
        return (
            "견적금액, 설계내역 적합성, 공사업 등록자격, 수의계약 배제사유를 확인하여 "
            "계약상대자를 결정합니다."
        )
    if rule.route_code == WorksRoute.TWO_PERSON:
        a = _money(data.a_value_total)
        return (
            f"예정가격 이하인 자 중 예정가격에서 A값({a})을 뺀 금액 대비 "
            f"견적가격에서 동일 A값을 뺀 금액이 {(rule.minimum_quote_rate or 0)*100:.3f}% 이상인 "
            "최저가격 제출자부터 순서대로 수의계약 배제사유를 확인하여 계약상대자를 결정합니다."
        )
    return (
        "예정가격 이하 최저가격 제출자 순으로 공고일 현재 적용되는 지방자치단체 "
        "시설공사 적격심사 세부기준을 적용하여 종합평점 등 낙찰기준을 충족한 자를 낙찰자로 결정합니다."
    )


def build_works_documents(data: WorksDocumentData, rule: WorksResult) -> list[GeneratedDocument]:
    title = _notice_title(data, rule)
    schedule = (
        f"- 견적·입찰 개시: {data.bid_start}\n"
        f"- 견적·입찰 마감: {data.bid_end}\n"
        f"- 개찰: {data.bid_open}"
        if rule.route_code != WorksRoute.ONE_PERSON
        else "- 견적서 제출기한: [입력 필요]\n- 제출방법: 학교가 정한 방법"
    )

    notice=f"""# {title}

- 공고번호: {_value(data.notice_number)}
- 발주기관: {data.school_name}

견적·입찰 참가자는 본 공고문, 설계서, 내역서, 시방서, 계약 일반조건·특수조건,
지방계약 관계법령 및 전자입찰 특별유의서를 충분히 숙지한 후 참가하여야 합니다.

## 1. 공사에 부치는 사항
- 공사명: {data.work_name}
- 공사현장: {data.location}
- 공사기간: 착공일부터 {data.completion_days}일
- 공사내용: {data.scope_text}
- 예산금액: {_money(data.budget_amount)}
- 기초금액: {_money(data.base_amount)}
- 추정가격: {_money(data.estimated_price)}
- A값(해당 시): {_money(data.a_value_total)}
- 공동수급: {'허용' if data.joint_supply_allowed else '불허'}

## 2. 계약방법
- {rule.contract_method}
- 공사유형별 수의계약 금액상한: {_money(rule.small_value_limit)}
- 전자견적·입찰: {'적용' if rule.designated_system_required else '필수 아님'}
- 적격심사: {'공고일 기준 시설공사 적격심사 적용기준 확인' if rule.route_code == WorksRoute.COMPETITIVE else '소액수의 견적제출은 별도 적격심사 없이 배제사유 확인'}

## 3. 견적·입찰 일정
{schedule}

## 4. 참가자격
- 지방계약법 시행령 제13조 및 시행규칙 제14조의 참가자격을 갖춘 자
- 관계 공사업법상 요구 업종·주력분야: {_value(data.required_industry)}
- 입찰·견적 마감일까지 나라장터 등 지정정보처리장치에 필요한 참가자격 등록을 완료한 자
{f'- 지역제한: {data.region_limit}' if data.region_limit else '- 지역제한: 적용 여부 및 소재지 기준 확인'}
- 공고일 현재 등록기준(기술능력·자본금 등)을 충족하고 영업정지 등 참가제한 사유가 없는 자

## 5. 현장설명 및 설계서 열람
- {data.site_explanation}
- 참가자는 현장여건, 학생·교직원 동선, 공사시간, 자재반입, 소음·분진 등 시공조건을 충분히 확인하여 견적·입찰가격에 반영해야 합니다.

## 6. 예정가격
- 기초금액의 ±3% 범위에서 서로 다른 복수예비가격 15개를 작성하고,
  참가자가 각 2개씩 선택한 결과 다빈도순 4개 가격을 산술평균하여 예정가격으로 결정합니다.

## 7. 계약상대자·낙찰자 결정
- {_award_text(data, rule)}
- 동일가격 제출자가 2인 이상인 경우 관계법령 및 전자입찰특별유의서에 따라 전자추첨 등으로 결정합니다.
- 재입찰·재견적: {'허용할 수 있으며 별도의 개별통보 없이 시스템에서 확인' if data.rebid_allowed else '허용하지 않음'}

## 8. 국민건강보험료 등 법정경비
- 입찰·견적금액 산정 시 예정가격에 계상된 국민연금보험료, 국민건강보험료,
  노인장기요양보험료, 퇴직공제부금비, 산업안전보건관리비, 안전관리비,
  품질관리비 등 관계규정이 정한 금액은 조정 없이 반영합니다.
- A값 합계: {_money(data.a_value_total)}
- 세부내역: {data.insurance_breakdown_text}
- 계약이행 후 관계법령과 지방자치단체 입찰 및 계약 집행기준에 따라 사후정산합니다.

## 9. 공사근로자 노무비 및 하도급
- 관계법령과 지방자치단체 공사계약 일반조건에 따른 노무비 구분관리·지급확인제 적용 여부를 확인하고 준수합니다.
- 불법하도급을 금지하며 하도급이 허용되는 경우 관계법령에 따른 통보·승인·대금지급 절차를 준수합니다.

## 10. 안전 및 중대재해
- 산업안전보건법 등 관계법령에 따른 안전조치를 준수합니다.
- 학생·교직원과 공사구역을 분리하고 학교 특성에 맞는 안전관리계획을 수립합니다.
- 중대재해처벌법 등 적용대상인 경우 발주기관의 안전·보건 확보절차에 협조합니다.

## 11. 입찰보증금 및 무효
- {'수의계약 견적제출이므로 입찰보증금 납부대상이 아닙니다.' if rule.route_code != WorksRoute.COMPETITIVE else '경쟁입찰의 입찰보증금은 지방계약법 시행령 제37조 및 공고조건에 따릅니다.'}
- 입찰·견적의 무효는 지방계약법 시행령 제39조, 시행규칙 제42조 및 전자입찰 특별유의서 등에 따릅니다.

## 12. 청렴계약·수의계약 체결 제한
- 참가자는 청렴서약 조건을 준수해야 합니다.
- 수의계약인 경우 수의계약 배제사유와 공직자의 이해충돌 방지법상 체결 제한을 확인합니다.

## 13. 계약·착공·준공
- 계약상대자는 통지를 받은 후 학교가 정한 기한 내 전자계약을 체결하고 착공서류를 제출합니다.
- 공사 완료 후 준공계, 준공사진, 시험·검사자료, 폐기물처리 증빙, 하자보증 관련 서류 등 해당서류를 제출합니다.

## 14. 문의
- 담당자: {_value(data.contact_name)}
- 연락처: {_value(data.contact_phone)}

※ 본 공고문은 자동생성 초안입니다. 게시 전 계약담당자가 공사업 등록,
상호시장·주력분야, A값, 법정경비, 적격심사 기준, 지역제한 및 최신 예규를 최종 확인해야 합니다.
"""

    scope=f"""# {data.work_name} 공사 시방·과업 요약

## 1. 공사범위
{data.scope_text}

## 2. 설계·내역
{data.design_summary}

## 3. 자재
- 설계서·시방서의 규격을 준수한다.
- 주요 자재의 승인·검수 절차를 따른다.

## 4. 안전
- {data.safety_text}
- 학생·교직원 동선과 공사구역을 분리한다.
- 소음·분진·화재·추락·감전 등 학교 공사 위험요인을 관리한다.
"""

    conditions=f"""# {data.work_name} 공사계약 특수조건

## 제1조 착공
계약상대자는 계약 후 정해진 기간 내 착공계·공정표·현장대리인계 등 필요한 서류를 제출한다.

## 제2조 현장관리
학생안전과 교육활동을 우선하고 학교와 공정·작업시간을 협의한다.

## 제3조 법정경비
국민연금·건강보험·퇴직공제·산업안전보건관리비 등 법정경비는 관계규정과 산출내역에 따라 관리·정산한다.

## 제4조 설계변경
현장여건 또는 학교요청으로 설계변경이 필요한 경우 임의시공하지 않고 계약담당자와 협의한다.

## 제5조 준공
준공검사에 필요한 준공계, 사진, 시험성적서, 폐기물처리증빙 등 해당 서류를 제출한다.

## 제6조 하자
공종별 법정 하자담보책임기간과 계약조건에 따라 하자보수를 이행한다.
"""

    checklist=f"""# {data.work_name} 착공·준공 서류 체크리스트

## 착공
- 착공계
- 현장대리인계
- 기술자 자격·재직증빙
- 예정공정표
- 산출내역서
- 안전관리 관련 서류
- 보험·퇴직공제 등 해당 서류

## 시공 중
- 자재승인
- 공정사진
- 설계변경·추가공사 승인
- 폐기물 처리
- 안전점검

## 준공
- 준공계
- 준공내역
- 준공사진
- 시험·검사성적서
- 폐기물처리 확인
- 하자보증 관련 서류
"""

    return [
        GeneratedDocument("notice", title, notice),
        GeneratedDocument("scope", f"{data.work_name} 공사과업", scope),
        GeneratedDocument("conditions", f"{data.work_name} 공사 특수조건", conditions),
        GeneratedDocument("checklist", f"{data.work_name} 착공준공 체크리스트", checklist),
    ]
