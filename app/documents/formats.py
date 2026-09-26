"""공통 계약문서 출력 포맷 유틸리티.

공사·용역·물품 모든 모듈이 HWPX/DOCX 패키징에 재사용한다.
공고문은 충청남도교육청·학교 실제 입찰공고의 조판 관행을 참고한 전용 레이아웃으로 출력한다.
"""

from dataclasses import dataclass, field
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt
from hwpx import HwpxDocument


_HWPUNIT_PER_MM = 7200 / 25.4
_HWPUNIT_PER_PT = 100


@dataclass(slots=True)
class GeneratedDocument:
    key: str
    title: str
    content: str
    layout: str = "default"
    notice_number: str = ""
    issuer: str = ""
    summary_rows: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    issue_date: str = ""
    signatory: str = ""
    alert_text: str = ""
    integrity_text: str = ""


def _safe_filename(title: str) -> str:
    return title.replace("/", "_").replace("\\", "_").replace(":", "_")


def _mm(value: float) -> int:
    return int(round(value * _HWPUNIT_PER_MM))


def _pt(value: float) -> int:
    return int(round(value * _HWPUNIT_PER_PT))


def _char_style(
    document: HwpxDocument,
    *,
    bold: bool = False,
    size: float = 11.5,
    font: str = "휴먼명조",
    color: str = "#000000",
) -> str:
    return document.ensure_run_style(
        bold=bold,
        size=size,
        font=font,
        color=color,
    )


def _apply_para_format(
    document: HwpxDocument,
    paragraph,
    *,
    align: str = "JUSTIFY",
    line_spacing: int = 165,
    left_mm: float = 0,
    right_mm: float = 0,
    first_line_mm: float = 0,
    before_pt: float = 0,
    after_pt: float = 0,
    keep_with_next: bool = False,
    keep_lines: bool = False,
) -> None:
    margins = {
        "left": _mm(left_mm),
        "right": _mm(right_mm),
        "intent": _mm(first_line_mm),
        "prev": _pt(before_pt),
        "next": _pt(after_pt),
    }
    paragraph.para_pr_id_ref = document.headers[0].ensure_paragraph_format(
        base_para_pr_id=paragraph.para_pr_id_ref,
        alignment=align,
        line_spacing_percent=line_spacing,
        margins=margins,
        break_setting={
            "keep_with_next": keep_with_next,
            "keep_lines": keep_lines,
        },
    )


def _add_paragraph(
    document: HwpxDocument,
    text: str,
    *,
    bold: bool = False,
    size: float = 11.5,
    font: str = "휴먼명조",
    color: str = "#000000",
    align: str = "JUSTIFY",
    line_spacing: int = 165,
    left_mm: float = 0,
    right_mm: float = 0,
    first_line_mm: float = 0,
    before_pt: float = 0,
    after_pt: float = 0,
    keep_with_next: bool = False,
    keep_lines: bool = False,
):
    paragraph = document.add_paragraph(
        text,
        char_pr_id_ref=_char_style(
            document,
            bold=bold,
            size=size,
            font=font,
            color=color,
        ),
    )
    _apply_para_format(
        document,
        paragraph,
        align=align,
        line_spacing=line_spacing,
        left_mm=left_mm,
        right_mm=right_mm,
        first_line_mm=first_line_mm,
        before_pt=before_pt,
        after_pt=after_pt,
        keep_with_next=keep_with_next,
        keep_lines=keep_lines,
    )
    return paragraph


def _style_cell(
    document: HwpxDocument,
    table,
    row: int,
    col: int,
    *,
    bold: bool = False,
    size: float = 10.5,
    font: str = "휴먼명조",
    align: str = "CENTER",
    line_spacing: int = 145,
    logical: bool = False,
) -> None:
    cell = table.cell(row, col)
    if not cell.paragraphs:
        return
    paragraph = cell.paragraphs[0]
    if paragraph.runs:
        paragraph.runs[0].char_pr_id_ref = _char_style(
            document,
            bold=bold,
            size=size,
            font=font,
        )
    _apply_para_format(
        document,
        paragraph,
        align=align,
        line_spacing=line_spacing,
        left_mm=1.2,
        right_mm=1.2,
        before_pt=1.0,
        after_pt=1.0,
        keep_lines=True,
    )


def _date_to_korean(value: str) -> str:
    if not value:
        return ""
    parts = value.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return f"{int(parts[0])}년 {int(parts[1])}월 {int(parts[2])}일"
    return value


