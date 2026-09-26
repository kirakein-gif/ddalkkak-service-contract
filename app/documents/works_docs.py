"""학교 시설공사 기본 문서세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.works import WorksResult


@dataclass(slots=True)
class WorksDocumentData:
    school_name: str
    work_name: str
    location: str
    start_date: date | None
    completion_days: int
    estimated_price: int
    base_amount: int | None = None
    scope_text: str = "[공사범위 입력 필요]"
    required_industry: str = ""
    design_summary: str = "[설계·내역 요약 입력 필요]"
    safety_text: str = "산업안전보건법 등 관계법령에 따른 안전조치"


def _money(v):
    return "[입력 필요]" if v is None else f"{v:,}원"


def build_works_documents(data: WorksDocumentData, rule: WorksResult) -> list[GeneratedDocument]:
    notice=f"""# {data.work_name} 공사 공고·견적제출 안내

## 1. 공사개요
- 기관: {data.school_name}
- 공사명: {data.work_name}
- 위치: {data.location}
- 공사기간: 착공일부터 {data.completion_days}일
- 추정가격: {_money(data.estimated_price)}
- 기초금액: {_money(data.base_amount)}

## 2. 계약방법
- {rule.contract_method}
- 견적·낙찰 기준: {f'{rule.minimum_quote_rate*100:.3f}%' if rule.minimum_quote_rate else '적격심사 등 별도 확인'}
- 해당 공사 수의계약 금액상한: {_money(rule.small_value_limit)}

## 3. 참가자격
- 관계 공사업법에 따른 등록업체
- 요구 업종·분야: {data.required_industry or '[입력 필요]'}
- 공고에서 정한 지역제한·기술자·실적 조건을 충족한 업체

## 4. 확인사항
{chr(10).join(f'- {x}' for x in rule.checks)}
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

    start_docs=f"""# {data.work_name} 착공·준공 서류 체크리스트

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
        GeneratedDocument("notice", f"{data.work_name} 공고", notice),
        GeneratedDocument("scope", f"{data.work_name} 공사과업", scope),
        GeneratedDocument("conditions", f"{data.work_name} 공사 특수조건", conditions),
        GeneratedDocument("checklist", f"{data.work_name} 착공준공 체크리스트", start_docs),
    ]
