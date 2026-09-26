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


def test_transport_qualification_api_passes_at_current_floor_with_full_ability() -> None:
    response = client.post(
        "/api/qualification/transport",
        json={
            "estimated_price": 150000000,
            "expected_price": 165000000,
            "bid_price": 148491750,
            "performance_base_amount": 150000000,
            "equivalent_performance_amount": 150000000,
            "similar_performance_amount": 0,
            "credit_rating": "A_MINUS_OR_BETTER",
            "safety_grade": "GRADE_1",
            "reputation_score": 0,
            "disqualification_reason": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["bid_rate_percent"] == 89.995
    assert body["price_score"] == 58.0
    assert body["ability_score_after_reputation"] == 30.0
    assert body["total_score"] == 88.0


def test_transport_qualification_api_rejects_500m_band() -> None:
    response = client.post(
        "/api/qualification/transport",
        json={
            "estimated_price": 500000000,
            "expected_price": 550000000,
            "bid_price": 500000000,
            "performance_base_amount": 500000000,
            "equivalent_performance_amount": 500000000,
            "credit_rating": "A_MINUS_OR_BETTER",
            "safety_grade": "GRADE_1",
        },
    )
    assert response.status_code == 422



def test_transport_hwpx_package_api_returns_zip_with_four_hwpx() -> None:
    response = client.post(
        "/api/documents/transport/package-hwpx",
        json=transport_payload(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert len(names) == 4
        assert all(name.endswith(".hwpx") for name in names)



def test_g2b_endpoint_requires_service_key(monkeypatch) -> None:
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    response = client.get("/api/g2b/service-notice/R26BK01234567")
    assert response.status_code == 503
    assert "DATA_GO_KR_SERVICE_KEY" in response.json()["detail"]



def test_travel_document_api_returns_five_documents_and_hwpx_zip() -> None:
    payload = {
        "school_name": "○○중학교",
        "service_name": "2027학년도 2학년 수학여행 위탁용역",
        "destination": "제주도",
        "start_date": "2027-05-10",
        "end_date": "2027-05-13",
        "student_count": 200,
        "teacher_count": 12,
        "estimated_price": 120000000,
        "base_amount": 132000000,
        "nights": 3,
        "meals": 7,
        "proposal_pass_score": 80,
        "itinerary_text": "1일차 학교→제주",
    }
    preview = client.post("/api/documents/travel/preview", json=payload)
    assert preview.status_code == 200
    assert len(preview.json()["documents"]) == 5
    package = client.post("/api/documents/travel/package-hwpx", json=payload)
    assert package.status_code == 200
    with ZipFile(BytesIO(package.content)) as archive:
        assert len(archive.namelist()) == 5
        assert all(name.endswith(".hwpx") for name in archive.namelist())


def test_program_document_api_returns_five_documents() -> None:
    payload = {
        "school_name": "○○초등학교",
        "service_name": "2027학년도 늘봄학교 프로그램 운영 용역",
        "start_date": "2027-03-01",
        "end_date": "2028-02-29",
        "estimated_price": 250000000,
        "expected_students": 180,
        "program_count": 12,
        "programs_text": "독서논술, 축구, 방송댄스",
        "operation_text": "학기중 방과후",
        "proposal_pass_score": 80,
    }
    response = client.post("/api/documents/program/preview", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["documents"]) == 5
    assert "강사" in body["documents"][1]["content"]


def test_facility_document_api_returns_five_documents() -> None:
    payload = {
        "school_name": "○○초등학교",
        "service_name": "2027년 소방시설 자체점검 용역",
        "facility_type": "소방시설",
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "estimated_price": 35000000,
        "statutory_inspection": True,
        "statutory_basis": "소방시설 설치 및 관리에 관한 법률 등",
        "required_license": "소방시설관리업 등 공고에서 정한 자격",
        "inspection_schedule": "상반기 1회, 하반기 1회",
    }
    response = client.post("/api/documents/facility/preview", json=payload)
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 5


def test_labor_document_api_marks_two_stage_as_not_allowed() -> None:
    payload = {
        "school_name": "○○중학교",
        "service_name": "2027년 교사동 청소용역",
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "estimated_price": 80000000,
        "worker_count": 2,
        "daily_hours": 8,
        "work_area": "교사동 및 공용부",
        "scope_text": "일상청소, 화장실, 복도, 계단",
    }
    response = client.post("/api/documents/labor/preview", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["rule"]["two_stage_allowed"] is False
    assert len(body["documents"]) == 5



def test_goods_document_api_and_hwpx_package() -> None:
    payload = {
        "school_name": "○○초등학교",
        "item_name": "복사용지 구매",
        "estimated_price": 30000000,
        "planned_date": "2026-09-26",
        "delivery_date": "2027-03-15",
        "quantity_text": "A4 80g 500박스",
        "specification_text": "백색도 및 평량은 규격서 참조",
        "delivery_place": "○○초 행정실",
        "is_sme_competition_product": False,
        "direct_production_applicable": False,
    }
    preview = client.post("/api/documents/goods/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["rule"]["route_code"] == "GOODS_TWO_PERSON"
    assert len(preview.json()["documents"]) == 4

    package = client.post("/api/documents/goods/package-hwpx", json=payload)
    assert package.status_code == 200
    with ZipFile(BytesIO(package.content)) as archive:
        assert len(archive.namelist()) == 4


def test_works_document_api_and_hwpx_package() -> None:
    payload = {
        "school_name": "○○초등학교",
        "work_name": "교실 바닥 교체공사",
        "estimated_price": 80000000,
        "works_type": "SPECIALIZED",
        "planned_date": "2026-09-26",
        "location": "본관 2층",
        "completion_days": 30,
        "scope_text": "기존 바닥 철거 및 신설",
        "required_industry": "실내건축공사업",
        "design_summary": "설계서 및 내역서 참조",
        "region_restriction_requested": True,
    }
    preview = client.post("/api/documents/works/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["rule"]["route_code"] == "WORKS_TWO_PERSON"
    assert preview.json()["rule"]["minimum_quote_rate"] == 0.89745
    assert len(preview.json()["documents"]) == 4

    package = client.post("/api/documents/works/package-hwpx", json=payload)
    assert package.status_code == 200
    with ZipFile(BytesIO(package.content)) as archive:
        assert len(archive.namelist()) == 4



def test_launcher_and_workspace_pages() -> None:
    launcher = client.get("/")
    workspace = client.get("/workspace?domain=service&type=transport")

    assert launcher.status_code == 200
    assert "딸깍 계약업무" in launcher.text
    assert "/workspace?domain=goods" in launcher.text

    assert workspace.status_code == 200
    assert "serviceDomain" in workspace.text
    assert "transportMode" in workspace.text
    assert "URLSearchParams" in workspace.text



def test_goods_category_profile_is_returned() -> None:
    payload = {
        "school_name": "○○중학교",
        "item_name": "2027학년도 학교급식 우유 구매",
        "goods_category": "MILK",
        "estimated_price": 30000000,
        "planned_date": "2026-09-26",
        "delivery_date": "2027-03-15",
    }
    response = client.post("/api/evaluate/goods", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["code"] == "MILK"
    assert body["profile"]["default_unit_price_contract"] is True
    assert any("단가계약" in item for item in body["checks"])


def test_works_school_type_recommends_industry() -> None:
    payload = {
        "school_name": "○○초등학교",
        "work_name": "교실 바닥 교체공사",
        "school_work_type": "INTERIOR",
        "estimated_price": 80000000,
        "planned_date": "2026-09-26",
        "location": "본관 2층",
        "completion_days": 30,
    }
    response = client.post("/api/documents/works/preview", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["recommended_industry"] == "실내건축공사업"
    assert body["profile"]["recommended_main_field"] == "실내건축공사"
    assert "실내건축공사업" in body["documents"][0]["content"]


def test_catalog_endpoints_return_school_types() -> None:
    works = client.get("/api/catalog/works")
    goods = client.get("/api/catalog/goods?planned_date=2026-09-26")
    assert works.status_code == 200
    assert goods.status_code == 200
    assert any(item["code"] == "ELECTRICAL" for item in works.json())
    assert any(item["code"] == "FOOD_INGREDIENTS" for item in goods.json())
