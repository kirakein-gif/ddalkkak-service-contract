"""학교 시설 유지관리·법정점검 용역 문서세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument


@dataclass(slots=True)
class FacilityDocumentData:
    school_name: str
    service_name: str
    facility_type: str
    start_date: date
    end_date: date
    estimated_price: int
    base_amount: int | None = None
    notice_date: date | None = None
    statutory_inspection: bool = False
    statutory_basis: str = ""
    required_license: str = ""
    inspection_schedule: str = "[점검일정 입력 필요]"
    scope_text: str = "[점검·유지관리 범위 입력 필요]"
    report_text: str = "점검결과보고서 및 관계법령상 제출자료"
    emergency_response: bool = True


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def build_facility_documents(data: FacilityDocumentData) -> list[GeneratedDocument]:
    qualification = data.required_license or "[관계법령상 필요한 등록·면허·자격 확인 필요]"
    basis = data.statutory_basis or "[해당 시설 관계법령 확인 필요]"

    notice=f"""# {data.service_name} 견적·입찰 공고 초안

## 1. 용역개요
- 학교: {data.school_name}
- 시설분야: {data.facility_type}
- 기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 추정가격: {_money(data.estimated_price)}
- 기초금액: {_money(data.base_amount)}
- 법정점검 여부: {'예' if data.statutory_inspection else '아니오/일반 유지관리'}

## 2. 참가자격
- 지방계약 관계법령상 참가자격을 갖춘 업체
- 요구 면허·등록·자격: {qualification}
- 법정점검인 경우 점검기관·기술인력·장비 등 관계법령의 등록기준 충족

## 3. 계약방법
- 추정가격에 따른 1인 견적, 2인 이상 견적, 경쟁입찰 여부는 공통 Rule Engine으로 결정한다.
- 기술용역·PQ 대상에 해당하는 경우 일반 유지관리용역과 분리해 별도 심사한다.

## 4. 확인사항
- 적용 법령: {basis}
- 점검주기와 법정기한
- 기술인력 보유·배치기준
- 측정·점검 장비
- 보험 및 손해배상
- 점검결과 보고·관계기관 제출
"""

    scope=f"""# {data.service_name} 과업지시서

## 1. 목적
{data.school_name}의 {data.facility_type} 시설을 안전하고 정상적으로 유지하고 관계법령상 필요한 점검·보고업무를 수행한다.

## 2. 과업기간
{data.start_date.isoformat()} ~ {data.end_date.isoformat()}

## 3. 과업범위
{data.scope_text}

## 4. 점검일정
{data.inspection_schedule}

## 5. 법정기준
- 법정점검 여부: {'적용' if data.statutory_inspection else '해당 시 적용'}
- 적용법령·기준: {basis}
- 계약상대자는 법정 점검주기·방법·기술기준을 준수한다.

## 6. 인력 및 자격
- 요구자격: {qualification}
- 법령 또는 공고에서 정한 기술인력을 실제 과업에 배치한다.
- 담당 기술인력 변경 시 학교에 알리고 자격증빙을 제출한다.

## 7. 결과보고
- {data.report_text}
- 점검결과 이상사항은 중요도·위험도와 조치방안을 구분해 보고한다.
- 법정 제출기한이 있는 경우 기한 내 관계기관 제출을 지원하거나 완료한다.

## 8. 긴급조치
- 긴급대응: {'계약범위에 포함' if data.emergency_response else '별도 조건'}
- 중대한 안전위험 발견 시 즉시 학교에 알리고 필요한 응급조치를 제안한다.
"""

    conditions=f"""# {data.service_name} 계약 특수조건

## 제1조 자격유지
계약상대자는 계약기간 동안 공고에서 요구한 면허·등록·기술인력 요건을 유지한다.

## 제2조 점검품질
점검을 형식적으로 수행해서는 안 되며 측정값·점검사진·결과자료 등 확인 가능한 근거를 남긴다.

## 제3조 보고
중대한 결함·위험요인을 발견하면 정기보고일까지 기다리지 않고 즉시 학교에 통보한다.

## 제4조 법정기한
법정점검 용역은 관계법령상 점검·보고·제출기한을 준수한다.

## 제5조 손해배상
계약상대자의 귀책으로 발생한 손해에 대해서는 관계법령과 계약조건에 따른 책임을 부담한다.

## 제6조 재위탁
법령 또는 공고조건에 위반되는 임의 재위탁을 금한다.
"""

    checklist=f"""# {data.service_name} 계약 전 자격·서류 체크리스트

- 사업자등록
- 관련 업종 등록·면허: {qualification}
- 기술인력 자격증 및 재직증빙
- 법정 장비 보유증빙(해당 시)
- 보험가입증명
- 최근 점검·유지관리 실적(공고에서 요구한 경우)
- 직접생산 또는 중소기업 관련 증빙(해당 시)
- 청렴계약·수의계약 배제사유 관련 서류
- 이해충돌방지법상 수의계약 체결 제한 확인
"""

    schedule=f"""# {data.service_name} 연간 점검·보고 일정표

- 계약기간: {data.start_date.isoformat()} ~ {data.end_date.isoformat()}
- 시설: {data.facility_type}

## 예정일정
{data.inspection_schedule}

## 각 점검 후
- 점검결과 확인
- 결함사항 및 조치 필요사항 분류
- 결과보고서 수령
- 법정 제출 여부 확인
- 보수 필요사항 별도 계약 여부 검토
"""

    notice_doc = GeneratedDocument(
        "notice",
        f"{data.service_name} 공고",
        notice,
        layout="public_notice",
        issuer=data.school_name,
        issue_date=data.notice_date.isoformat() if data.notice_date else "",
        signatory=f"{data.school_name}장",
        summary_rows=(
            ("용 역 명", data.service_name, "시설분야", data.facility_type),
            ("용역기간", f"{data.start_date.isoformat()} ~ {data.end_date.isoformat()}", "법정점검", "적용" if data.statutory_inspection else "해당 시 확인"),
            ("기초금액", _money(data.base_amount), "추정가격", _money(data.estimated_price)),
        ),
        alert_text="과업지시서, 점검일정, 관계법령상 자격요건 및 계약 특수조건을 충분히 숙지한 후 견적·입찰에 참가하시기 바랍니다.",
        integrity_text="본 계약은 지방계약 관계법령에 따른 청렴계약(서약)제가 적용됩니다. 법정점검의 시설별 등록·인력·보고기한은 공고 전에 담당자가 최종 확인해야 합니다.",
    )

    return [
        notice_doc,
        GeneratedDocument("scope", f"{data.service_name} 과업지시서", scope),
        GeneratedDocument("conditions", f"{data.service_name} 특수조건", conditions),
        GeneratedDocument("checklist", f"{data.service_name} 자격서류 체크리스트", checklist),
        GeneratedDocument("schedule", f"{data.service_name} 점검일정표", schedule),
    ]
