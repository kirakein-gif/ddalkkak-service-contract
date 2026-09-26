"""수학여행·숙박형 현장체험학습 위탁용역 문서세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.two_stage import TwoStageResult


@dataclass(slots=True)
class TravelDocumentData:
    school_name: str
    service_name: str
    destination: str
    start_date: date
    end_date: date
    student_count: int
    teacher_count: int
    estimated_price: int
    base_amount: int | None = None
    nights: int = 0
    meals: int = 0
    transport_type: str = "전세버스"
    lodging_required: bool = True
    insurance_required: bool = True
    proposal_submit_place: str = "학교 행정실"
    proposal_evaluation_datetime: str = "[입력 필요]"
    bid_open_datetime: str = "[입력 필요]"
    region_limit: str = ""
    itinerary_text: str = "[세부일정 입력 필요]"


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def build_travel_documents(
    data: TravelDocumentData,
    two_stage: TwoStageResult,
) -> list[GeneratedDocument]:
    people = data.student_count + data.teacher_count
    travel_license = (
        "국내 일정은 종합여행업·국내외여행업·국내여행업 중 과업범위에 맞는 여행업 등록을 확인한다."
        if data.destination and "해외" not in data.destination
        else "국외 일정은 종합여행업 또는 국내외여행업 등 과업범위에 맞는 여행업 등록을 확인한다."
    )

    notice = f"""# {data.service_name} 입찰공고

{data.school_name}

## 1. 입찰에 부치는 사항
- 용역명: {data.service_name}
- 여행기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 여행장소: {data.destination}
- 예정인원: 총 {people}명(학생 {data.student_count}명, 인솔교사 {data.teacher_count}명)
- 숙박: {data.nights}박
- 식사: {data.meals}식
- 이동수단: {data.transport_type}
- 추정가격: {_money(data.estimated_price)}
- 기초금액: {_money(data.base_amount)}

## 2. 입찰 및 낙찰방법
- {two_stage.contract_method}
- 근거: {two_stage.legal_basis}
- 제안서 적격기준: {two_stage.proposal_pass_score:g}점 이상(학교가 확정한 평가기준)
- 규격적격자에 한해 가격입찰서를 개찰한다.
- 가격개찰 후 예정가격 이하 최저가격 제출자 등 공고에서 정한 기준으로 낙찰자를 결정한다.

## 3. 참가자격
- 지방계약 관계 법령상 입찰참가자격을 갖춘 자
- {travel_license}
- 숙박·운송 등 일부 과업을 직접 수행하지 않는 경우 각 분야의 적법한 사업자와의 계약·확보 여부를 제안서에서 확인한다.
- 학교가 지역제한을 두는 경우 해당 제한기준을 충족해야 한다.
{f'- 지역제한: {data.region_limit}' if data.region_limit else ''}

## 4. 제안서 및 가격입찰
- 제안서 제출처: {data.proposal_submit_place}
- 제안서 평가: {data.proposal_evaluation_datetime}
- 가격입찰: 나라장터(G2B)
- 가격개찰: {data.bid_open_datetime}

## 5. 제안서 평가의 주요내용
- 최근 학생 체험학습·수학여행 수행실적
- 수행조직 및 인력
- 숙박시설의 안전성·편의성
- 식사 품질 및 위생관리
- 교통수단 및 운행 안전계획
- 여행 일정의 교육성·적정성
- 안전사고·응급환자·기상악화 등 비상대응
- 여행자보험 등 안전보장

※ 세부 배점은 학교가 제안요청서에서 확정한다.

## 6. 유의사항
- 참가인원 증감에 따른 정산방식을 특수조건에 명확히 정한다.
- 항공·선박·숙박·차량·입장료 등 취소수수료 부담기준을 사전에 정한다.
- 최종 공고 전 관광진흥법령, 지방계약법령 및 교육청 현장체험학습 안전지침을 확인한다.
"""

    scope = f"""# {data.service_name} 과업설명서

## 1. 목적
학생의 교육과정과 연계한 안전하고 교육적인 현장체험학습을 운영한다.

## 2. 기본조건
- 학교: {data.school_name}
- 장소: {data.destination}
- 기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 인원: 학생 {data.student_count}명, 교직원 {data.teacher_count}명
- 숙박: {data.nights}박
- 식사: {data.meals}식
- 이동: {data.transport_type}

## 3. 세부일정
{data.itinerary_text}

## 4. 숙박
- 숙박시설의 등록·영업신고 등 적법성을 확인한다.
- 학생 안전, 객실배치, 비상대피로, 소방시설, 야간안전관리 계획을 제시한다.
- 학교가 요구하는 객실당 배정인원과 학생·교직원 동선 분리조건을 준수한다.

