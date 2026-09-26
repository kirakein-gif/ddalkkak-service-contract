from dataclasses import asdict
from datetime import date
import os
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import httpx

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.documents.formats import build_hwpx_zip
from app.documents.facility_docs import FacilityDocumentData, build_facility_documents
from app.documents.labor_docs import LaborDocumentData, build_labor_documents
from app.documents.program_docs import ProgramDocumentData, build_program_documents
from app.documents.travel_docs import TravelDocumentData, build_travel_documents
from app.documents.transport_docs import (
    RouteEntry,
    TransportDocumentData,
    build_transport_documents,
    build_transport_docx_zip,
    build_transport_hwpx_zip,
)
from app.rules.simple_labor import evaluate_simple_labor
from app.rules.two_stage import TwoStageInput, TwoStageMethod, evaluate_two_stage
from app.rules.engine import (
    ContractInput,
    VendorCategory,
    evaluate_contract,
)
from app.rules.transport import (
    PassengerGroup,
    PricingMethod,
    TransportInput,
    TransportServiceItem,
    evaluate_transport,
)
from app.services.g2b import G2BAPIError, G2BClient, G2BClientConfig
from app.rules.transport_qualification import (
    CreditRating,
    QualificationInput,
    SafetyGrade,
    calculate_transport_qualification,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="딸깍 용역계약",
    description="학교 용역 계약업무 지원 웹도구",
    version="0.7.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class EvaluateRequest(BaseModel):
    service_name: str = Field(min_length=1, max_length=200)
    estimated_price: int = Field(gt=0)
    planned_date: date = date(2026, 7, 1)
    vendor_category: VendorCategory = VendorCategory.NONE
    special_entity_requirements_confirmed: bool = False
    special_knowledge_or_qualification: bool = False
    technical_service: bool = False
    requires_proposal_evaluation: bool = False


class TransportEvaluateRequest(BaseModel):
    service_name: str = Field(min_length=1, max_length=200)
    estimated_price: int = Field(gt=0)
    planned_date: date = date(2026, 9, 25)
    passenger_group: PassengerGroup
    vehicle_count: int = Field(gt=0, le=100)
    seat_capacity_min: int = Field(gt=0, le=100)
    service_item: TransportServiceItem = TransportServiceItem.SCHOOL_TRANSPORT
    pricing_method: PricingMethod = PricingMethod.TOTAL
    operation_days: int | None = Field(default=None, gt=0, le=366)
    driver_included: bool = True
    attendant_included: bool = False
    regional_restriction_requested: bool = True


class TransportQualificationRequest(BaseModel):
    estimated_price: int = Field(gt=0, lt=500_000_000)
    planned_date: date = date(2026, 7, 27)
    expected_price: int = Field(gt=0)
    bid_price: int = Field(gt=0)
    performance_base_amount: int = Field(gt=0)
    equivalent_performance_amount: int = Field(default=0, ge=0)
    similar_performance_amount: int = Field(default=0, ge=0)
    credit_rating: CreditRating = CreditRating.A_MINUS_OR_BETTER
    safety_grade: SafetyGrade = SafetyGrade.GRADE_1
    reputation_score: Decimal = Field(default=Decimal("0"), ge=Decimal("-5"), le=Decimal("4.25"))
    disqualification_reason: bool = False



class TravelDocumentRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=100)
    service_name: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    student_count: int = Field(ge=0, le=5000)
    teacher_count: int = Field(ge=0, le=500)
    estimated_price: int = Field(gt=0)
    base_amount: int | None = Field(default=None, gt=0)
    nights: int = Field(default=0, ge=0, le=30)
    meals: int = Field(default=0, ge=0, le=100)
    transport_type: str = Field(default="전세버스", max_length=100)
    lodging_required: bool = True
    insurance_required: bool = True
    proposal_pass_score: float = Field(default=80, gt=0, le=100)
    proposal_submit_place: str = Field(default="학교 행정실", max_length=200)
    proposal_evaluation_datetime: str = Field(default="[입력 필요]", max_length=100)
    bid_open_datetime: str = Field(default="[입력 필요]", max_length=100)
    region_limit: str = Field(default="", max_length=200)
    itinerary_text: str = Field(default="[세부일정 입력 필요]", max_length=10000)


class ProgramDocumentRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=100)
    service_name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    estimated_price: int = Field(gt=0)
    base_amount: int | None = Field(default=None, gt=0)
    expected_students: int = Field(default=0, ge=0, le=10000)
    program_count: int = Field(default=0, ge=0, le=500)
    programs_text: str = Field(default="[프로그램 목록 입력 필요]", max_length=10000)
    operation_text: str = Field(default="[운영요일·시간 입력 필요]", max_length=10000)
    instructor_cost_included: bool = True
    material_cost_separate: bool = True
    actual_settlement: bool = True
    proposal_pass_score: float = Field(default=80, gt=0, le=100)
    proposal_evaluation_datetime: str = Field(default="[입력 필요]", max_length=100)
    bid_open_datetime: str = Field(default="[입력 필요]", max_length=100)
    region_limit: str = Field(default="", max_length=200)


class FacilityDocumentRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=100)
    service_name: str = Field(min_length=1, max_length=200)
    facility_type: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    estimated_price: int = Field(gt=0)
    base_amount: int | None = Field(default=None, gt=0)
    statutory_inspection: bool = False
    statutory_basis: str = Field(default="", max_length=1000)
    required_license: str = Field(default="", max_length=1000)
    inspection_schedule: str = Field(default="[점검일정 입력 필요]", max_length=5000)
    scope_text: str = Field(default="[점검·유지관리 범위 입력 필요]", max_length=10000)
    report_text: str = Field(default="점검결과보고서 및 관계법령상 제출자료", max_length=3000)
    emergency_response: bool = True


class LaborDocumentRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=100)
    service_name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    estimated_price: int = Field(gt=0)
    base_amount: int | None = Field(default=None, gt=0)
    worker_count: int = Field(default=0, ge=0, le=1000)
    daily_hours: float = Field(default=0, ge=0, le=24)
    work_area: str = Field(default="[작업구역 입력 필요]", max_length=5000)
    scope_text: str = Field(default="[세부 청소·방역 범위 입력 필요]", max_length=10000)
    supplies_included: bool = True
    disinfection_license_required: bool = False
    required_license: str = Field(default="", max_length=1000)


class RouteRequest(BaseModel):
    route_name: str = Field(min_length=1, max_length=100)
    direction: str = Field(default="등교", max_length=30)
    departure: str = Field(default="", max_length=200)
    via: str = Field(default="", max_length=500)
    destination: str = Field(default="", max_length=200)
    departure_time: str = Field(default="", max_length=50)
    notes: str = Field(default="", max_length=500)


class TransportDocumentRequest(TransportEvaluateRequest):
    school_name: str = Field(default="○○학교", min_length=1, max_length=100)
    school_address: str = Field(default="", max_length=300)
    contact_name: str = Field(default="", max_length=100)
    contact_phone: str = Field(default="", max_length=50)
    notice_number: str = Field(default="", max_length=100)
    base_amount: int | None = Field(default=None, gt=0)
    budget_amount: int | None = Field(default=None, gt=0)
    contract_start: date | None = None
    contract_end: date | None = None
    region_restriction_text: str = Field(default="", max_length=200)
    bid_start: str = Field(default="", max_length=100)
    bid_end: str = Field(default="", max_length=100)
    bid_open: str = Field(default="", max_length=100)
    vehicle_year_condition: str = Field(default="", max_length=300)
    direct_vehicle_required: bool = False
    extra_notes: str = Field(default="", max_length=1000)
    routes: list[RouteRequest] = Field(default_factory=list, max_length=50)


