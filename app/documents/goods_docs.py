"""학교 물품 제조·구매 공고문 및 계약문서 세트.

공고문은 계약경로별로 제목·보증금·낙찰문구를 달리 생성한다.
- 1인 견적: 견적요청서
- 2인 이상 견적: 소액수의 견적제출 안내공고
- 경쟁입찰: 물품 구매 입찰공고
"""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.goods import GoodsResult, GoodsRoute


@dataclass(slots=True)
class GoodsDocumentData:
    school_name: str
    item_name: str
    start_date: date | None
    delivery_date: date
    estimated_price: int
    base_amount: int | None = None
    budget_amount: int | None = None
    quantity_text: str = "[수량 입력 필요]"
    specification_text: str = "[규격 입력 필요]"
    delivery_place: str = "학교 지정장소"
    warranty_text: str = "[하자·A/S 조건 입력 필요]"
    inspection_text: str = "납품 후 규격·수량·품질 검사"
    notice_number: str = ""
    bid_start: str = "[입력 필요]"
    bid_end: str = "[입력 필요]"
    bid_open: str = "[입력 필요]"
    region_limit: str = ""
    detail_product_name: str = ""
    detail_product_code: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    joint_supply_allowed: bool = False
    rebid_allowed: bool = True


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def _value(value: str, fallback: str = "[입력 필요]") -> str:
    return value.strip() if value and value.strip() else fallback


def _notice_title(data: GoodsDocumentData, rule: GoodsResult) -> str:
    if rule.route_code == GoodsRoute.ONE_PERSON:
        return f"{data.item_name} 수의계약 견적요청서"
    if rule.route_code == GoodsRoute.TWO_PERSON:
        return f"{data.item_name} 소액수의 견적제출 안내공고"
    return f"{data.item_name} 물품 구매 입찰공고"


def _award_text(rule: GoodsResult) -> str:
    if rule.route_code == GoodsRoute.ONE_PERSON:
        return (
            "제출 견적의 적정성, 규격 충족 여부, 수의계약 배제사유 및 "
            "가격조사 결과를 확인하여 계약상대자를 결정한다."
        )
    if rule.route_code == GoodsRoute.TWO_PERSON:
        rate = (rule.minimum_quote_rate or 0) * 100
        return (
            f"예정가격 이하로서 예정가격 대비 견적가격이 {rate:g}% 이상인 자 중 "
            "최저가격 제출자부터 순서대로 수의계약 배제사유에 해당하지 않는 자를 "
            "계약상대자로 결정한다."
        )
    return (
        "예정가격 이하 최저가격 제출자 순으로 공고에 명시한 낙찰자 결정기준을 적용한다. "
        "중소기업자간 경쟁제품인 경우 공고일 현재 유효한 계약이행능력심사 기준의 "
        "낙찰하한율·통과점수를 별도로 확인하여 적용한다."
    )


