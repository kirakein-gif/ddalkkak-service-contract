"""학교 시설공사 공고문 및 계약문서 세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.documents.g2b_notice import (
    G2B_SPECIAL_NOTICE,
    electronic_contract_lines,
    electronic_submission_lines,
    equal_price_lottery_line,
    preliminary_price_lines,
)
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
    school_work_type_label: str = "기타 공사"
    recommended_main_field: str = ""
    design_summary: str = "[설계·내역 요약 입력 필요]"
    safety_text: str = "산업안전보건법 등 관계법령에 따른 안전조치"
    notice_number: str = ""
    notice_date: date | None = None
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
        return f"{data.work_name} 수의계약 전자견적 제출 안내공고"
    return f"{data.work_name} 공사 전자입찰 공고"


def _award_text(data: WorksDocumentData, rule: WorksResult) -> str:
    if rule.route_code == WorksRoute.ONE_PERSON:
        return "견적금액, 설계내역 적합성, 공사업 등록자격, 수의계약 배제사유를 확인하여 계약상대자를 결정합니다."
    if rule.route_code == WorksRoute.TWO_PERSON:
        return (
            f"예정가격 이하인 자 중 예정가격에서 A값({_money(data.a_value_total)})을 뺀 금액 대비 "
            f"견적가격에서 같은 A값을 뺀 금액이 {(rule.minimum_quote_rate or 0)*100:.3f}% 이상인 "
            "최저가격 제출자부터 순서대로 수의계약 배제사유를 확인하여 계약상대자를 결정합니다."
        )
    return (
        "예정가격 이하 최저가격 입찰자 순으로 공고일 현재 적용되는 지방자치단체 시설공사 적격심사 기준을 적용하여 "
        "종합평점 등 낙찰기준을 충족한 자를 낙찰자로 결정합니다."
    )


def build_works_documents(data: WorksDocumentData, rule: WorksResult) -> list[GeneratedDocument]:
    title = _notice_title(data, rule)
    label = "견적서" if rule.route_code != WorksRoute.COMPETITIVE else "입찰서"
    schedule = (
        f"- 견적·입찰 개시: {data.bid_start}\n- 견적·입찰 마감: {data.bid_end}\n- 개찰일시 및 장소: {data.bid_open} / 발주기관 입찰집행관 PC"
        if rule.route_code != WorksRoute.ONE_PERSON
        else "- 견적서 제출기한: [입력 필요]\n- 제출방법: 학교가 정한 방법"
    )
    submission = electronic_submission_lines(label)
    prices = preliminary_price_lines()
    contract_lines = electronic_contract_lines(
        small_value=rule.route_code != WorksRoute.COMPETITIVE
    )
    bond = (
        "수의계약 견적제출이므로 입찰보증금 납부대상이 아닙니다."
        if rule.route_code != WorksRoute.COMPETITIVE
        else "입찰보증금은 지방계약법 시행령 제37조 및 공고조건에 따르며, 전자입찰서의 납부확약으로 갈음하는 경우 해당 전자서식에 따릅니다."
    )

    notice=f"""# {title}

- 공고번호: {_value(data.notice_number)}
- 발주기관: {data.school_name}

견적·입찰 참가자는 본 공고문, 설계서, 내역서, 시방서, 공사계약 일반조건·특수조건, 지방자치단체 입찰 및 계약 집행기준, {G2B_SPECIAL_NOTICE} 등 입찰·계약에 필요한 모든 사항을 숙지한 후 참가하여야 합니다.

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

## 2. 견적제출·입찰 및 계약방식
- 학교 공사유형: {data.school_work_type_label}
- 추천 업종·주력분야: {data.required_industry}{f' / {data.recommended_main_field}' if data.recommended_main_field else ''}
- 계약방법: {rule.contract_method}
- 전자견적·입찰: {'국가종합전자조달시스템(G2B) 적용' if rule.route_code != WorksRoute.ONE_PERSON else '학교가 정한 방법'}
- 전자계약, 청렴계약제 시행 대상입니다.
- 공사유형별 수의계약 금액상한: {_money(rule.small_value_limit)}
- 적격심사: {'공고일 기준 시설공사 적격심사 적용기준 확인' if rule.route_code == WorksRoute.COMPETITIVE else '소액수의 견적제출은 별도 적격심사 없이 배제사유 확인'}

