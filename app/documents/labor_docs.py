"""학교 청소·방역 등 단순노무용역 문서세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.simple_labor import SimpleLaborResult


@dataclass(slots=True)
class LaborDocumentData:
    school_name: str
    service_name: str
    start_date: date
    end_date: date
    estimated_price: int
    base_amount: int | None = None
    worker_count: int = 0
    daily_hours: float = 0
    work_area: str = "[작업구역 입력 필요]"
    scope_text: str = "[세부 청소·방역 범위 입력 필요]"
    supplies_included: bool = True
    disinfection_license_required: bool = False
    required_license: str = ""


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def build_labor_documents(
    data: LaborDocumentData,
    rule: SimpleLaborResult,
) -> list[GeneratedDocument]:
    license_text = data.required_license or (
        "소독업 등 관계법령상 자격 확인"
        if data.disinfection_license_required
        else "별도 면허 없음 또는 과업별 확인"
    )

    notice=f"""# {data.service_name} 견적·입찰 공고 초안

## 1. 용역개요
- 학교: {data.school_name}
- 기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 작업구역: {data.work_area}
- 투입인원: {data.worker_count if data.worker_count else '[입력 필요]'}명
- 1일 근로시간: {data.daily_hours if data.daily_hours else '[입력 필요]'}시간
- 추정가격: {_money(data.estimated_price)}
- 기초금액: {_money(data.base_amount)}

## 2. 계약방법
- 추정가격에 따른 수의계약·경쟁입찰 분기는 공통 Rule Engine을 적용한다.
- 청소·경비 등 단순노무용역은 지방계약법 시행령 제18조 2단계 입찰 대상에서 제외한다.
- 협상에 의한 계약도 단순노무 제공 용역에는 적용하지 않는다.

## 3. 참가자격
- 지방계약 관계법령상 참가자격
- 과업상 필요한 면허·등록: {license_text}

## 4. 근로조건
- 최저임금, 4대보험, 퇴직급여 등 관계 노동관계법령 준수
- 산출내역의 인원·시간·노무비가 실제 과업조건과 일치하도록 작성
- 임금지급·근로자 보호 관련 발주기관 조건 준수
"""

    scope=f"""# {data.service_name} 과업지시서

## 1. 작업구역
{data.work_area}

## 2. 작업범위
{data.scope_text}

## 3. 인력
- 예정인원: {data.worker_count if data.worker_count else '[입력 필요]'}명
- 1일 근로시간: {data.daily_hours if data.daily_hours else '[입력 필요]'}시간
- 결원 발생 시 업무공백이 없도록 대체인력을 확보한다.

## 4. 작업관리
- 학교 수업·학생동선을 고려하여 작업시간을 조정한다.
- 화학제품·소독약품 사용 시 안전자료와 사용법을 준수한다.
- 청소도구·소모품 포함: {'계약상대자 부담' if data.supplies_included else '학교 제공 또는 별도조건'}
- 학교 비품·시설물 훼손 시 즉시 보고한다.

## 5. 안전
- 미끄럼·낙상·화학물질·전기·고소작업 등 위험요인을 관리한다.
- 학생이 있는 시간대에는 작업구역을 안전하게 통제한다.

## 6. 방역·소독
- 법정 자격 필요 여부: {'확인 필요' if data.disinfection_license_required else '과업에 따라 확인'}
- 요구자격: {license_text}
"""

    conditions=f"""# {data.service_name} 계약 특수조건

## 제1조 인력배치
계약상대자는 계약조건에서 정한 인원과 근로시간을 준수한다.

## 제2조 임금 및 법정부담
관계 노동관계법령에 따른 임금·보험·퇴직급여 등을 준수하고 발주기관이 정한 확인절차에 협조한다.

## 제3조 결원
결원·휴가 등으로 과업에 공백이 발생하지 않도록 대체인력을 투입한다.

## 제4조 안전
산업안전 및 학생안전을 위한 작업수칙을 준수한다.

## 제5조 품질
학교가 과업수행상태를 확인해 미흡사항을 요구하면 정당한 범위에서 즉시 보완한다.

## 제6조 개인정보 및 보안
교실·행정실 등에서 알게 된 학생·교직원 정보와 학교 내부정보를 외부에 누설하지 않는다.
"""

    cost=f"""# {data.service_name} 원가계산 입력표

## 노무비
- 인원: {data.worker_count if data.worker_count else '[입력 필요]'}명
- 근로시간: {data.daily_hours if data.daily_hours else '[입력 필요]'}시간
- 기본급
- 주휴·연차 등 관계법령상 수당
- 퇴직급여충당
- 국민연금
- 건강보험
- 장기요양보험
- 고용보험
- 산재보험

## 경비
- 청소·방역 소모품
- 피복비
- 안전용품
- 장비비
- 기타 직접경비

## 기타
- 일반관리비
- 이윤
- 부가가치세

※ 실제 원가계산은 계약 예정연도의 임금·보험료율·법정기준을 사용한다.
"""

    checklist=f"""# {data.service_name} 계약·월별 확인 체크리스트

- 계약인원 배치 여부
- 출근·근로시간 확인
- 결원 대체 여부
- 임금 지급 확인(발주기관 지침상 필요한 범위)
- 4대보험 가입·납부 관련 확인(해당 시)
- 작업품질 확인
- 안전사고·민원 발생 여부
- 소독업 등 면허 유지 여부(해당 시)
- 소모품·약품 안전관리
"""

    notice_doc = GeneratedDocument(
        "notice",
        f"{data.service_name} 공고",
        notice,
        layout="public_notice",
        issuer=data.school_name,
        issue_date=data.start_date.isoformat(),
        signatory=f"{data.school_name}장",
        summary_rows=(
            ("용 역 명", data.service_name, "작업구역", data.work_area),
            ("용역기간", f"{data.start_date.isoformat()} ~ {data.end_date.isoformat()}", "투입인원", f"{data.worker_count or '[입력 필요]'}명"),
            ("기초금액", _money(data.base_amount), "추정가격", _money(data.estimated_price)),
        ),
        alert_text="과업지시서, 근로조건, 원가계산 기준 및 관계 규정을 충분히 숙지한 후 견적·입찰에 참가하시기 바랍니다.",
        integrity_text="본 계약은 지방계약 관계법령에 따른 청렴계약(서약)제가 적용됩니다. 최저임금·4대보험·퇴직급여 등 노무비 기준은 계약 예정연도의 현행 기준을 적용해야 합니다.",
    )

    return [
        notice_doc,
        GeneratedDocument("scope", f"{data.service_name} 과업지시서", scope),
        GeneratedDocument("conditions", f"{data.service_name} 특수조건", conditions),
        GeneratedDocument("cost", f"{data.service_name} 원가계산표", cost),
        GeneratedDocument("checklist", f"{data.service_name} 이행확인 체크리스트", checklist),
    ]
