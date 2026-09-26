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
from app.documents.goods_docs import GoodsDocumentData, build_goods_documents
from app.documents.works_docs import WorksDocumentData, build_works_documents
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
from app.rules.goods import GoodsInput, evaluate_goods
from app.rules.goods_catalog import GoodsCategory, get_goods_profile, list_goods_profiles
from app.rules.works import WorksInput, WorksType, evaluate_works
from app.rules.works_catalog import SchoolWorkType, get_works_profile, list_works_profiles
from app.rules.service_catalog import (
    SchoolServiceType,
    get_service_profile,
    list_service_profiles,
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
    title="딸깍 계약업무",
    description="학교 공사·용역·물품 계약업무 지원 웹도구",
    version="0.15.0",
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


class ServiceEvaluateRequest(EvaluateRequest):
    """용역 세부유형을 먼저 받아 공통 Rule Engine에 연결하는 요청."""

    service_category: SchoolServiceType = SchoolServiceType.GENERAL


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




class GoodsRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=100)
    item_name: str = Field(min_length=1, max_length=200)
    goods_category: GoodsCategory = GoodsCategory.GENERAL_OFFICE
    estimated_price: int = Field(gt=0)
    planned_date: date = date(2026, 7, 1)
    base_amount: int | None = Field(default=None, gt=0)
    budget_amount: int | None = Field(default=None, gt=0)
    delivery_date: date
    quantity_text: str = Field(default="[수량 입력 필요]", max_length=5000)
    specification_text: str = Field(default="[규격 입력 필요]", max_length=10000)
    delivery_place: str = Field(default="학교 지정장소", max_length=1000)
    warranty_text: str = Field(default="[하자·A/S 조건 입력 필요]", max_length=3000)
    inspection_text: str = Field(default="납품 후 규격·수량·품질 검사", max_length=3000)
    notice_number: str = Field(default="", max_length=100)
    bid_start: str = Field(default="[입력 필요]", max_length=100)
    bid_end: str = Field(default="[입력 필요]", max_length=100)
    bid_open: str = Field(default="[입력 필요]", max_length=100)
    region_limit: str = Field(default="", max_length=200)
    detail_product_name: str = Field(default="", max_length=300)
    detail_product_code: str = Field(default="", max_length=30)
    contact_name: str = Field(default="", max_length=100)
    contact_phone: str = Field(default="", max_length=50)
    joint_supply_allowed: bool = False
    rebid_allowed: bool = True
    is_sme_competition_product: bool = False
    direct_production_applicable: bool = False
    is_publication: bool = False
    unit_price_contract: bool = False


class WorksRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=100)
    work_name: str = Field(min_length=1, max_length=200)
    school_work_type: SchoolWorkType = SchoolWorkType.OTHER
    estimated_price: int = Field(gt=0)
    works_type: WorksType = WorksType.SPECIALIZED
    planned_date: date = date(2026, 7, 1)
    base_amount: int | None = Field(default=None, gt=0)
    budget_amount: int | None = Field(default=None, gt=0)
    location: str = Field(default="[공사위치 입력 필요]", max_length=1000)
    completion_days: int = Field(default=30, gt=0, le=3650)
    scope_text: str = Field(default="[공사범위 입력 필요]", max_length=10000)
    required_industry: str = Field(default="", max_length=1000)
    design_summary: str = Field(default="[설계·내역 요약 입력 필요]", max_length=10000)
    safety_text: str = Field(default="산업안전보건법 등 관계법령에 따른 안전조치", max_length=3000)
    notice_number: str = Field(default="", max_length=100)
    bid_start: str = Field(default="[입력 필요]", max_length=100)
    bid_end: str = Field(default="[입력 필요]", max_length=100)
    bid_open: str = Field(default="[입력 필요]", max_length=100)
    region_limit: str = Field(default="", max_length=200)
    contact_name: str = Field(default="", max_length=100)
    contact_phone: str = Field(default="", max_length=50)
    a_value_total: int | None = Field(default=None, ge=0)
    insurance_breakdown_text: str = Field(default="[국민연금·건강보험·퇴직공제·산업안전보건관리비 등 세부금액 입력 필요]", max_length=5000)
    site_explanation: str = Field(default="별도의 현장설명은 생략하고 설계서·내역서 열람으로 갈음", max_length=1000)
    joint_supply_allowed: bool = False
    rebid_allowed: bool = True
    region_restriction_requested: bool = True


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
    notice_date: date | None = None
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
    notice_date: date | None = None
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
    notice_date: date | None = None
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
    notice_date: date | None = None
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
        "version": "0.15.0",
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




