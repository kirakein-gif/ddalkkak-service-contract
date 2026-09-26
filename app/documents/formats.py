"""공통 계약문서 출력 포맷 유틸리티.

공사·용역·물품 모든 모듈이 HWPX/DOCX 패키징에 재사용한다.
"""

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt
from hwpx import HwpxDocument


@dataclass(slots=True)
class GeneratedDocument:
    key: str
    title: str
    content: str


def _safe_filename(title: str) -> str:
    return title.replace("/", "_").replace("\\", "_").replace(":", "_")


def document_to_hwpx_bytes(item: GeneratedDocument) -> bytes:
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
