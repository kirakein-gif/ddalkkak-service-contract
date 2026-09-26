from datetime import date
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from hwpx import HwpxDocument

from app.documents.formats import document_to_hwpx_bytes
from app.documents.goods_docs import GoodsDocumentData, build_goods_documents
from app.documents.works_docs import WorksDocumentData, build_works_documents
from app.rules.goods import GoodsInput, evaluate_goods
from app.rules.works import WorksInput, WorksType, evaluate_works


def test_goods_two_person_notice_is_publication_ready():
    rule = evaluate_goods(GoodsInput("급식용 부식 구매", 30_000_000))
    docs = build_goods_documents(
        GoodsDocumentData(
            school_name="○○중학교",
            item_name="2027년 3월 급식용 부식 구매",
            start_date=None,
            notice_date=date(2027, 2, 15),
            delivery_date=date(2027, 3, 31),
            estimated_price=30_000_000,
            base_amount=33_000_000,
            budget_amount=33_000_000,
            quantity_text="내역서 참조",
            specification_text="현품설명서 및 규격서 참조",
            notice_number="○○중-공고-2027-1",
            bid_start="2027. 2. 20. 10:00",
            bid_end="2027. 2. 24. 10:00",
            bid_open="2027. 2. 24. 11:00",
            region_limit="충청남도",
            contact_name="계약담당자",
            contact_phone="041-000-0000",
        ),
        rule,
    )
    notice = docs[0]
    assert "소액수의 전자견적 제출 안내공고" in notice.title
    assert "88%" in notice.content
    assert "15개의 복수예비가격" in notice.content
    assert "가장 많이 선택된 4개" in notice.content
    assert "면세사업자" in notice.content
    assert "충청남도" in notice.content
    assert "입찰보증금 납부대상이 아닙니다" in notice.content


def test_goods_notice_contains_g2b_electronic_contract_clauses():
    rule = evaluate_goods(GoodsInput("복사용지 구매", 30_000_000))
    notice = build_goods_documents(
        GoodsDocumentData(
            school_name="○○초등학교",
            item_name="복사용지 구매",
            start_date=None,
            notice_date=date(2027, 2, 15),
            delivery_date=date(2027, 3, 31),
            estimated_price=30_000_000,
            base_amount=33_000_000,
        ),
        rule,
    )[0].content

    assert "전자계약" in notice
    assert "보낸 문서함" in notice
    assert "문서서버" in notice
    assert "제15조제1항" in notice
    assert "자동추첨 프로그램" in notice
    assert "10일 이내" in notice
    assert "1588-0800" in notice


def test_publication_goods_notice_uses_90_percent_and_direct_production_text():
    rule = evaluate_goods(
        GoodsInput(
            "도서 구매",
            30_000_000,
            is_sme_competition_product=True,
            direct_production_applicable=True,
            is_publication=True,
        )
    )
    docs = build_goods_documents(
        GoodsDocumentData(
            school_name="○○고등학교",
            item_name="도서 구매",
            start_date=None,
            delivery_date=date(2027, 4, 1),
            estimated_price=30_000_000,
            base_amount=33_000_000,
            detail_product_name="기타인쇄물",
            detail_product_code="5510159901",
        ),
        rule,
    )
    notice = docs[0].content
    assert "90%" in notice
    assert "직접생산확인증명서" in notice
    assert "5510159901" in notice


def test_works_notice_contains_a_value_formula_and_statutory_costs():
    rule = evaluate_works(
        WorksInput(
            "교실 바닥 교체공사",
            80_000_000,
            WorksType.SPECIALIZED,
            required_industry="실내건축공사업",
        )
    )
    docs = build_works_documents(
        WorksDocumentData(
            school_name="○○초등학교",
            work_name="교실 바닥 교체공사",
            location="본관 2층",
            start_date=None,
            notice_date=date(2027, 1, 5),
            completion_days=30,
            estimated_price=80_000_000,
            base_amount=88_000_000,
            budget_amount=90_000_000,
            required_industry="실내건축공사업",
            a_value_total=3_730_152,
            insurance_breakdown_text="국민연금 1,612,136원 / 건강보험 1,220,132원 / 장기요양 160,325원 / 산업안전보건관리비 737,559원",
            bid_start="2027. 1. 10. 10:00",
            bid_end="2027. 1. 15. 10:00",
            bid_open="2027. 1. 15. 11:00",
            region_limit="충청남도",
        ),
        rule,
    )
    notice = docs[0]
    assert "수의계약 전자견적 제출 안내공고" in notice.title
    assert "89.745%" in notice.content
    assert "A값(3,730,152원)" in notice.content
    assert "산업안전보건관리비" in notice.content
    assert "노무비 구분관리" in notice.content
    assert "사후정산" in notice.content
    assert "자동추첨 프로그램" in notice.content
    assert "전자계약" in notice.content


def test_notice_hwpx_has_real_notice_layout_objects():
    rule = evaluate_goods(GoodsInput("복사용지 구매", 30_000_000))
    notice = build_goods_documents(
        GoodsDocumentData(
            school_name="○○초등학교",
            item_name="복사용지 구매",
            start_date=None,
            notice_date=date(2027, 2, 15),
            delivery_date=date(2027, 3, 31),
            estimated_price=30_000_000,
            base_amount=33_000_000,
            notice_number="○○초-공고-2027-1",
        ),
        rule,
    )[0]

    payload = document_to_hwpx_bytes(notice)
    with HwpxDocument.open(BytesIO(payload)) as hwpx:
        exported = hwpx.export_text()
        assert "복사용지 구매" in exported
        assert "전자계약" in exported
        assert "○○초등학교장" in exported

    with ZipFile(BytesIO(payload)) as archive:
        section_name = next(name for name in archive.namelist() if name.endswith("section0.xml"))
        root = ET.fromstring(archive.read(section_name))
        names = [element.tag.rsplit("}", 1)[-1] for element in root.iter()]
        assert "tbl" in names
        assert "footer" in names or "pageNum" in names


def test_competitive_goods_and_works_notice_titles_change():
    goods_rule = evaluate_goods(GoodsInput("기자재 구매", 150_000_000))
    works_rule = evaluate_works(WorksInput("증축공사", 500_000_000, WorksType.GENERAL))

    goods_docs = build_goods_documents(
        GoodsDocumentData(
            school_name="○○학교",
            item_name="기자재 구매",
            start_date=None,
            delivery_date=date(2027, 5, 1),
            estimated_price=150_000_000,
        ),
        goods_rule,
    )
    works_docs = build_works_documents(
        WorksDocumentData(
            school_name="○○학교",
            work_name="증축공사",
            location="교내",
            start_date=None,
            completion_days=180,
            estimated_price=500_000_000,
        ),
        works_rule,
    )
    assert goods_docs[0].title.endswith("물품 구매 전자입찰 공고")
    assert works_docs[0].title.endswith("공사 전자입찰 공고")
    assert "적격심사" in works_docs[0].content