def _append_unique(target: list[str], values) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def _goods_rule_and_profile(request: GoodsRequest):
    profile = get_goods_profile(request.goods_category, request.planned_date)
    rule = evaluate_goods(
        GoodsInput(
            item_name=request.item_name,
            estimated_price=request.estimated_price,
            planned_date=request.planned_date,
            is_sme_competition_product=request.is_sme_competition_product,
            direct_production_applicable=request.direct_production_applicable,
            is_publication=request.is_publication or profile.default_publication,
            unit_price_contract=request.unit_price_contract or profile.default_unit_price_contract,
        )
    )
    _append_unique(rule.legal_bases, profile.legal_bases)
    _append_unique(rule.checks, profile.checks)
    _append_unique(rule.warnings, profile.warnings)
    if profile.recommend_mas_check:
        _append_unique(rule.checks, ("나라장터 종합쇼핑몰·MAS·제3자단가계약 활용 가능 여부 확인",))
    if profile.requires_two_stage:
        _append_unique(
            rule.warnings,
            ("이 품목유형은 2단계 규격·가격 동시입찰 전용 절차를 우선 검토해야 하며 일반 물품공고를 그대로 사용하면 안 됩니다.",),
        )
    return rule, profile


def _works_rule_profile_and_values(request: WorksRequest):
    profile = get_works_profile(request.school_work_type)
    works_type = profile.works_type if request.school_work_type != SchoolWorkType.OTHER else request.works_type
    industry = request.required_industry.strip() or profile.recommended_industry
    rule = evaluate_works(
        WorksInput(
            work_name=request.work_name,
            estimated_price=request.estimated_price,
            works_type=works_type,
            planned_date=request.planned_date,
            required_industry=industry,
            region_restriction_requested=request.region_restriction_requested,
        )
    )
    _append_unique(rule.legal_bases, profile.legal_bases)
    profile_checks = list(profile.checks)
    if profile.recommended_main_field:
        profile_checks.insert(0, f"추천 주력분야: {profile.recommended_main_field}")
    _append_unique(rule.checks, profile_checks)
    _append_unique(rule.warnings, profile.warnings)
    return rule, profile, works_type, industry


@app.get("/api/catalog/goods")
def get_goods_catalog(planned_date: date | None = None) -> list[dict]:
    return jsonable_encoder([asdict(item) for item in list_goods_profiles(planned_date)])


@app.get("/api/catalog/works")
def get_works_catalog() -> list[dict]:
    return jsonable_encoder([asdict(item) for item in list_works_profiles()])


@app.get("/api/catalog/services")
def get_service_catalog() -> list[dict]:
    """용역은 반드시 최상위 '용역' 아래의 세부유형으로만 제공한다."""
    return jsonable_encoder([asdict(item) for item in list_service_profiles()])


@app.post("/api/evaluate/service")
def evaluate_service_contract(request: ServiceEvaluateRequest) -> dict:
    """세부유형의 전문 검토항목을 일반 용역 계약판정 결과에 함께 붙인다."""
    profile = get_service_profile(request.service_category)
    requires_proposal = request.requires_proposal_evaluation or request.service_category in {
        SchoolServiceType.TRAVEL,
        SchoolServiceType.AFTER_SCHOOL,
    }
    technical = (
        request.technical_service
        or request.service_category == SchoolServiceType.STATUTORY_INSPECTION
    )
    result = evaluate_contract(
        ContractInput(
            service_name=request.service_name,
            estimated_price=request.estimated_price,
            planned_date=request.planned_date,
            vendor_category=request.vendor_category,
            special_entity_requirements_confirmed=request.special_entity_requirements_confirmed,
            special_knowledge_or_qualification=request.special_knowledge_or_qualification,
            technical_service=technical,
            requires_proposal_evaluation=requires_proposal,
        )
    )
    _append_unique(result.legal_bases, profile.legal_bases)
    _append_unique(result.required_checks, profile.checks)
    _append_unique(result.warnings, profile.warnings)
    output = jsonable_encoder(asdict(result))
    output["profile"] = jsonable_encoder(asdict(profile))
    return output


@app.post("/api/evaluate/goods")
def evaluate_goods_contract(request: GoodsRequest) -> dict:
    rule, profile = _goods_rule_and_profile(request)
    result = jsonable_encoder(asdict(rule))
    result["profile"] = jsonable_encoder(asdict(profile))
    return result


@app.post("/api/documents/goods/preview")
def preview_goods_documents(request: GoodsRequest) -> dict:
    rule, profile = _goods_rule_and_profile(request)
    documents = build_goods_documents(
        GoodsDocumentData(
            school_name=request.school_name,
            item_name=request.item_name,
            start_date=None,
            delivery_date=request.delivery_date,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            budget_amount=request.budget_amount,
            quantity_text=request.quantity_text,
            specification_text=request.specification_text,
            delivery_place=request.delivery_place,
            warranty_text=request.warranty_text,
            inspection_text=request.inspection_text,
            notice_number=request.notice_number,
            notice_date=request.planned_date,
            bid_start=request.bid_start,
            bid_end=request.bid_end,
            bid_open=request.bid_open,
            region_limit=request.region_limit,
            detail_product_name=request.detail_product_name,
            detail_product_code=request.detail_product_code,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            joint_supply_allowed=request.joint_supply_allowed,
            rebid_allowed=request.rebid_allowed,
            category_label=profile.label,
            purchase_method_hint=profile.purchase_method_hint,
            category_checks=profile.checks,
        ),
        rule,
    )
    result = _documents_preview(documents)
    result["rule"] = jsonable_encoder(asdict(rule))
    result["profile"] = jsonable_encoder(asdict(profile))
    return result


