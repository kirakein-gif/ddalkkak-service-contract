from datetime import date
from io import BytesIO
from zipfile import ZipFile

from hwpx import HwpxDocument

from app.documents.formats import build_hwpx_zip
from app.documents.program_docs import ProgramDocumentData, build_program_documents
from app.documents.travel_docs import TravelDocumentData, build_travel_documents
from app.rules.two_stage import TwoStageInput, TwoStageMethod, evaluate_two_stage


def test_two_stage_simultaneous_flow_only_opens_price_for_qualified():
    result = evaluate_two_stage(
        TwoStageInput(
            service_name="수학여행 위탁용역",
            method=TwoStageMethod.SIMULTANEOUS,
            proposal_pass_score=80,
        )
    )
    assert result.price_open_only_for_qualified is True
    assert "제18조" in result.legal_basis
    assert any("가격입찰" in step for step in result.flow)


def test_two_stage_score_is_school_defined():
    result = evaluate_two_stage(
        TwoStageInput(
            service_name="방과후 프로그램",
            proposal_pass_score=75,
        )
    )
    assert result.proposal_pass_score == 75
    assert any("80점" in item for item in result.warnings)


def test_travel_builds_five_hwpx_documents():
    rule = evaluate_two_stage(TwoStageInput(service_name="수학여행", proposal_pass_score=80))
    docs = build_travel_documents(
        TravelDocumentData(
            school_name="○○중학교",
            service_name="2027학년도 2학년 수학여행 위탁용역",
            destination="제주도",
            start_date=date(2027, 5, 10),
            end_date=date(2027, 5, 13),
            student_count=200,
            teacher_count=12,
            estimated_price=120_000_000,
            base_amount=132_000_000,
            nights=3,
            meals=7,
            itinerary_text="1일차: 학교 → 제주",
        ),
        rule,
    )
    assert len(docs) == 5
    assert "여행업" in docs[0].content
    payload = build_hwpx_zip(docs)
    with ZipFile(BytesIO(payload)) as archive:
        assert len(archive.namelist()) == 5
        with HwpxDocument.open(BytesIO(archive.read(archive.namelist()[0]))) as hwpx:
            assert len(hwpx.sections) >= 1


def test_program_builds_five_documents_with_program_specific_terms():
    rule = evaluate_two_stage(TwoStageInput(service_name="늘봄 프로그램", proposal_pass_score=80))
    docs = build_program_documents(
        ProgramDocumentData(
            school_name="○○초등학교",
            service_name="2027학년도 늘봄학교 프로그램 운영 용역",
            start_date=date(2027, 3, 1),
            end_date=date(2028, 2, 29),
            estimated_price=250_000_000,
            expected_students=180,
            program_count=12,
            programs_text="독서논술, 축구, 방송댄스, 컴퓨터",
            operation_text="학기 중 방과후, 방학 중 오전",
        ),
        rule,
    )
    assert len(docs) == 5
    combined = "\n".join(doc.content for doc in docs)
    assert "강사" in combined
    assert "출결" in combined
    assert "교재" in combined



def test_travel_chungnam_samples_keep_variable_terms_out_of_hardcoded_rules():
    rule = evaluate_two_stage(TwoStageInput(service_name="수학여행", proposal_pass_score=80))
    docs = build_travel_documents(
        TravelDocumentData(
            school_name="○○중학교",
            service_name="2027학년도 수학여행 위탁용역",
            destination="서울·경기",
            start_date=date(2027, 10, 20),
            end_date=date(2027, 10, 22),
            student_count=80,
            teacher_count=10,
            estimated_price=50_000_000,
            base_amount=55_000_000,
            tie_break_method="전자조달시스템 자동추첨",
            contract_deadline_text="낙찰통보 후 10일 이내",
        ),
        rule,
    )
    notice = docs[0].content
    assert "복수예비가격 15개" in notice
    assert "보낸 문서함" in notice
    assert "규격적격자에 한하여 가격개찰" in notice
    assert "전자조달시스템 자동추첨" in notice
    assert "낙찰통보 후 10일 이내" in notice
    assert "학생·교직원을 구분" in notice


def test_two_stage_requires_school_to_choose_equal_price_method():
    result = evaluate_two_stage(TwoStageInput(service_name="수학여행"))
    assert any("동일가격" in item for item in result.checks)
