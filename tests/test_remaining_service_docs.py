from datetime import date
from io import BytesIO
from zipfile import ZipFile

from app.documents.facility_docs import FacilityDocumentData, build_facility_documents
from app.documents.formats import build_hwpx_zip
from app.documents.labor_docs import LaborDocumentData, build_labor_documents
from app.rules.simple_labor import evaluate_simple_labor


def test_facility_docs_include_license_and_statutory_schedule():
    docs = build_facility_documents(
        FacilityDocumentData(
            school_name="○○초등학교",
            service_name="2027년 소방시설 자체점검 용역",
            facility_type="소방시설",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
            estimated_price=35_000_000,
            statutory_inspection=True,
            statutory_basis="소방시설 설치 및 관리에 관한 법률 등",
            required_license="소방시설관리업 등 공고에서 정한 자격",
            inspection_schedule="상반기 1회, 하반기 1회",
        )
    )
    assert len(docs) == 5
    combined = "\n".join(d.content for d in docs)
    assert "법정점검" in combined
    assert "면허" in combined
    assert len(ZipFile(BytesIO(build_hwpx_zip(docs))).namelist()) == 5


def test_simple_labor_excludes_two_stage_and_negotiation():
    rule = evaluate_simple_labor()
    assert rule.two_stage_allowed is False
    assert rule.negotiation_allowed is False


def test_labor_docs_include_labor_cost_and_worker_protection():
    rule = evaluate_simple_labor()
    docs = build_labor_documents(
        LaborDocumentData(
            school_name="○○중학교",
            service_name="2027년 교사동 청소용역",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
            estimated_price=80_000_000,
            worker_count=2,
            daily_hours=8,
            work_area="교사동 및 공용부",
            scope_text="일상청소, 화장실, 복도, 계단",
        ),
        rule,
    )
    assert len(docs) == 5
    combined = "\n".join(d.content for d in docs)
    assert "최저임금" in combined
    assert "4대보험" in combined
    assert "2단계 입찰 대상에서 제외" in combined