def _to_transport_input(request: TransportEvaluateRequest) -> TransportInput:
    return TransportInput(
        service_name=request.service_name,
        estimated_price=request.estimated_price,
        planned_date=request.planned_date,
        passenger_group=request.passenger_group,
        vehicle_count=request.vehicle_count,
        seat_capacity_min=request.seat_capacity_min,
        service_item=request.service_item,
        pricing_method=request.pricing_method,
        operation_days=request.operation_days,
        driver_included=request.driver_included,
        attendant_included=request.attendant_included,
        regional_restriction_requested=request.regional_restriction_requested,
    )


def _build_document_data(request: TransportDocumentRequest, rule) -> TransportDocumentData:
    pricing_label = "단가" if request.pricing_method == PricingMethod.UNIT else "총액"
    return TransportDocumentData(
        school_name=request.school_name,
        service_name=request.service_name,
        estimated_price=request.estimated_price,
        vehicle_count=request.vehicle_count,
        seat_capacity_min=request.seat_capacity_min,
        planned_date=request.planned_date,
        base_amount=request.base_amount,
        budget_amount=request.budget_amount,
        contract_start=request.contract_start,
        contract_end=request.contract_end,
        operation_days=request.operation_days,
        school_address=request.school_address,
        contact_name=request.contact_name,
        contact_phone=request.contact_phone,
        notice_number=request.notice_number,
        region_restriction_text=request.region_restriction_text,
        bid_start=request.bid_start,
        bid_end=request.bid_end,
        bid_open=request.bid_open,
        vehicle_year_condition=request.vehicle_year_condition,
        direct_vehicle_required=request.direct_vehicle_required,
        pricing_method_label=pricing_label,
        service_item_name=rule.service_item_name,
        service_item_code=rule.service_item_code,
        driver_included=request.driver_included,
        attendant_included=request.attendant_included,
        routes=[
            RouteEntry(
                route_name=item.route_name,
                direction=item.direction,
                departure=item.departure,
                via=item.via,
                destination=item.destination,
                departure_time=item.departure_time,
                notes=item.notes,
            )
            for item in request.routes
        ],
        extra_notes=request.extra_notes,
    )



def _hwpx_response(documents, filename: str) -> StreamingResponse:
    payload = build_hwpx_zip(documents)
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _documents_preview(documents) -> dict:
    return {
        "documents": [
            {"key": item.key, "title": item.title, "content": item.content}
            for item in documents
        ]
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ddalkkak-service-contract",
        "version": "0.7.0",
    }