def _add_box(
    document: HwpxDocument,
    text: str,
    *,
    title: str = "",
    title_size: float = 11.5,
    body_size: float = 10.5,
) -> None:
    if title:
        _add_paragraph(
            document,
            title,
            bold=True,
            size=title_size,
            font="휴먼고딕",
            align="CENTER",
            line_spacing=140,
            before_pt=5,
            after_pt=3,
            keep_with_next=True,
        )
    border = document.ensure_border_fill(
        border_color="#5A5A5A",
        border_width="0.12 mm",
        fill_color="#FFFFFF",
    )
    table = document.add_table(rows=1, cols=1, border_fill_id_ref=border)
    table.set_cell_text(0, 0, text)
    _style_cell(
        document,
        table,
        0,
        0,
        size=body_size,
        font="휴먼명조",
        align="JUSTIFY",
        line_spacing=155,
    )
    _add_paragraph(document, "", size=4, line_spacing=100, after_pt=1)


def _add_summary_table(
    document: HwpxDocument,
    rows: tuple[tuple[str, ...], ...],
) -> None:
    if not rows:
        return
    border = document.ensure_border_fill(
        border_color="#4B4B4B",
        border_width="0.12 mm",
        fill_color="#FFFFFF",
    )
    table = document.add_table(
        rows=len(rows),
        cols=4,
        border_fill_id_ref=border,
    )
    table.set_column_widths([1.15, 3.05, 1.15, 2.65])

    for row_index, row in enumerate(rows):
        values = tuple(row) + ("",) * (4 - len(row))
        label1, value1, label2, value2 = values[:4]

        table.set_cell_text(row_index, 0, label1)
        table.set_cell_shading(row_index, 0, "F1F1F1")
        _style_cell(
            document,
            table,
            row_index,
            0,
            bold=True,
            size=10.3,
            font="휴먼고딕",
        )

        if not label2 and not value2:
            table.merge_cells(row_index, 1, row_index, 3)
            table.set_cell_text(row_index, 1, value1, logical=True)
            _style_cell(
                document,
                table,
                row_index,
                1,
                size=10.5,
                font="휴먼명조",
                align="LEFT",
                logical=True,
            )
        else:
            table.set_cell_text(row_index, 1, value1)
            _style_cell(
                document,
                table,
                row_index,
                1,
                size=10.5,
                font="휴먼명조",
                align="LEFT",
            )
            table.set_cell_text(row_index, 2, label2)
            table.set_cell_shading(row_index, 2, "F1F1F1")
            _style_cell(
                document,
                table,
                row_index,
                2,
                bold=True,
                size=10.3,
                font="휴먼고딕",
            )
            table.set_cell_text(row_index, 3, value2)
            _style_cell(
                document,
                table,
                row_index,
                3,
                size=10.5,
                font="휴먼명조",
                align="LEFT",
            )
    _add_paragraph(document, "", size=4, line_spacing=100, after_pt=2)


