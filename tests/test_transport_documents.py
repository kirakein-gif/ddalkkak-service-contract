from datetime import date
from io import BytesIO
from zipfile import ZipFile

from docx import Document

from app.documents.transport_docs import (
    RouteEntry,
    TransportDocumentData,
    build_transport_documents,
    build_transport_docx_zip,
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
