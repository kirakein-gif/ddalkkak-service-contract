"""학교 물품 제조·구매 공고문 및 계약문서 세트."""

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
    notice_date: date | None = None
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
    category_label: str = "일반 물품"
    purchase_method_hint: str = ""
    category_checks: tuple[str, ...] = ()


def _money(value: int | None) -> str:
    return "[입력 필요]" if value is None else f"{value:,}원"


def _value(value: str, fallback: str = "[입력 필요]") -> str:
    return value.strip() if value and value.strip() else fallback


def _notice_title(data: GoodsDocumentData, rule: GoodsResult) -> str:
    if rule.route_code == GoodsRoute.ONE_PERSON:
        return f"{data.item_name} 수의계약 견적요청서"
    if rule.route_code == GoodsRoute.TWO_PERSON:
        return f"{data.item_name} 소액수의 전자견적 제출 안내공고"
    return f"{data.item_name} 물품 구매 전자입찰 공고"


def _award_text(rule: GoodsResult) -> str:
    if rule.route_code == GoodsRoute.ONE_PERSON:
        return "제출견적의 적정성, 규격 충족 여부, 수의계약 배제사유 및 가격조사 결과를 확인하여 계약상대자를 결정합니다."
    if rule.route_code == GoodsRoute.TWO_PERSON:
        rate = (rule.minimum_quote_rate or 0) * 100
        return (
            f"예정가격 이하로서 예정가격 대비 견적가격이 {rate:g}% 이상인 자 중 최저가격 제출자부터 순서대로 "
            "수의계약 배제사유에 해당하지 않는 자를 계약상대자로 결정합니다."
        )
    return (
        "예정가격 이하 최저가격 제출자 순으로 공고에 명시한 낙찰자 결정기준을 적용합니다. "
        "중소기업자간 경쟁제품은 공고일 현재 유효한 계약이행능력심사 기준을 별도로 확인하여 적용합니다."
    )