def _render_notice_hwpx(item: GeneratedDocument) -> bytes:
    document = HwpxDocument.new()

    # 문자서식에서 폰트 이름만 참조하면 한/글이 기본글꼴로 대체할 수 있으므로
    # HWPX 헤더의 7개 언어 fontface 블록에 실제 서체를 명시적으로 등록한다.
    # 글꼴 파일을 임베드하지 않고, 미설치 환경을 위한 대체 서체만 함께 선언한다.
    document.styles.ensure_font("휴먼명조", subst_face="함초롬바탕")
    document.styles.ensure_font("휴먼고딕", subst_face="맑은 고딕")

    # 충남교육청 공고 PDF의 A4 본문 폭과 유사한 약 20 mm 좌우 여백.
    section = document.sections[0]
    section.properties.set_page_margins(
        left=_mm(20),
        right=_mm(20),
        top=_mm(18),
        bottom=_mm(15),
        header=_mm(8),
        footer=_mm(8),
        gutter=0,
    )

    if item.notice_number:
        _add_paragraph(
            document,
            item.notice_number,
            bold=True,
            size=11.5,
            font="휴먼명조",
            align="LEFT",
            line_spacing=130,
            after_pt=14,
        )

    _add_paragraph(
        document,
        item.title,
        bold=True,
        size=22,
        font="휴먼고딕",
        align="CENTER",
        line_spacing=125,
        after_pt=13,
        keep_with_next=True,
        keep_lines=True,
    )

    if item.issue_date:
        _add_paragraph(
            document,
            _date_to_korean(item.issue_date),
            size=11.5,
            font="휴먼명조",
            align="RIGHT",
            line_spacing=130,
            after_pt=2,
        )
    if item.issuer:
        _add_paragraph(
            document,
            item.issuer,
            size=12,
            font="휴먼명조",
            align="RIGHT",
            line_spacing=130,
            after_pt=11,
        )

    if item.alert_text:
        _add_box(document, item.alert_text, body_size=10.5)

    if item.integrity_text:
        _add_box(
            document,
            item.integrity_text,
            title="< 본 계약은 청렴계약(서약)제가 적용됩니다 >",
            title_size=11.5,
            body_size=10.4,
        )

    body_lines = item.content.splitlines()
    in_summary = False
    summary_inserted = False
    sub_index = 0
    korean = (
        "가", "나", "다", "라", "마", "바", "사", "아",
        "자", "차", "카", "타", "파", "하",
    )

    for raw in body_lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            continue
        if line.startswith("- 공고번호:") or line.startswith("- 발주기관:"):
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            in_summary = bool(item.summary_rows and heading.startswith("1."))
            sub_index = 0
            _add_paragraph(
                document,
                heading,
                bold=True,
                size=13,
                font="휴먼고딕",
                align="LEFT",
                line_spacing=150,
                before_pt=10,
                after_pt=4,
                keep_with_next=True,
                keep_lines=True,
            )
            if in_summary and not summary_inserted:
                _add_summary_table(document, item.summary_rows)
                summary_inserted = True
            continue

        if in_summary:
            continue

        if line.startswith("- "):
            prefix = korean[sub_index] + "." if sub_index < len(korean) else "•"
            sub_index += 1
            _add_paragraph(
                document,
                f"{prefix} {line[2:].strip()}",
                size=11.5,
                font="휴먼명조",
                align="JUSTIFY",
                line_spacing=168,
                left_mm=7,
                first_line_mm=-5,
                after_pt=1.5,
                keep_lines=True,
            )
            continue

        if line.startswith("※"):
            _add_paragraph(
                document,
                line,
                bold=False,
                size=10.5,
                font="휴먼명조",
                align="JUSTIFY",
                line_spacing=155,
                left_mm=5,
                first_line_mm=-5,
                before_pt=1,
                after_pt=2,
                keep_lines=True,
            )
            continue

        _add_paragraph(
            document,
            line,
            size=11.5,
            font="휴먼명조",
            align="JUSTIFY",
            line_spacing=168,
            after_pt=1.5,
            keep_lines=True,
        )

    if item.issue_date or item.signatory:
        _add_paragraph(document, "", size=6, line_spacing=100, before_pt=9)
        _add_paragraph(
            document,
            "위와 같이 공고합니다.",
            size=11.5,
            font="휴먼명조",
            align="CENTER",
            line_spacing=140,
            before_pt=8,
            after_pt=4,
            keep_with_next=True,
        )
        if item.issue_date:
            _add_paragraph(
                document,
                _date_to_korean(item.issue_date),
                size=11.5,
                font="휴먼명조",
                align="CENTER",
                line_spacing=140,
                after_pt=5,
                keep_with_next=True,
            )
        if item.signatory:
            _add_paragraph(
                document,
                item.signatory,
                bold=True,
                size=15.5,
                font="휴먼고딕",
                align="CENTER",
                line_spacing=135,
                keep_lines=True,
            )

    document.set_footer_content(
        [
            {
                "align": "CENTER",
                "children": [
                    {
                        "type": "page_number",
                        "format": "page",
                        "position": "BOTTOM_CENTER",
                    }
                ],
            }
        ],
        section_index=0,
    )
    return document.to_bytes()


def document_to_hwpx_bytes(item: GeneratedDocument) -> bytes:
    if item.layout == "public_notice":
        return _render_notice_hwpx(item)

    document = HwpxDocument.new()
    for raw in item.content.splitlines():
        line = raw.rstrip()
        if not line:
            document.add_paragraph("")
        elif line.startswith("# "):
            document.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            document.add_heading(line[3:], level=2)
        elif line.startswith("- "):
            document.add_paragraph("• " + line[2:])
        else:
            document.add_paragraph(line)
    return document.to_bytes()


def build_hwpx_zip(documents: list[GeneratedDocument]) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for index, item in enumerate(documents, start=1):
            archive.writestr(
                f"{index:02d}_{_safe_filename(item.title)}.hwpx",
                document_to_hwpx_bytes(item),
            )
    return stream.getvalue()


def _docx_font(document: Document) -> None:
    style = document.styles["Normal"]
    style.font.name = "Malgun Gothic"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    style.font.size = Pt(10.5)


def document_to_docx_bytes(item: GeneratedDocument) -> bytes:
    document = Document()
    _docx_font(document)
    for raw in item.content.splitlines():
        line = raw.rstrip()
        if not line:
            document.add_paragraph()
        elif line.startswith("# "):
            p = document.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(line[2:])
            run.bold = True
            run.font.size = Pt(16)
        elif line.startswith("## "):
            p = document.add_paragraph()
            run = p.add_run(line[3:])
            run.bold = True
            run.font.size = Pt(12)
        elif line.startswith("- "):
            document.add_paragraph(line[2:], style="List Bullet")
        else:
            document.add_paragraph(line)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def build_docx_zip(documents: list[GeneratedDocument]) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for index, item in enumerate(documents, start=1):
            archive.writestr(
                f"{index:02d}_{_safe_filename(item.title)}.docx",
                document_to_docx_bytes(item),
            )
    return stream.getvalue()