## 3. 견적·입찰 및 개찰 일정
{schedule}

## 4. 참가자격
- 지방계약법 시행령 제13조 및 시행규칙 제14조의 참가자격을 갖춘 자
- 관계 공사업법상 요구 업종·주력분야: {_value(data.required_industry)}
- 전자견적·입찰인 경우 제출마감일까지 나라장터에 필요한 참가자격 등록을 완료한 자
{f'- 지역제한: {data.region_limit}' if data.region_limit else '- 지역제한: 적용 여부 및 소재지 기준 확인'}
- 공고일 현재 등록기준을 충족하고 영업정지 등 참가제한 사유가 없는 자

## 5. 전자견적·입찰서 제출 유의사항
{chr(10).join(f'- {line}' for line in submission)}

## 6. 현장설명 및 설계서 열람
- {data.site_explanation}
- 참가자는 현장여건, 학생·교직원 동선, 공사시간, 자재반입, 소음·분진 등 시공조건을 충분히 확인하여 견적·입찰가격에 반영해야 합니다.

## 7. 예정가격
{chr(10).join(f'- {line}' for line in prices)}

## 8. 계약상대자·낙찰자 결정
- {_award_text(data, rule)}
- {equal_price_lottery_line()}
- 재입찰·재견적: {'허용할 수 있으며 별도의 개별통보 없이 나라장터 개찰결과와 재입찰 일정을 확인' if data.rebid_allowed else '허용하지 않음'}

## 9. 국민건강보험료 등 법정경비 및 A값
- 입찰·견적금액 산정 시 예정가격에 계상된 국민연금보험료, 국민건강보험료, 노인장기요양보험료, 퇴직공제부금비, 산업안전보건관리비, 안전관리비, 품질관리비 등 관계규정이 정한 금액은 조정 없이 반영합니다.
- A값 합계: {_money(data.a_value_total)}
- 세부내역: {data.insurance_breakdown_text}
- 계약이행 후 관계법령과 지방자치단체 입찰 및 계약 집행기준에 따라 사후정산합니다.

## 10. 입찰보증금 및 견적·입찰의 무효
- {bond}
- 지방계약법 시행령 제39조, 시행규칙 제42조 및 국가종합전자조달시스템 전자입찰특별유의서 등 관계규정에 따른 무효사유에 해당하는 견적·입찰은 무효입니다.

## 11. 전자계약 체결
{chr(10).join(f'- {line}' for line in contract_lines)}
- 계약 체결 후 착공계, 현장대리인계, 공정표, 산출내역서 등 해당 착공서류를 제출합니다.

## 12. 공사근로자 노무비·하도급 및 안전
- 관계법령과 지방자치단체 공사계약 일반조건에 따른 노무비 구분관리·지급확인제 적용 여부를 확인하고 준수합니다.
- 불법하도급을 금지하며, 하도급이 허용되는 경우 관계법령에 따른 통보·승인·대금지급 절차를 준수합니다.
- {data.safety_text}
- 학생·교직원과 공사구역을 분리하고 학교 특성에 맞는 안전관리계획을 수립합니다.

## 13. 청렴계약·수의계약 체결 제한
- 참가자는 청렴계약 조건을 숙지·준수하여야 합니다.
- 수의계약은 수의계약 배제사유와 공직자의 이해충돌 방지법상 수의계약 체결 제한 여부를 확인합니다.

## 14. 준공·하자 및 기타사항
- 공사 완료 후 준공계, 준공사진, 시험·검사자료, 폐기물처리 증빙, 하자보증 관련 서류 등 해당서류를 제출합니다.
- 공종별 법정 하자담보책임기간과 계약조건에 따라 하자보수를 이행합니다.
- 전자입찰 시스템 문의: 정부조달 콜센터 1588-0800
- 계약담당자: {_value(data.contact_name)}
- 연락처: {_value(data.contact_phone)}
"""

    scope=f"""# {data.work_name} 공사 시방·과업 요약