def build_goods_documents(data: GoodsDocumentData, rule: GoodsResult) -> list[GeneratedDocument]:
    title = _notice_title(data, rule)
    electronic = "국가종합전자조달시스템(G2B) 전자제출" if rule.route_code != GoodsRoute.ONE_PERSON else "학교가 정한 견적제출 방법"
    schedule = (
        f"- 견적·입찰 개시: {data.bid_start}\n- 견적·입찰 마감: {data.bid_end}\n- 개찰일시 및 장소: {data.bid_open} / 발주기관 입찰집행관 PC"
        if rule.route_code != GoodsRoute.ONE_PERSON
        else "- 견적서 제출기한: [입력 필요]\n- 제출방법: 학교가 정한 방법"
    )

    qualification_lines = [
        "지방계약법 시행령 제13조 및 시행규칙 제14조에 따른 참가자격을 갖춘 자",
        "전자견적·입찰인 경우 제출마감일 전일까지 나라장터 입찰참가자격 등록을 완료한 자",
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
        qualification_lines.append("중소기업공공구매 종합정보망(SMPP)에서 관련 확인서의 유효성을 확인할 수 있어야 함")

    submission = electronic_submission_lines("견적서" if rule.route_code != GoodsRoute.COMPETITIVE else "입찰서")
    prices = preliminary_price_lines()
    contract_lines = electronic_contract_lines(
        small_value=rule.route_code != GoodsRoute.COMPETITIVE
    )
    bond = (
        "수의계약 견적제출이므로 입찰보증금 납부대상이 아닙니다."
        if rule.route_code != GoodsRoute.COMPETITIVE
        else "입찰보증금은 지방계약법 시행령 제37조 및 공고조건에 따르며, 전자입찰서의 납부확약으로 갈음하는 경우 해당 전자서식에 따릅니다."
    )

    notice=f"""# {title}

- 공고번호: {_value(data.notice_number)}
- 발주기관: {data.school_name}

본 공고문, 규격서, 물품구매계약 일반조건·특수조건, 지방자치단체 입찰 및 계약 집행기준, {G2B_SPECIAL_NOTICE} 등 입찰·계약에 필요한 모든 사항을 숙지한 후 참가하여야 하며, 이를 숙지하지 못한 책임은 참가자에게 있습니다.

## 1. 견적·입찰에 부치는 사항
- 건명: {data.item_name}
- 품목 및 규격: {data.quantity_text}
- 예산금액: {_money(data.budget_amount)}
- 기초금액: {_money(data.base_amount)}
- 추정가격: {_money(data.estimated_price)}
- 납품기한: {data.delivery_date.isoformat()}
- 납품장소: {data.delivery_place}
- 계약형태: {'단가계약' if any('단가계약' in x for x in rule.checks) else '총액계약'}
- 공동수급: {'허용' if data.joint_supply_allowed else '불허'}

※ 면세사업자도 부가가치세를 포함한 금액으로 투찰하며, 계약상대자가 면세사업자인 경우 계약금액에서 부가가치세 상당액을 차감하여 계약금액을 결정합니다.

## 2. 견적제출 및 계약방식
- 물품유형: {data.category_label}
- 유형별 구매검토: {data.purchase_method_hint or '일반 물품계약'}
- 계약방법: {rule.contract_method}
- 제출방법: {electronic}
- {'전자계약, 청렴계약제 시행 대상입니다.' if rule.route_code != GoodsRoute.ONE_PERSON else '계약 체결 시 청렴계약 관련 서류를 확인합니다.'}
- 최소 견적자 수: {rule.quote_count_min if rule.quote_count_min else '경쟁입찰 기준 확인'}
- 중소기업제품: {rule.sme_competition_status}
- 직접생산: {rule.direct_production_status}

## 3. 견적·입찰 및 개찰 일정
{schedule}

## 4. 참가자격
{chr(10).join(f'- {line}' for line in qualification_lines)}

## 5. 참가신청 및 전자견적·입찰서 제출 유의사항
{chr(10).join(f'- {line}' for line in submission)}

## 6. 예정가격
{chr(10).join(f'- {line}' for line in prices)}
- 지정정보처리장치의 예가작성 방식과 공고조건이 다른 경우 실제 나라장터 공고 설정을 우선 확인합니다.

## 7. 계약상대자·낙찰자 결정
- {_award_text(rule)}
- {equal_price_lottery_line()}
- 선순위자가 참가자격 미달 또는 수의계약 배제사유 등에 해당하면 차순위자 순으로 확인합니다.
- 재입찰·재견적: {'허용할 수 있으며 별도의 개별통보 없이 나라장터 개찰결과와 재입찰 일정을 확인' if data.rebid_allowed else '허용하지 않음'}

## 8. 입찰보증금 및 견적·입찰의 무효
- {bond}
- 지방계약법 시행령 제39조, 시행규칙 제42조 및 국가종합전자조달시스템 전자입찰특별유의서 등 관계규정에 따른 무효사유에 해당하는 견적·입찰은 무효입니다.
- 공고에서 요구한 참가자격·직접생산·중소기업 확인 등 자격을 충족하지 못한 경우 계약상대자·낙찰자 결정에서 제외될 수 있습니다.

## 9. 전자계약 체결
{chr(10).join(f'- {line}' for line in contract_lines)}

## 10. 청렴계약 및 수의계약 체결 제한
- 참가자는 청렴계약 조건을 숙지·준수하여야 하며, 전자견적·입찰서 제출로 청렴계약 이행서약서를 제출한 것으로 간주하는 경우 기관 기준에 따릅니다.
- 수의계약은 수의계약 배제사유와 공직자의 이해충돌 방지법상 수의계약 체결 제한 여부를 확인합니다.

## 11. 규격·납품 및 검사검수
- {data.specification_text}
- 계약상대자는 계약 규격과 수량을 정확히 납품해야 합니다.
- 납품 후 검사·검수를 실시하며 규격·수량·품질 미달 시 교환·보완을 요구할 수 있습니다.
- 하자·A/S 조건: {data.warranty_text}

## 12. 품목유형별 추가 확인사항
{chr(10).join(f'- {item}' for item in data.category_checks) if data.category_checks else '- 별도 추가 확인사항 없음'}

## 13. 기타사항 및 문의
- 공고문과 개찰결과는 국가종합전자조달시스템에서 확인합니다.
- 전자입찰 시스템 문의: 정부조달 콜센터 1588-0800
- 계약담당자: {_value(data.contact_name)}
- 연락처: {_value(data.contact_phone)}
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
- 신품 납품을 원칙으로 합니다.
- 제조사·모델 지정이 필요한 경우 동등이상 허용 여부와 지정사유를 검토합니다.
- 규격·품질이 계약조건에 미달하면 교환·보완합니다.
"""

    conditions=f"""# {data.item_name} 구매계약 특수조건

## 제1조 납품
계약상대자는 납품기한까지 지정장소에 물품을 완전한 상태로 납품합니다.

## 제2조 검사·검수
{data.inspection_text}

## 제3조 하자·보증
{data.warranty_text}

## 제4조 규격불일치
규격·수량·품질이 계약과 다른 경우 학교는 교환·보완을 요구할 수 있습니다.

## 제5조 비용
운송·설치·포장·회수 등 공고에서 별도 정하지 않은 통상 납품비용의 부담주체를 산출내역에서 명확히 합니다.
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

    summary = (
        ("건 명", data.item_name, "", ""),
        ("물품유형", data.category_label, "구매검토", data.purchase_method_hint or "일반 물품계약"),
        ("기초금액", _money(data.base_amount), "추정가격", _money(data.estimated_price)),
        ("규격·수량", data.quantity_text, "납품기한", data.delivery_date.isoformat()),
        ("전자견적서 제출기간", f"{data.bid_start} ~ {data.bid_end}" if rule.route_code != GoodsRoute.ONE_PERSON else "[입력 필요]", "", ""),
        ("개찰일시 및 장소", f"{data.bid_open} / 발주기관 입찰집행관 PC" if rule.route_code != GoodsRoute.ONE_PERSON else "해당 없음", "", ""),
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
            "본 공고문과 규격서·특수조건 및 관계 규정을 충분히 숙지한 후 견적·입찰에 참가하시기 바랍니다.\n\n"
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
        GeneratedDocument("spec", f"{data.item_name} 규격서", spec),
        GeneratedDocument("conditions", f"{data.item_name} 특수조건", conditions),
        GeneratedDocument("inspection", f"{data.item_name} 검사검수표", checklist),
    ]