## 5. 식사
- 식단, 식사장소, 위생관리, 식중독 예방대책을 제시한다.
- 알레르기 등 학생별 식이 제한에 대응할 수 있어야 한다.

## 6. 교통
- 관계법령에 적합한 차량·항공·선박 등을 확보한다.
- 차량 운행 시 운전자 자격, 차량보험, 차령·검사 등 안전사항을 확인한다.
- 운송수단 변경 시 학교의 사전 승인을 받는다.

## 7. 안전관리
- 여행 전·중·후 안전관리계획을 수립한다.
- 응급환자 발생, 교통사고, 숙박시설 사고, 감염병, 기상악화 등 비상상황 대응체계를 둔다.
- 비상연락망과 인솔지원체계를 학교에 제출한다.
- 여행자보험: {'가입' if data.insurance_required else '학교 조건에 따라 검토'}

## 8. 정산
- 실제 참가인원 증감 시 공고·계약에서 정한 1인당 단가 또는 산출내역 기준으로 정산한다.
- 취소수수료는 원인·시점·실제 발생비용을 확인해 계약조건에 따라 처리한다.
"""

    special = f"""# {data.service_name} 계약 특수조건

## 제1조 계약범위
계약상대자는 숙박·식사·교통·프로그램·입장·보험 등 계약서와 과업설명서에서 정한 서비스를 종합적으로 제공한다.

## 제2조 인원변경
실제 참가인원은 학교사정으로 변동될 수 있으며 정산방법은 계약 산출내역에 따른다.

## 제3조 숙박 및 식사
계약상대자는 제안·승인된 숙박시설과 식사조건을 임의 변경할 수 없으며 불가피한 경우 학교의 사전승인을 받아야 한다.

## 제4조 안전
계약상대자는 여행 전 과정의 안전관리 책임체계를 갖추고 사고 발생 시 즉시 학교와 관계기관에 알린다.

## 제5조 교통
차량 등 운송수단은 관계법령과 계약조건을 충족해야 하며 무단 대체를 금한다.

## 제6조 취소 및 변경
천재지변, 감염병, 교육과정 변경 등 불가피한 사유로 일정이 변경·취소되는 경우 실제 발생한 비용과 관계규정에 따라 상호 협의한다.

## 제7조 개인정보
학생·보호자·교직원 개인정보는 본 용역 수행 목적에 한해 사용하고 종료 후 관계기준에 따라 파기한다.
"""

    evaluation = f"""# {data.service_name} 제안요청서·평가기준 초안

## 1. 평가원칙
- 제안서 총점: {two_stage.total_proposal_score:g}점
- 규격적격 기준: {two_stage.proposal_pass_score:g}점 이상
- 적격점수는 학교가 공고 전에 확정한다.
- 규격적격자에 한해 가격입찰을 개찰한다.

## 2. 평가영역 예시
- 객관적 평가: 수행실적, 경영상태, 수행인력
- 숙박시설: 위치, 객실, 편의시설, 대피·소방안전
- 식사: 식단, 품질, 위생, 식중독 예방
- 교통: 차량·운송수단 확보, 운전자·보험·안전관리
- 프로그램: 교육성, 일정의 적정성, 학생 참여도
- 안전관리: 비상대응, 의료기관 연계, 보험
- 기타 제안: 학교 요구사항 대응

## 3. 선정절차
{chr(10).join(f'- {step}' for step in two_stage.flow)}

※ 배점표는 학교의 여행형태·지역·숙박·교통조건에 따라 조정한다. 80점은 흔한 사례이나 법정 고정점수가 아니다.
"""

    itinerary = f"""# {data.service_name} 세부일정표

- 학교: {data.school_name}
- 장소: {data.destination}
- 기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 예정인원: {people}명

## 일정
{data.itinerary_text}

## 일정 작성 시 확인
- 출발·도착시간
- 이동시간과 휴게시간
- 식사시간
- 숙소 입·퇴실
- 체험장소 예약시간
- 우천·기상악화 대체일정
- 응급상황 시 인근 의료기관
"""

    return [
        GeneratedDocument("notice", f"{data.service_name} 입찰공고", notice),
        GeneratedDocument("scope", f"{data.service_name} 과업설명서", scope),
        GeneratedDocument("special", f"{data.service_name} 계약 특수조건", special),
        GeneratedDocument("evaluation", f"{data.service_name} 제안요청서", evaluation),
        GeneratedDocument("itinerary", f"{data.service_name} 세부일정표", itinerary),
    ]