## 1. 공사범위
{data.scope_text}

## 2. 설계·내역
{data.design_summary}

## 3. 자재
- 설계서·시방서의 규격을 준수합니다.
- 주요 자재의 승인·검수 절차를 따릅니다.

## 4. 안전
- {data.safety_text}
- 학생·교직원 동선과 공사구역을 분리합니다.
- 소음·분진·화재·추락·감전 등 학교 공사 위험요인을 관리합니다.
"""

    conditions=f"""# {data.work_name} 공사계약 특수조건

## 제1조 착공
계약상대자는 계약 후 정해진 기간 내 착공계·공정표·현장대리인계 등 필요한 서류를 제출합니다.

## 제2조 현장관리
학생안전과 교육활동을 우선하고 학교와 공정·작업시간을 협의합니다.

## 제3조 법정경비
국민연금·건강보험·퇴직공제·산업안전보건관리비 등 법정경비는 관계규정과 산출내역에 따라 관리·정산합니다.

## 제4조 설계변경
현장여건 또는 학교요청으로 설계변경이 필요한 경우 임의시공하지 않고 계약담당자와 협의합니다.

## 제5조 준공
준공검사에 필요한 준공계, 사진, 시험성적서, 폐기물처리증빙 등 해당 서류를 제출합니다.

## 제6조 하자
공종별 법정 하자담보책임기간과 계약조건에 따라 하자보수를 이행합니다.
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

    summary = (
        ("공 사 명", data.work_name, "", ""),
        ("학교 공사유형", data.school_work_type_label, "추천 주력분야", data.recommended_main_field or "별도 확인"),
        ("공사현장", data.location, "공사기간", f"착공일부터 {data.completion_days}일"),
        ("기초금액", _money(data.base_amount), "추정가격", _money(data.estimated_price)),
        ("A 값", _money(data.a_value_total), "요구업종", _value(data.required_industry)),
        ("전자견적서 제출기간", f"{data.bid_start} ~ {data.bid_end}" if rule.route_code != WorksRoute.ONE_PERSON else "[입력 필요]", "", ""),
        ("개찰일시 및 장소", f"{data.bid_open} / 발주기관 입찰집행관 PC" if rule.route_code != WorksRoute.ONE_PERSON else "해당 없음", "", ""),
    )

    notice_doc = GeneratedDocument(
        "notice",
        title,
        notice,
        layout="public_notice",
        notice_number=_value(data.notice_number),
        issuer=data.school_name,
        summary_rows=summary,
        issue_date=data.notice_date.isoformat() if data.notice_date else "",
        signatory=f"{data.school_name}장",
        alert_text=(
            "규정 착오 또는 관계 규정의 미숙지 등으로 계약을 체결하지 않거나 계약을 체결하고 불이행하는 경우, "
            "관계 법령에 따라 부정당업자로 제재되어 일정 기간 입찰 참가가 제한되는 등 불이익을 받을 수 있습니다. "
            "본 공고문과 설계서·내역서·시방서 및 관계 규정을 충분히 숙지한 후 견적·입찰에 참가하시기 바랍니다.\n\n"
            "전자입찰 이용 및 참가자격등록: 조달청 나라장터 콜센터(1588-0800)"
        ),
        integrity_text=(
            "본 계약은 「지방자치단체를 당사자로 하는 계약에 관한 법률」 제6조의2에 따라 청렴서약제가 적용됩니다. "
            "견적·입찰 참가자는 청렴계약 조건을 숙지하고 승낙하여야 하며, 계약상대자는 전자계약 체결 시 "
            "청렴계약 이행서약서 등 발주기관이 요구하는 서류를 제출하여야 합니다."
        ),
    )

    return [
        notice_doc,
        GeneratedDocument("scope", f"{data.work_name} 공사과업", scope),
        GeneratedDocument("conditions", f"{data.work_name} 공사 특수조건", conditions),
        GeneratedDocument("checklist", f"{data.work_name} 착공준공 체크리스트", checklist),
    ]
