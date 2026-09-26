from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def transport_payload() -> dict:
    return {
        "service_name": "2027학년도 ○○초등학교 통학차량 임차용역",
        "estimated_price": 45000000,
        "planned_date": "2026-09-26",
        "passenger_group": "ELEMENTARY",
        "vehicle_count": 1,
        "seat_capacity_min": 45,
        "service_item": "SCHOOL_TRANSPORT",
        "pricing_method": "TOTAL",
        "operation_days": 190,
        "driver_included": True,
        "attendant_included": True,
        "regional_restriction_requested": True,
        "school_name": "○○초등학교",
        "school_address": "충청남도 ○○시 ○○로 1",
        "contact_name": "계약담당자",
        "contact_phone": "041-000-0000",
        "base_amount": 49500000,
        "budget_amount": 50000000,
        "contract_start": "2027-03-01",
        "contract_end": "2028-02-29",
        "region_restriction_text": "충청남도",
        "vehicle_year_condition": "2022년 이후 출고 차량",
        "direct_vehicle_required": True,
        "routes": [
            {
                "route_name": "1호차",
                "direction": "등교",
                "departure": "○○마을",
                "via": "△△아파트",
                "destination": "○○초등학교",
                "departure_time": "07:40",
                "notes": "",
            }
        ],
    }


def test_transport_preview_api_returns_four_documents() -> None:
    response = client.post("/api/documents/transport/preview", json=transport_payload())
    assert response.status_code == 200
    body = response.json()

    assert body["rule"]["route_code"] == "TRANSPORT_SMALL_VALUE"
    assert len(body["documents"]) == 4
    assert body["documents"][0]["key"] == "notice"
    assert "○○초등학교" in body["documents"][0]["content"]


def test_transport_package_api_returns_zip_with_four_docx() -> None:
    response = client.post("/api/documents/transport/package", json=transport_payload())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert len(names) == 4
        assert all(name.endswith(".docx") for name in names)
