"""학교 물품 구매 문서세트."""

from dataclasses import dataclass
from datetime import date

from app.documents.formats import GeneratedDocument
from app.rules.goods import GoodsResult


@dataclass(slots=True)
class GoodsDocumentData:
    school_name: str
    item_name: str
    start_date: date | None
    delivery_date: date
    estimated_price: int
    base_amount: int | None = None
    quantity_text: str = "[수량 입력 필요]"
    specification_text: str = "[규격 입력 필요]"
    delivery_place: str = "학교 지정장소"
    warranty_text: str = "[하자·A/S 조건 입력 필요]"
    inspection_text: str = "납품 후 규격·수량·품질 검사"


def _money(v):
    return "[입력 필요]" if v is None else f"{v:,}원"


def build_goods_documents(data: GoodsDocumentData, rule: GoodsResult) -> list[GeneratedDocument]:
    notice=f"""# {data.item_name} 구매 공고·견적요청서

## 1. 구매개요
- 기관: {data.school_name}
- 품명: {data.item_name}
- 수량: {data.quantity_text}
- 추정가격: {_money(data.estimated_price)}
- 기초금액: {_money(data.base_amount)}
- 납품기한: {data.delivery_date.isoformat()}
- 납품장소: {data.delivery_place}

## 2. 계약방법
- {rule.contract_method}
- 견적자 수: {rule.quote_count_min if rule.quote_count_min else '별도 검토'}
- 견적·낙찰 기준: {f'{rule.minimum_quote_rate*100:.3f}%' if rule.minimum_quote_rate else '별도 확인'}
- 중소기업제품: {rule.sme_competition_status}
- 직접생산: {rule.direct_production_status}

## 3. 참가자격·확인사항
{chr(10).join(f'- {x}' for x in rule.checks)}

## 4. 규격
{data.specification_text}
"""

    spec=f"""# {data.item_name} 구매 규격서

- 품명: {data.item_name}
- 수량: {data.quantity_text}
- 납품장소: {data.delivery_place}
- 납품기한: {data.delivery_date.isoformat()}

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
        GeneratedDocument("notice", f"{data.item_name} 구매 공고", notice),
        GeneratedDocument("spec", f"{data.item_name} 규격서", spec),
        GeneratedDocument("conditions", f"{data.item_name} 특수조건", conditions),
        GeneratedDocument("inspection", f"{data.item_name} 검사검수표", checklist),
    ]
