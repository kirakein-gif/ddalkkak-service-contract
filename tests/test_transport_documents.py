from datetime import date
from io import BytesIO
from zipfile import ZipFile

from docx import Document
from hwpx import HwpxDocument

from app.documents.transport_docs import (
    RouteEntry,
    TransportDocumentData,
    build_transport_documents,
    build_transport_docx_zip,
    build_transport_hwpx_zip,
)
from app.rules.transport import (
    PassengerGroup,
    PricingMethod,
    TransportInput,
    TransportServiceItem,
    evaluate_transport,
)


def build_sample():
    transport = TransportInput(
        service_name="2027학년도 ○○초등학교 통학차량 임차용역",
        estimated_price=45_000_000,
        planned_date=date(2026, 9, 26),
        passenger_group=PassengerGroup.ELEMENTARY,
        vehicle_count=1,
        seat_capacity_min=45,
        service_item=TransportServiceItem.SCHOOL_TRANSPORT,
        pricing_method=PricingMethod.TOTAL,
        operation_days=190,
        driver_included=True,
        attendant_included=True,
        regional_restriction_requested=True,
    )
    rule = evaluate_transport(transport)
    data = TransportDocumentData(
        school_name="○○초등학교",
        service_name=transport.service_name,
        estimated_price=transport.estimated_price,
        vehicle_count=transport.vehicle_count,
        seat_capacity_min=transport.seat_capacity_min,
        planned_date=transport.planned_date,
        base_amount=49_500_000,
        budget_amount=50_000_000,
        contract_start=date(2027, 3, 1),
        contract_end=date(2028, 2, 29),
        operation_days=190,
        school_address="충청남도 ○○시 ○○로 1",
        contact_name="계약담당자",
        contact_phone="041-000-0000",
        region_restriction_text="충청남도",
        vehicle_year_condition="2022년 이후 출고 차량",
        direct_vehicle_required=True,
        pricing_method_label="총액",
        service_item_name=rule.service_item_name,
        service_item_code=rule.service_item_code,
        driver_included=True,
        attendant_included=True,
        routes=[
            RouteEntry(
                route_name="1호차",
                direction="등교",
                departure="○○마을",
                via="△△아파트",
                destination="○○초등학교",
                departure_time="07:40",
            )
        ],
    )
    return rule, data


def test_builds_four_transport_documents() -> None:
    rule, data = build_sample()
    documents = build_transport_documents(data, rule)

    assert len(documents) == 4
    keys = [doc.key for doc in documents]
    assert keys == ["notice", "scope", "special_conditions", "routes"]
    assert "○○초등학교" in documents[0].content
    assert "직접생산확인증명서" in documents[0].content
    assert "○○마을" in documents[3].content


def test_builds_zip_with_four_openable_docx_files() -> None:
    rule, data = build_sample()
    documents = build_transport_documents(data, rule)
    payload = build_transport_docx_zip(documents)

    with ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()
        assert len(names) == 4
        assert all(name.endswith(".docx") for name in names)

        first_doc = Document(BytesIO(archive.read(names[0])))
        text = "\n".join(p.text for p in first_doc.paragraphs)
        assert "통학차량" in text
        assert "○○초등학교" in text



def test_builds_zip_with_four_openable_hwpx_files() -> None:
    rule, data = build_sample()
    documents = build_transport_documents(data, rule)
    payload = build_transport_hwpx_zip(documents)

    with ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()
        assert len(names) == 4
        assert all(name.endswith(".hwpx") for name in names)

        raw = archive.read(names[0])
        with HwpxDocument.open(BytesIO(raw)) as hwpx:
            assert len(hwpx.sections) >= 1



def test_transport_notice_reflects_current_and_editable_procurement_terms() -> None:
    transport = TransportInput(
        service_name="2027학년도 통학차량 임차용역",
        estimated_price=150_000_000,
        planned_date=date(2026, 9, 26),
        passenger_group=PassengerGroup.ELEMENTARY,
        vehicle_count=2,
        seat_capacity_min=45,
        service_item=TransportServiceItem.SCHOOL_TRANSPORT,
        pricing_method=PricingMethod.TOTAL,
        operation_days=190,
        driver_included=True,
        attendant_included=True,
        regional_restriction_requested=True,
    )
    rule = evaluate_transport(transport)
    data = TransportDocumentData(
        school_name="○○초등학교",
        service_name=transport.service_name,
        estimated_price=transport.estimated_price,
        vehicle_count=2,
        seat_capacity_min=45,
        planned_date=transport.planned_date,
        base_amount=165_000_000,
        operation_days=190,
        region_restriction_text="충청남도",
        vehicle_year_condition="2019년 이후 출고 차량",
        direct_vehicle_required=True,
        joint_supply_allowed=False,
        qualification_document_deadline_text="적격심사 대상 통보 후 5일 이내",
        contract_deadline_text="낙찰통보 후 10일 이내",
        social_insurance_settlement_text="원가계산서 계상 사회보험료를 관련 규정에 따라 사후정산",
        pricing_method_label="총액",
        service_item_name=rule.service_item_name,
        service_item_code=rule.service_item_code,
    )
    notice = build_transport_documents(data, rule)[0].content

    assert "89.995%" in notice
    assert "88점 이상" in notice
    assert "복수예비가격 15개" in notice
    assert "4개 가격을 산술평균" in notice
    assert "종합평점" in notice
    assert "5일 이내" in notice
    assert "10일 이내" in notice
    assert "2019년 이후" in notice
    assert "공동수급: 불허" in notice
    assert "사후정산" in notice


def test_transport_small_value_and_unit_price_keep_distinct_terms() -> None:
    rule, data = build_sample()
    data.pricing_method_label = "단가"
    data.equal_price_method = ""
    notice = build_transport_documents(data, rule)[0].content
    assert "단가계약" in notice
    assert "실제 운행일수" in notice
    assert "자동추첨" in notice