@app.post("/api/documents/goods/package-hwpx")
def package_goods_documents(request: GoodsRequest) -> StreamingResponse:
    rule, profile = _goods_rule_and_profile(request)
    documents = build_goods_documents(
        GoodsDocumentData(
            school_name=request.school_name,
            item_name=request.item_name,
            start_date=None,
            delivery_date=request.delivery_date,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            budget_amount=request.budget_amount,
            quantity_text=request.quantity_text,
            specification_text=request.specification_text,
            delivery_place=request.delivery_place,
            warranty_text=request.warranty_text,
            inspection_text=request.inspection_text,
            notice_number=request.notice_number,
            notice_date=request.planned_date,
            bid_start=request.bid_start,
            bid_end=request.bid_end,
            bid_open=request.bid_open,
            region_limit=request.region_limit,
            detail_product_name=request.detail_product_name,
            detail_product_code=request.detail_product_code,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            joint_supply_allowed=request.joint_supply_allowed,
            rebid_allowed=request.rebid_allowed,
            category_label=profile.label,
            purchase_method_hint=profile.purchase_method_hint,
            category_checks=profile.checks,
        ),
        rule,
    )
    return _hwpx_response(documents, "ddalkkak_goods_hwpx.zip")


@app.post("/api/evaluate/works")
def evaluate_works_contract(request: WorksRequest) -> dict:
    rule, profile, _, _ = _works_rule_profile_and_values(request)
    result = jsonable_encoder(asdict(rule))
    result["profile"] = jsonable_encoder(asdict(profile))
    return result


@app.post("/api/documents/works/preview")
def preview_works_documents(request: WorksRequest) -> dict:
    rule, profile, _, industry = _works_rule_profile_and_values(request)
    documents = build_works_documents(
        WorksDocumentData(
            school_name=request.school_name,
            work_name=request.work_name,
            location=request.location,
            start_date=None,
            completion_days=request.completion_days,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            budget_amount=request.budget_amount,
            scope_text=request.scope_text,
            required_industry=industry,
            school_work_type_label=profile.label,
            recommended_main_field=profile.recommended_main_field,
            design_summary=request.design_summary,
            safety_text=request.safety_text,
            notice_number=request.notice_number,
            notice_date=request.planned_date,
            bid_start=request.bid_start,
            bid_end=request.bid_end,
            bid_open=request.bid_open,
            region_limit=request.region_limit,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            a_value_total=request.a_value_total,
            insurance_breakdown_text=request.insurance_breakdown_text,
            site_explanation=request.site_explanation,
            joint_supply_allowed=request.joint_supply_allowed,
            rebid_allowed=request.rebid_allowed,
        ),
        rule,
    )
    result = _documents_preview(documents)
    result["rule"] = jsonable_encoder(asdict(rule))
    result["profile"] = jsonable_encoder(asdict(profile))
    return result


@app.post("/api/documents/works/package-hwpx")
def package_works_documents(request: WorksRequest) -> StreamingResponse:
    rule, profile, _, industry = _works_rule_profile_and_values(request)
    documents = build_works_documents(
        WorksDocumentData(
            school_name=request.school_name,
            work_name=request.work_name,
            location=request.location,
            start_date=None,
            completion_days=request.completion_days,
            estimated_price=request.estimated_price,
            base_amount=request.base_amount,
            budget_amount=request.budget_amount,
            scope_text=request.scope_text,
            required_industry=industry,
            school_work_type_label=profile.label,
            recommended_main_field=profile.recommended_main_field,
            design_summary=request.design_summary,
            safety_text=request.safety_text,
            notice_number=request.notice_number,
            notice_date=request.planned_date,
            bid_start=request.bid_start,
            bid_end=request.bid_end,
            bid_open=request.bid_open,
            region_limit=request.region_limit,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            a_value_total=request.a_value_total,
            insurance_breakdown_text=request.insurance_breakdown_text,
            site_explanation=request.site_explanation,
            joint_supply_allowed=request.joint_supply_allowed,
            rebid_allowed=request.rebid_allowed,
        ),
        rule,
    )
    return _hwpx_response(documents, "ddalkkak_works_hwpx.zip")


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
            notice_date=request.notice_date,
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
            notice_date=request.notice_date,
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
            notice_date=request.notice_date,
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
            notice_date=request.notice_date,
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


@app.get("/workspace")
def workspace() -> FileResponse:
    return FileResponse(STATIC_DIR / "workspace.html")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
