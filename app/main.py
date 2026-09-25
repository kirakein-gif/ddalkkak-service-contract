from dataclasses import asdict
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="딸깍 용역계약",
    description="학교 용역 계약업무 지원 웹도구",
    version="0.3.0",
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ddalkkak-service-contract",
        "version": "0.3.0",
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
    result = evaluate_transport(
        TransportInput(
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
    )
    return jsonable_encoder(asdict(result))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
