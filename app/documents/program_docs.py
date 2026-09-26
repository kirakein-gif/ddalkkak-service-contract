"""방과후·늘봄 프로그램 운영 위탁용역 문서세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.two_stage import TwoStageResult


@dataclass(slots=True)
class ProgramDocumentData:
    school_name: str
    service_name: str
    start_date: date
    end_date: date
    estimated_price: int
    base_amount: int | None = None
    expected_students: int = 0
    program_count: int = 0
    programs_text: str = "[프로그램 목록 입력 필요]"
    operation_text: str = "[운영요일·시간 입력 필요]"
    instructor_cost_included: bool = True
    material_cost_separate: bool = True
    actual_settlement: bool = True
    proposal_evaluation_datetime: str = "[입력 필요]"
    bid_open_datetime: str = "[입력 필요]"
    region_limit: str = ""


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def build_program_documents(
    data: ProgramDocumentData,
    two_stage: TwoStageResult,
) -> list[GeneratedDocument]:
    notice = f"""# {data.service_name} 입찰공고

{data.school_name}

## 1. 입찰에 부치는 사항
- 용역명: {data.service_name}
- 운영기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 예정 학생수: {data.expected_students if data.expected_students else '[입력 필요]'}명
- 프로그램 수: {data.program_count if data.program_count else '[입력 필요]'}개
- 추정가격: {_money(data.estimated_price)}
- 기초금액: {_money(data.base_amount)}

## 2. 입찰방법
- {two_stage.contract_method}
- 근거: {two_stage.legal_basis}
- 제안서 적격기준: {two_stage.proposal_pass_score:g}점 이상(학교 확정기준)
- 규격적격자에 한해 가격입찰 개찰
- 낙찰자는 공고에서 정한 예정가격 이하 최저가격 기준 등에 따라 결정

## 3. 제안서 평가
- 제안서 평가일: {data.proposal_evaluation_datetime}
- 가격개찰: {data.bid_open_datetime}
- 평가영역: 업체운영능력, 프로그램 구성, 강사 확보·관리, 학생·출결·안전관리, 학교와의 협력, 수강료·강사료·교재비 운영

## 4. 참가자격
- 지방계약 관계 법령상 입찰참가자격을 갖춘 업체
- 사업 수행에 필요한 인력·운영체계를 갖춘 업체
{f'- 지역제한: {data.region_limit}' if data.region_limit else ''}

## 5. 유의사항
- 프로그램별 강사료, 수용비, 교재·재료비의 부담주체를 명확히 한다.
- 실제 학생수·수강차시를 기준으로 정산하는 항목은 산출내역서에서 구분한다.
- 강사 채용·성범죄 및 아동학대 관련 조회 등 학생안전 절차를 학교 기준에 맞게 수행한다.
"""

    scope = f"""# {data.service_name} 과업내용서

## 1. 목적
학교의 방과후·늘봄 교육과정을 안정적으로 운영하고 학생에게 질 높은 프로그램을 제공한다.

## 2. 운영개요
- 학교: {data.school_name}
- 기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 예정 학생수: {data.expected_students if data.expected_students else '[입력 필요]'}명
- 프로그램 수: {data.program_count if data.program_count else '[입력 필요]'}개

## 3. 프로그램
{data.programs_text}

## 4. 운영시간
{data.operation_text}

## 5. 강사관리
- 프로그램별 자격·경력·전문성을 갖춘 강사를 확보한다.
- 강사 변경은 학교와 협의하고 필요한 확인서류를 제출한다.
- 성범죄·아동학대 관련 조회, 건강·안전 관련 학교 절차에 협조한다.
- 강사 결강 시 보강·대체강사 운영기준을 마련한다.

## 6. 학생관리
- 출결관리, 귀가관리, 학생안전, 학교폭력·사고 발생 대응체계를 둔다.
- 개인정보와 학생정보를 목적 외 사용하지 않는다.
- 특수교육대상학생 등 지원이 필요한 학생에 대한 운영방안을 학교와 협의한다.

## 7. 비용 및 정산
- 강사비 포함: {'예' if data.instructor_cost_included else '아니오/별도'}
- 교재·재료비 별도: {'예' if data.material_cost_separate else '아니오'}
- 실제 참여인원·수강차시 정산: {'적용' if data.actual_settlement else '미적용 또는 별도기준'}
- 학생수 변동 시 산출내역서와 계약조건에 따라 정산한다.

