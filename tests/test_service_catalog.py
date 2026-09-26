from app.main import ServiceEvaluateRequest, evaluate_service_contract, get_service_catalog
from app.rules.engine import RouteCode
from app.rules.service_catalog import SchoolServiceType, get_service_profile

def test_service_catalog_keeps_transport_below_service_hierarchy():
    transport = get_service_profile(SchoolServiceType.TRANSPORT)
    travel = get_service_profile(SchoolServiceType.TRAVEL)
    assert transport.group_label == "용역"
    assert transport.label == "통학차량·통학버스"
    assert travel.document_route == "travel"

def test_service_catalog_api_exposes_school_service_types():
    codes = {item["code"] for item in get_service_catalog()}
    assert {"TRANSPORT", "TRAVEL", "AFTER_SCHOOL", "STATUTORY_INSPECTION", "DISINFECTION"} <= codes

def test_service_evaluation_adds_profile_checks_and_preserves_two_stage_review():
    body = evaluate_service_contract(
        ServiceEvaluateRequest(
            service_name="2027학년도 수학여행 위탁용역",
            estimated_price=120_000_000,
            planned_date="2026-09-26",
            service_category="TRAVEL",
        )
    )
    assert body["route_code"] == RouteCode.TWO_STAGE_REVIEW
    assert body["profile"]["label"] == "수학여행·현장체험학습"
    assert any("여행업 등록" in item for item in body["required_checks"])
