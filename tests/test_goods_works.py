from datetime import date
from io import BytesIO
from zipfile import ZipFile

from app.documents.formats import build_hwpx_zip
from app.documents.goods_docs import GoodsDocumentData, build_goods_documents
from app.documents.works_docs import WorksDocumentData, build_works_documents
from app.rules.goods import GoodsInput, GoodsRoute, evaluate_goods
from app.rules.goods_catalog import GoodsCategory, get_goods_profile
from app.rules.works import WorksInput, WorksRoute, WorksType, evaluate_works
from app.rules.works_catalog import SchoolWorkType, get_works_profile


def test_goods_small_value_routes():
    assert evaluate_goods(GoodsInput("복사용지", 20_000_000)).route_code == GoodsRoute.ONE_PERSON
    r = evaluate_goods(GoodsInput("복사용지", 20_000_001))
    assert r.route_code == GoodsRoute.TWO_PERSON
    assert r.minimum_quote_rate == 0.88
    assert evaluate_goods(GoodsInput("복사용지", 100_000_001)).route_code == GoodsRoute.COMPETITIVE


def test_goods_direct_production_check():
    r = evaluate_goods(GoodsInput(
        "사물함",
        30_000_000,
        is_sme_competition_product=True,
        direct_production_applicable=True,
    ))
    assert "직접생산확인증명서" in r.direct_production_status


def test_works_limits_by_type():
    assert evaluate_works(WorksInput("건축공사", 400_000_000, WorksType.GENERAL)).route_code == WorksRoute.TWO_PERSON
    assert evaluate_works(WorksInput("전문공사", 200_000_000, WorksType.SPECIALIZED)).route_code == WorksRoute.TWO_PERSON
    assert evaluate_works(WorksInput("전기공사", 160_000_000, WorksType.OTHER)).route_code == WorksRoute.TWO_PERSON
    assert evaluate_works(WorksInput("전기공사", 160_000_001, WorksType.OTHER)).route_code == WorksRoute.COMPETITIVE


def test_works_small_value_rate():
    r = evaluate_works(WorksInput("교실보수", 50_000_000, WorksType.SPECIALIZED))
    assert r.minimum_quote_rate == 0.89745


def test_goods_and_works_generate_openable_hwpx_sets():
    gr = evaluate_goods(GoodsInput("복사용지", 30_000_000))
    gd = build_goods_documents(
        GoodsDocumentData(
            school_name="○○초등학교",
            item_name="복사용지 구매",
            start_date=None,
            delivery_date=date(2027, 3, 15),
            estimated_price=30_000_000,
            quantity_text="A4 80g 500박스",
            specification_text="백색도 및 평량은 규격서 참조",
        ),
        gr,
    )
    wr = evaluate_works(WorksInput("교실 바닥 교체공사", 80_000_000, WorksType.SPECIALIZED))
    wd = build_works_documents(
        WorksDocumentData(
            school_name="○○초등학교",
            work_name="교실 바닥 교체공사",
            location="본관 2층",
            start_date=None,
            completion_days=30,
            estimated_price=80_000_000,
            scope_text="기존 바닥 철거 및 신설",
            required_industry="실내건축공사업 등 공고에서 정한 업종",
        ),
        wr,
    )
    for docs in (gd, wd):
        with ZipFile(BytesIO(build_hwpx_zip(docs))) as archive:
            assert len(archive.namelist()) == 4
            assert all(name.endswith(".hwpx") for name in archive.namelist())



def test_school_works_catalog_maps_to_legal_trade():
    interior = get_works_profile(SchoolWorkType.INTERIOR)
    electrical = get_works_profile(SchoolWorkType.ELECTRICAL)
    waterproof = get_works_profile(SchoolWorkType.WET_WATERPROOF)

    assert interior.works_type == WorksType.SPECIALIZED
    assert interior.recommended_industry == "실내건축공사업"
    assert interior.recommended_main_field == "실내건축공사"
    assert electrical.works_type == WorksType.OTHER
    assert electrical.recommended_industry == "전기공사업"
    assert waterproof.recommended_main_field == "습식·방수공사"


def test_goods_catalog_has_school_specific_purchase_profiles():
    food = get_goods_profile(GoodsCategory.FOOD_INGREDIENTS, date(2026, 9, 26))
    milk = get_goods_profile(GoodsCategory.MILK, date(2026, 9, 26))
    books = get_goods_profile(GoodsCategory.BOOKS, date(2026, 9, 26))
    uniform = get_goods_profile(GoodsCategory.UNIFORM, date(2026, 9, 26))

    assert any("입찰참가 제한" in item for item in food.checks)
    assert milk.default_unit_price_contract is True
    assert books.default_publication is True
    assert uniform.requires_two_stage is True