## 8. 학교 협력
- 프로그램 편성·시간표 변경 시 학교 승인을 받는다.
- 운영현황, 출결, 사고, 민원 등을 학교에 보고한다.
- 학교운영위원회·교육청 지침 등 필요한 내부절차에 협조한다.
"""

    rfp = f"""# {data.service_name} 제안요청서

## 1. 평가기준
- 제안서 총점: {two_stage.total_proposal_score:g}점
- 적격기준: {two_stage.proposal_pass_score:g}점 이상
- 적격업체에 한해 가격입찰서를 개찰한다.

## 2. 평가영역 예시
- 업체 일반현황 및 최근 유사사업 실적
- 사업 이해도와 운영계획
- 프로그램 구성의 교육성·다양성
- 강사 확보계획과 전문성
- 수업 품질관리·강사평가·대체강사 체계
- 학생 출결·귀가·안전관리
- 민원대응 및 학교와의 의사소통
- 교재·교구·재료 관리
- 수강료·강사료 등 원가구성의 적정성

## 3. 선정절차
{chr(10).join(f'- {step}' for step in two_stage.flow)}

※ 학교별 프로그램 성격에 따라 평가항목과 배점을 확정한다.
"""

    conditions = f"""# {data.service_name} 계약 특수조건

## 제1조 운영책임
계약상대자는 제안서와 과업내용서에 따라 프로그램을 성실하게 운영한다.

## 제2조 강사
계약상대자는 승인된 강사를 배치하며 변경 시 학교와 사전협의한다.

## 제3조 수업 및 출결
정해진 프로그램·차시를 준수하고 학생 출결 및 귀가상황을 관리한다.

## 제4조 안전
학생 안전사고 예방계획을 수립하고 사고 발생 시 즉시 학교에 보고한다.

## 제5조 비용
강사비·수용비·교재비·재료비·기타비용을 계약 산출내역에 따라 구분하고 임의로 추가징수하지 않는다.

## 제6조 정산
실제 수강인원·운영차시 등 변동항목은 계약에서 정한 정산기준에 따른다.

## 제7조 개인정보
학생·학부모·교직원의 개인정보를 계약목적 외 사용하지 않는다.

## 제8조 계약변경
학사일정·학생수·학교교육과정 변경 시 관계규정과 계약조건에 따라 운영내용을 조정할 수 있다.
"""

    cost = f"""# {data.service_name} 원가·정산항목표

## 기본정보
- 예정학생수: {data.expected_students if data.expected_students else '[입력 필요]'}명
- 프로그램수: {data.program_count if data.program_count else '[입력 필요]'}개

## 비용항목
- 강사 인건비
- 대체강사 비용
- 관리인력 인건비
- 4대보험 등 법정부담금(해당 시)
- 교재비
- 재료비
- 교구비
- 일반관리비
- 이윤
- 부가가치세
- 기타 직접경비

## 정산구분
- 고정비
- 학생수 연동비
- 수강차시 연동비
- 실비정산 항목

※ 입찰 전 학교가 비용부담 주체와 정산식을 확정한다.
"""

    notice_doc = GeneratedDocument(
        "notice",
        f"{data.service_name} 입찰공고",
        notice,
        layout="public_notice",
        issuer=data.school_name,
        issue_date=data.start_date.isoformat(),
        signatory=f"{data.school_name}장",
        summary_rows=(
            ("용 역 명", data.service_name, "운영기간", f"{data.start_date.isoformat()} ~ {data.end_date.isoformat()}"),
            ("예정학생수", f"{data.expected_students or '[입력 필요]'}명", "프로그램 수", f"{data.program_count or '[입력 필요]'}개"),
            ("기초금액", _money(data.base_amount), "추정가격", _money(data.estimated_price)),
        ),
        alert_text="제안요청서, 과업내용서, 계약 특수조건 및 관계 규정을 충분히 숙지한 후 입찰에 참가하시기 바랍니다. 전자입찰 이용 및 참가자격등록: 조달청 나라장터 콜센터(1588-0800)",
        integrity_text="본 계약은 지방계약 관계법령에 따른 청렴계약(서약)제가 적용됩니다. 제안서 평가기준과 계약조건은 학교가 공고 전에 확정해야 합니다.",
    )

    return [
        notice_doc,
        GeneratedDocument("scope", f"{data.service_name} 과업내용서", scope),
        GeneratedDocument("rfp", f"{data.service_name} 제안요청서", rfp),
        GeneratedDocument("conditions", f"{data.service_name} 계약 특수조건", conditions),
        GeneratedDocument("cost", f"{data.service_name} 원가·정산항목표", cost),
    ]