def build_goods_documents(data: GoodsDocumentData, rule: GoodsResult) -> list[GeneratedDocument]:
    title = _notice_title(data, rule)
    electronic = "국가종합전자조달시스템 등 지정정보처리장치" if rule.designated_system_required else "학교가 정한 방법"
    schedule = (
        f"- 견적·입찰 개시: {data.bid_start}\n"
        f"- 견적·입찰 마감: {data.bid_end}\n"
        f"- 개찰: {data.bid_open}\n"
        if rule.route_code != GoodsRoute.ONE_PERSON
        else "- 견적서 제출기한: [입력 필요]\n- 제출방법: 학교가 정한 방법"
    )
    qualification_lines = [
        "지방계약법 시행령 제13조 및 시행규칙 제14조에 따른 참가자격을 갖춘 자",
        "견적·입찰 마감일 전일까지 필요한 나라장터 입찰참가자격 등록을 완료한 자",
    ]
    if rule.route_code == GoodsRoute.TWO_PERSON:
        qualification_lines.append("소기업·소상공인 확인서 보유 여부 또는 법령상 예외 적용 여부 확인")
    if data.region_limit:
        qualification_lines.append(f"지역제한: {data.region_limit}")
    if data.detail_product_name or data.detail_product_code:
        qualification_lines.append(
            f"세부품명: {_value(data.detail_product_name, '세부품명 미입력')}"
            + (f" ({data.detail_product_code})" if data.detail_product_code else "")
        )
    if "확인 필요" in rule.direct_production_status:
        qualification_lines.append("해당 세부품명의 유효한 직접생산확인증명서 보유")
    if "중소기업자간 경쟁제품" in rule.sme_competition_status:
        qualification_lines.append("SMPP에서 중소기업자간 경쟁제품 및 확인서 유효성 확인")

    notice=f"""# {title}

- 공고번호: {_value(data.notice_number)}
- 발주기관: {data.school_name}

입찰·견적 참가자는 본 공고문, 규격서, 계약 특수조건, 지방계약 관계법령,
국가종합전자조달시스템 전자입찰특별유의서 등 관련 규정을 충분히 숙지한 후
참가하여야 하며, 미숙지에 따른 책임은 참가자에게 있습니다.

## 1. 구매에 부치는 사항
- 건명: {data.item_name}
- 규격·수량: {data.quantity_text}
- 예산금액: {_money(data.budget_amount)}
- 기초금액: {_money(data.base_amount)}
- 추정가격: {_money(data.estimated_price)}
- 납품기한: {data.delivery_date.isoformat()}
- 납품장소: {data.delivery_place}
- 계약형태: {'단가계약' if any('단가계약' in x for x in rule.checks) else '총액계약 또는 입력조건에 따름'}
- 공동수급: {'허용' if data.joint_supply_allowed else '불허'}

※ 면세사업자가 견적·입찰에 참여하는 경우에도 부가가치세를 포함한 금액으로
투찰하고, 계약상대자가 면세사업자인 경우 계약금액에서 부가가치세 상당액을
차감하여 계약금액을 결정합니다.

## 2. 계약방법 및 제출방식
- 계약방법: {rule.contract_method}
- 제출방법: {electronic}
- 최소 견적자 수: {rule.quote_count_min if rule.quote_count_min else '경쟁입찰 기준 확인'}
- 중소기업제품: {rule.sme_competition_status}
- 직접생산: {rule.direct_production_status}

## 3. 견적·입찰 일정
{schedule}

## 4. 참가자격
{chr(10).join(f'- {line}' for line in qualification_lines)}

## 5. 예정가격
- 예정가격을 작성하는 경우 기초금액의 ±3% 범위에서 서로 다른 복수예비가격 15개를 작성하고,
  견적·입찰 참가자가 각 2개씩 선택한 결과 다빈도순 4개 가격을 산술평균하여 예정가격으로 결정합니다.
- 지정정보처리장치의 예가작성 방식과 공고조건이 다른 경우 해당 시스템 설정을 우선 확인합니다.

## 6. 계약상대자·낙찰자 결정
- {_award_text(rule)}
- 동일가격 제출자가 2인 이상인 경우 관계법령과 전자조달 특별유의서에 따라 전자추첨 등으로 결정합니다.
- 선순위자가 참가자격 미달, 수의계약 배제사유 등에 해당하면 차순위자를 순서대로 확인합니다.
- 재입찰·재견적: {'허용할 수 있음(별도 개별통보 없이 시스템 확인)' if data.rebid_allowed else '허용하지 않음'}

## 7. 견적·입찰보증금
- {'1인·2인 이상 수의계약 견적제출이므로 입찰보증금 납부대상이 아닙니다.' if rule.route_code != GoodsRoute.COMPETITIVE else '경쟁입찰의 입찰보증금은 지방계약법 시행령 제37조 및 공고조건에 따릅니다.'}

## 8. 입찰·견적의 무효
- 지방계약법 시행령 제39조, 시행규칙 제42조 및 전자입찰특별유의서 등 관계규정에 따릅니다.
- 참가자격·직접생산·중소기업 확인 등 공고에서 요구한 자격을 충족하지 못한 경우 무효 또는 계약상대자 결정에서 제외될 수 있습니다.

## 9. 청렴계약 및 수의계약 체결 제한
- 참가자는 청렴서약 조건을 준수하여야 합니다.
- 수의계약인 경우 지방계약 수의계약 배제사유 및 공직자의 이해충돌 방지법상 수의계약 체결 제한 여부를 확인합니다.

## 10. 규격 및 납품
{data.specification_text}

- 계약상대자는 계약 규격과 수량을 정확히 납품해야 합니다.
- 납품 후 검사·검수를 실시하고 규격·수량·품질 미달 시 교환·보완을 요구할 수 있습니다.

## 11. 문의
- 담당자: {_value(data.contact_name)}
- 연락처: {_value(data.contact_phone)}

※ 본 공고문은 자동생성 초안입니다. 공고 게시 전 계약담당자가 최신 법령,
중소기업제품 지정정보, 조달분류번호, 실제 예가설정 및 기관 내부기준을 최종 확인해야 합니다.
"""

    spec=f"""# {data.item_name} 구매 규격서

- 품명: {data.item_name}
- 수량: {data.quantity_text}
- 납품장소: {data.delivery_place}
- 납품기한: {data.delivery_date.isoformat()}
- 세부품명: {_value(data.detail_product_name, '해당 시 입력')}{f' ({data.detail_product_code})' if data.detail_product_code else ''}

## 세부규격
{data.specification_text}

## 기본조건
- 신품 납품을 원칙으로 한다.
- 제조사·모델 지정이 필요한 경우 동등이상 허용 여부와 지정사유를 검토한다.
- 규격·품질이 계약조건에 미달하면 교환·보완한다.
"""

    conditions=f"""# {data.item_name} 구매계약 특수조건

## 제1조 납품
계약상대자는 납품기한까지 지정장소에 물품을 완전한 상태로 납품한다.

## 제2조 검사·검수
{data.inspection_text}

## 제3조 하자·보증
{data.warranty_text}

## 제4조 규격불일치
규격·수량·품질이 계약과 다른 경우 학교는 교환·보완을 요구할 수 있다.

## 제5조 비용
운송·설치·포장·회수 등 공고에서 별도 정하지 않은 통상 납품비용의 부담주체를 산출내역에서 명확히 한다.
"""

    checklist=f"""# {data.item_name} 검사·검수 체크리스트

- 계약 품명 일치
- 모델·규격 일치
- 수량 확인
- 외관·파손 확인
- 제조일자·유효기간 확인(해당 시)
- 인증·시험성적서 확인(해당 시)
- 설치·시운전 확인(해당 시)
- 납품사진
- 하자보증·A/S 서류
- 검수 완료일
"""

    return [
        GeneratedDocument("notice", title, notice),
        GeneratedDocument("spec", f"{data.item_name} 규격서", spec),
        GeneratedDocument("conditions", f"{data.item_name} 특수조건", conditions),
        GeneratedDocument("inspection", f"{data.item_name} 검사검수표", checklist),
    ]
