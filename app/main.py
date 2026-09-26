from dataclasses import asdict
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.documents.transport_docs import (
    RouteEntry,
    TransportDocumentData,
    build_transport_documents,
    build_transport_docx_zip,
)
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
    version="0.5.0",
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
    expected_price: int = Field(gt=0)
    bid_price: int = Field(gt=0)
    performance_base_amount: int = Field(gt=0)
    equivalent_performance_amount: int = Field(default=0, ge=0)
    similar_performance_amount: int = Field(default=0, ge=0)
    credit_rating: CreditRating = CreditRating.A_MINUS_OR_BETTER
    safety_grade: SafetyGrade = SafetyGrade.GRADE_1
    reputation_score: Decimal = Field(default=Decimal("0"), ge=Decimal("-5"), le=Decimal("4.25"))
    disqualification_reason: bool = False


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ddalkkak-service-contract",
        "version": "0.5.0",
    }


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