@app.get("/api/g2b/service-notice/{bid_notice_no}")
async def get_g2b_service_notice(bid_notice_no: str) -> dict:
    service_key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not service_key:
        raise HTTPException(
            status_code=503,
            detail="공공데이터포털 인증키(DATA_GO_KR_SERVICE_KEY)가 설정되지 않았습니다.",
        )
    config = G2BClientConfig(
        service_key=service_key,
        base_url=os.getenv(
            "DATA_GO_KR_BASE_URL",
            "https://apis.data.go.kr/1230000/ad/BidPublicInfoService",
        ),
    )
    try:
        return await G2BClient(config).get_service_case(bid_notice_no.strip())
    except (G2BAPIError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/evaluate")
def evaluate(request: EvaluateRequest) -> dict:
    result = evaluate_contract(
        ContractInput(
            service_name=request.service_name,
            estimated_price=request.estimated_price,
            planned_date=request.planned_date,
            vendor_category=request.vendor_category,
            special_entity_requirements_confirmed=request.special_entity_requirements_confirmed,
            special_knowledge_or_qualification=request.special_knowledge_or_qualification,
            technical_service=request.technical_service,
            requires_proposal_evaluation=request.requires_proposal_evaluation,
        )
    )
    return jsonable_encoder(asdict(result))


@app.post("/api/evaluate/transport")
def evaluate_school_transport(request: TransportEvaluateRequest) -> dict:
    result = evaluate_transport(_to_transport_input(request))
    return jsonable_encoder(asdict(result))


@app.post("/api/qualification/transport")
def calculate_school_transport_qualification(
    request: TransportQualificationRequest,
) -> dict:
    result = calculate_transport_qualification(
        QualificationInput(
            estimated_price=request.estimated_price,
            planned_date=request.planned_date,
            expected_price=request.expected_price,
            bid_price=request.bid_price,
            performance_base_amount=request.performance_base_amount,
            equivalent_performance_amount=request.equivalent_performance_amount,
            similar_performance_amount=request.similar_performance_amount,
            credit_rating=request.credit_rating,
            safety_grade=request.safety_grade,
            reputation_score=request.reputation_score,
            disqualification_reason=request.disqualification_reason,
        )
    )
    return jsonable_encoder(asdict(result))



@app.post("/api/documents/travel/preview")
def preview_travel_documents(request: TravelDocumentRequest) -> dict:
    rule = evaluate_two_stage(
        TwoStageInput(
            service_name=request.service_name,
            method=TwoStageMethod.SIMULTANEOUS,
            proposal_pass_score=request.proposal_pass_score,
        )
    )
    documents = build_travel_documents(
        TravelDocumentData(
            school_name=request.school_name,
            service_name=request.service_name,
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            student_count=request.student_count,
            teacher_count=request.teacher_count,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            nights=request.nights,
            meals=request.meals,
            transport_type=request.transport_type,
            lodging_required=request.lodging_required,
            insurance_required=request.insurance_required,
            proposal_submit_place=request.proposal_submit_place,
            proposal_evaluation_datetime=request.proposal_evaluation_datetime,
            bid_open_datetime=request.bid_open_datetime,
            region_limit=request.region_limit,
            itinerary_text=request.itinerary_text,
        ),
        rule,
    )
    result = _documents_preview(documents)
    result["rule"] = jsonable_encoder(asdict(rule))
    return result


@app.post("/api/documents/travel/package-hwpx")
def package_travel_documents(request: TravelDocumentRequest) -> StreamingResponse:
    rule = evaluate_two_stage(
        TwoStageInput(
            service_name=request.service_name,
            method=TwoStageMethod.SIMULTANEOUS,
            proposal_pass_score=request.proposal_pass_score,
        )
    )
    documents = build_travel_documents(
        TravelDocumentData(
            school_name=request.school_name,
            service_name=request.service_name,
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            student_count=request.student_count,
            teacher_count=request.teacher_count,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            nights=request.nights,
            meals=request.meals,
            transport_type=request.transport_type,
            lodging_required=request.lodging_required,
            insurance_required=request.insurance_required,
            proposal_submit_place=request.proposal_submit_place,
            proposal_evaluation_datetime=request.proposal_evaluation_datetime,
            bid_open_datetime=request.bid_open_datetime,
            region_limit=request.region_limit,
            itinerary_text=request.itinerary_text,
        ),
        rule,
    )
    return _hwpx_response(documents, "ddalkkak_travel_hwpx.zip")


@app.post("/api/documents/program/preview")
def preview_program_documents(request: ProgramDocumentRequest) -> dict:
    rule = evaluate_two_stage(
        TwoStageInput(
            service_name=request.service_name,
            method=TwoStageMethod.SIMULTANEOUS,
            proposal_pass_score=request.proposal_pass_score,
        )
    )
    documents = build_program_documents(
        ProgramDocumentData(
            school_name=request.school_name,
            service_name=request.service_name,
            start_date=request.start_date,
            end_date=request.end_date,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            expected_students=request.expected_students,
            program_count=request.program_count,
            programs_text=request.programs_text,
            operation_text=request.operation_text,
            instructor_cost_included=request.instructor_cost_included,
            material_cost_separate=request.material_cost_separate,
            actual_settlement=request.actual_settlement,
            proposal_evaluation_datetime=request.proposal_evaluation_datetime,
            bid_open_datetime=request.bid_open_datetime,
            region_limit=request.region_limit,
        ),
        rule,
    )
    result = _documents_preview(documents)
    result["rule"] = jsonable_encoder(asdict(rule))
    return result


@app.post("/api/documents/program/package-hwpx")
def package_program_documents(request: ProgramDocumentRequest) -> StreamingResponse:
    rule = evaluate_two_stage(
        TwoStageInput(
            service_name=request.service_name,
            method=TwoStageMethod.SIMULTANEOUS,
            proposal_pass_score=request.proposal_pass_score,
        )
    )
    documents = build_program_documents(
        ProgramDocumentData(
            school_name=request.school_name,
            service_name=request.service_name,
            start_date=request.start_date,
            end_date=request.end_date,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            expected_students=request.expected_students,
            program_count=request.program_count,
            programs_text=request.programs_text,
            operation_text=request.operation_text,
            instructor_cost_included=request.instructor_cost_included,
            material_cost_separate=request.material_cost_separate,
            actual_settlement=request.actual_settlement,
            proposal_evaluation_datetime=request.proposal_evaluation_datetime,
            bid_open_datetime=request.bid_open_datetime,
            region_limit=request.region_limit,
        ),
        rule,
    )
    return _hwpx_response(documents, "ddalkkak_program_hwpx.zip")


@app.post("/api/documents/facility/preview")
def preview_facility_documents(request: FacilityDocumentRequest) -> dict:
    documents = build_facility_documents(FacilityDocumentData(**request.model_dump()))
    return _documents_preview(documents)


@app.post("/api/documents/facility/package-hwpx")
def package_facility_documents(request: FacilityDocumentRequest) -> StreamingResponse:
    documents = build_facility_documents(FacilityDocumentData(**request.model_dump()))
    return _hwpx_response(documents, "ddalkkak_facility_hwpx.zip")


@app.post("/api/documents/labor/preview")
def preview_labor_documents(request: LaborDocumentRequest) -> dict:
    rule = evaluate_simple_labor()
    documents = build_labor_documents(LaborDocumentData(**request.model_dump()), rule)
    result = _documents_preview(documents)
    result["rule"] = jsonable_encoder(asdict(rule))
    return result


@app.post("/api/documents/labor/package-hwpx")
def package_labor_documents(request: LaborDocumentRequest) -> StreamingResponse:
    rule = evaluate_simple_labor()
    documents = build_labor_documents(LaborDocumentData(**request.model_dump()), rule)
    return _hwpx_response(documents, "ddalkkak_labor_hwpx.zip")


@app.post("/api/documents/transport/preview")
def preview_transport_documents(request: TransportDocumentRequest) -> dict:
    rule = evaluate_transport(_to_transport_input(request))
    data = _build_document_data(request, rule)
    documents = build_transport_documents(data, rule)
    return {
        "rule": jsonable_encoder(asdict(rule)),
        "documents": [
            {"key": doc.key, "title": doc.title, "content": doc.content}
            for doc in documents
        ],
    }


@app.post("/api/documents/transport/package-hwpx")
def package_transport_hwpx_documents(
    request: TransportDocumentRequest,
) -> StreamingResponse:
    rule = evaluate_transport(_to_transport_input(request))
    data = _build_document_data(request, rule)
    documents = build_transport_documents(data, rule)
    payload = build_transport_hwpx_zip(documents)
    headers = {
        "Content-Disposition": 'attachment; filename="ddalkkak_transport_hwpx.zip"'
    }
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/zip",
        headers=headers,
    )


@app.post("/api/documents/transport/package")
def package_transport_documents(request: TransportDocumentRequest) -> StreamingResponse:
    rule = evaluate_transport(_to_transport_input(request))
    data = _build_document_data(request, rule)
    documents = build_transport_documents(data, rule)
    payload = build_transport_docx_zip(documents)
    headers = {
        "Content-Disposition": 'attachment; filename="ddalkkak_transport_documents.zip"'
    }
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/zip",
        headers=headers,
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
