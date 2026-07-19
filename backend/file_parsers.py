from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from pypdf import PdfReader

from .models import ContentBlock, MaterialModality, RawMaterial, SourceType
from .multimodal_parser import MultimodalParseError, parse_audio, parse_image


SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".docx", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".m4a", ".wav", ".mp4"}


class FileParseError(ValueError):
    pass


def source_type_from_material_id(material_id: str | None) -> SourceType:
    mapping = {
        "financial": SourceType.FINANCIAL_TABLE,
        "annual": SourceType.ANNUAL_REPORT_SUMMARY,
        "management": SourceType.MANAGEMENT_NOTE,
        "sellside": SourceType.SELL_SIDE_SUMMARY,
        "news": SourceType.NEWS_SUMMARY,
        "notes": SourceType.USER_NOTE,
    }
    if material_id and material_id in mapping:
        return mapping[material_id]
    return SourceType.OTHER


def parse_uploaded_file(
    *,
    filename: str,
    data: bytes,
    material_id: str | None = None,
    title: str | None = None,
) -> RawMaterial:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FileParseError(f"暂不支持的文件类型：{ext or 'unknown'}")

    blocks: list[ContentBlock] = []
    warnings: list[str] = []
    modality = MaterialModality.TEXT
    if ext in {".txt", ".md"}:
        content = _decode_text(data)
    elif ext == ".csv":
        content = _parse_csv(data)
    elif ext == ".docx":
        content = _parse_docx(data)
    elif ext == ".xlsx":
        content = _parse_xlsx(data)
    elif ext == ".pdf":
        content = _parse_pdf(data)
    elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
        modality = MaterialModality.IMAGE
        try:
            content, blocks, warnings = parse_image(filename, data)
        except MultimodalParseError as exc:
            raise FileParseError(str(exc)) from exc
    elif ext in {".mp3", ".m4a", ".wav", ".mp4"}:
        modality = MaterialModality.AUDIO
        try:
            content, blocks, warnings = parse_audio(filename, data)
        except MultimodalParseError as exc:
            raise FileParseError(str(exc)) from exc
    else:
        raise FileParseError(f"暂不支持的文件类型：{ext}")

    content = _normalize_text(content)
    if not content:
        raise FileParseError(f"文件未解析出有效文本：{filename}")

    if not blocks:
        blocks = _blocks_from_content(content, ext)
        if ext in {".csv", ".xlsx"}:
            modality = MaterialModality.TABLE
    return RawMaterial(
        title=title or filename,
        content=content,
        source_type=source_type_from_material_id(material_id),
        file_name=filename,
        usage_rights_confirmed=True,
        modality=modality,
        blocks=blocks,
        parse_warnings=warnings,
    )


def _blocks_from_content(content: str, ext: str) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    current_page: int | None = None
    current_sheet: str | None = None
    paragraph = 0
    row = 0
    for line in content.splitlines():
        stripped = line.strip()
        page_match = re.fullmatch(r"## Page (\d+)", stripped)
        if page_match:
            current_page = int(page_match.group(1))
            paragraph = 0
            continue
        if ext == ".xlsx" and stripped.startswith("## "):
            current_sheet = stripped[3:]
            row = 0
            continue
        if not stripped:
            continue
        if ext in {".csv", ".xlsx"}:
            row += 1
            blocks.append(ContentBlock(modality=MaterialModality.TABLE, content=stripped, sheet=current_sheet, row=row))
        else:
            paragraph += 1
            blocks.append(ContentBlock(modality=MaterialModality.TEXT, content=stripped, page=current_page, paragraph=paragraph))
    return blocks


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise FileParseError("文本编码无法识别")


def _parse_csv(data: bytes) -> str:
    text = _decode_text(data)
    rows = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        rows.append(" | ".join(cell.strip() for cell in row))
    return "\n".join(rows)


def _parse_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml")
    except Exception as exc:
        raise FileParseError("Word 文档解析失败，请确认是 .docx 文件") from exc

    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for para in root.findall(".//w:p", ns):
        texts = [node.text or "" for node in para.findall(".//w:t", ns)]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def _parse_xlsx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            shared_strings = _xlsx_shared_strings(zf)
            sheet_names = [name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]
            outputs: list[str] = []
            for sheet_name in sorted(sheet_names):
                outputs.append(f"## {Path(sheet_name).stem}")
                outputs.extend(_xlsx_sheet_rows(zf.read(sheet_name), shared_strings))
            return "\n".join(outputs)
    except Exception as exc:
        raise FileParseError("Excel 文档解析失败，请确认是 .xlsx 文件") from exc


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings: list[str] = []
    for si in root.findall(".//x:si", ns):
        parts = [t.text or "" for t in si.findall(".//x:t", ns)]
        strings.append("".join(parts))
    return strings


def _xlsx_sheet_rows(xml: bytes, shared_strings: list[str]) -> list[str]:
    root = ET.fromstring(xml)
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows: list[str] = []
    for row in root.findall(".//x:row", ns):
        values_by_col: dict[int, str] = {}
        for cell in row.findall("x:c", ns):
            cell_type = cell.attrib.get("t")
            col_index = _xlsx_column_index(cell.attrib.get("r", ""))
            value_node = cell.find("x:v", ns)
            inline_node = cell.find("x:is/x:t", ns)
            value = ""
            if inline_node is not None and inline_node.text:
                value = inline_node.text
            elif value_node is not None and value_node.text:
                raw_value = value_node.text
                if cell_type == "s":
                    try:
                        value = shared_strings[int(raw_value)]
                    except (ValueError, IndexError):
                        value = raw_value
                else:
                    value = raw_value
            values_by_col[col_index] = value.strip()
        if not values_by_col:
            continue
        cells = [values_by_col.get(index, "") for index in range(max(values_by_col) + 1)]
        if any(cells):
            rows.append(" | ".join(cells))
    return rows


def _xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    if not letters:
        return 0
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _parse_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"## Page {index}\n{text}")
        return "\n\n".join(pages)
    except Exception as exc:
        raise FileParseError("PDF 解析失败，可能是扫描件或加密 PDF") from exc


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
