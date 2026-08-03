#!/usr/bin/env python3
"""Доводит Quarto DOCX до редакторской A4-сборки.

Скрипт использует только стандартную библиотеку: добавляет отсутствующие в
Pandoc заголовки частей, включает обновление полей при открытии документа и
удаляет служебные маркеры ``&`` из многострочных формул ``aligned``.
"""

from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape, unescape
from zipfile import ZIP_DEFLATED, ZipFile
import re
import sys


PARTS = (
    (
        "1. Понятие частости и вероятности случайного события",
        "Часть 1. Случайные события",
    ),
    (
        "9. Случайные величины и шкалы измерения",
        "Часть 2. Случайные величины и статистика продаж",
    ),
    (
        "18. Выборочный метод исследования",
        "Часть 3. Методы математической статистики",
    ),
    (
        "26. Выявление и оценка связи между признаками",
        "Часть 4. Связи между признаками",
    ),
    (
        "35. Временные ряды как бизнес-данные",
        "Часть 5. Динамические ряды и методы их анализа",
    ),
    ("Рекомендуемые источники", "Справочные материалы"),
    ("Appendix A — Ключи к тестовым заданиям", "Приложения"),
)

ALIGNMENT_MARKER = b"<m:r><m:t>&amp;</m:t></m:r>"
DOC_PR_PATTERN = re.compile(
    r"<wp:docPr(?P<attrs>[^>]*?)(?:\s*/>|>(?P<children>.*?)</wp:docPr>)",
    re.DOTALL,
)
TEXT_PATTERN = re.compile(r"<w:t(?:\s+[^>]*)?>(.*?)</w:t>", re.DOTALL)
EXTENT_PATTERN = re.compile(r'<wp:extent\s+cx="(?P<cx>\d+)"\s+cy="(?P<cy>\d+)"\s*/>')
FIGURE_CAPTION_PATTERN = re.compile(r"Рисунок\s+\d+(?:\.\d+)+:\s*(.+)", re.DOTALL)
DECORATIVE_MAX_EMU = 300_000
DECORATIVE_EXTENSION = (
    '<a:extLst><a:ext uri="{C183D7F6-B498-43B3-948B-1728B52AA6E4}">'
    '<adec:decorative '
    'xmlns:adec="http://schemas.microsoft.com/office/drawing/2017/decorative" '
    'val="1"/></a:ext></a:extLst>'
)
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def part_paragraph(title: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="PartTitle"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{escape(title)}</w:t></w:r></w:p>'
    )


def insert_parts(xml: str) -> tuple[str, int]:
    inserted = 0
    for target, title in PARTS:
        if f">{escape(title)}<" in xml:
            continue
        target_xml = escape(target)
        pattern = re.compile(
            r'(<w:p(?:\s+[^>]*)?>'
            r'(?:(?!</w:p>)[\s\S])*?'
            r'<w:pStyle\s+w:val="Heading1"\s*/>'
            r'(?:(?!</w:p>)[\s\S])*?'
            r'<w:t(?:\s+[^>]*)?>'
            + re.escape(target_xml)
            + r'</w:t>(?:(?!</w:p>)[\s\S])*</w:p>)',
        )
        xml, count = pattern.subn(part_paragraph(title) + r"\1", xml, count=1)
        if count != 1:
            raise RuntimeError(f"Не найден целевой заголовок для части: {target}")
        inserted += 1
    return xml, inserted


def set_attribute(attrs: str, name: str, value: str) -> str:
    encoded = escape(value, {'"': "&quot;"})
    pattern = re.compile(rf'(\s{name}=")[^"]*(")')
    if pattern.search(attrs):
        return pattern.sub(rf"\g<1>{encoded}\g<2>", attrs, count=1)
    return attrs.rstrip() + f' {name}="{encoded}"'


def drawing_extent(xml: str, position: int) -> tuple[int, int] | None:
    inline_start = xml.rfind("<wp:inline", 0, position)
    anchor_start = xml.rfind("<wp:anchor", 0, position)
    container_start = max(inline_start, anchor_start)
    if container_start < 0:
        return None
    match = EXTENT_PATTERN.search(xml, container_start, position)
    if not match:
        return None
    return int(match.group("cx")), int(match.group("cy"))


def figure_description(xml: str, position: int) -> str | None:
    table_start = xml.rfind("<w:tbl", 0, position)
    table_end = xml.find("</w:tbl>", position)
    if table_start < 0 or table_end < 0:
        return None
    table_xml = xml[table_start : table_end + len("</w:tbl>")]
    text = "".join(unescape(item) for item in TEXT_PATTERN.findall(table_xml))
    match = FIGURE_CAPTION_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).strip()


def patch_images(xml: str) -> tuple[str, int, int]:
    matches = list(DOC_PR_PATTERN.finditer(xml))
    described = decorative = 0
    for match in reversed(matches):
        attrs = match.group("attrs")
        children = match.group("children") or ""
        extent = drawing_extent(xml, match.start())
        is_decorative = bool(
            extent
            and extent[0] <= DECORATIVE_MAX_EMU
            and extent[1] <= DECORATIVE_MAX_EMU
        )

        if is_decorative:
            if "adec:decorative" not in children:
                children += DECORATIVE_EXTENSION
            replacement = f"<wp:docPr{attrs}>{children}</wp:docPr>"
            decorative += 1
        else:
            description = figure_description(xml, match.start())
            if not description:
                identifier = re.search(r'\sid="([^"]+)"', attrs)
                image_id = identifier.group(1) if identifier else "?"
                raise RuntimeError(
                    f"Не найдена содержательная подпись для изображения {image_id}"
                )
            attrs = set_attribute(attrs, "descr", description)
            replacement = f"<wp:docPr{attrs}>" + children + "</wp:docPr>"
            described += 1

        xml = xml[: match.start()] + replacement + xml[match.end() :]
    return xml, described, decorative


def validate_table_headers(xml: str) -> int:
    root = ElementTree.fromstring(xml)
    namespace = {"w": WORD_NAMESPACE}
    verified = 0
    for table in root.findall(".//w:tbl", namespace):
        rows = table.findall("w:tr", namespace)
        if len(rows) <= 1:
            continue
        first_cells = rows[0].findall("w:tc", namespace)
        if len(first_cells) <= 1:
            continue
        header = rows[0].find("w:trPr/w:tblHeader", namespace)
        if header is None:
            raise RuntimeError(
                "В многорядной таблице отсутствует отметка строки заголовков"
            )
        verified += 1
    return verified


def patch_document(data: bytes) -> tuple[bytes, int, int, int, int, int]:
    alignment_count = data.count(ALIGNMENT_MARKER)
    data = data.replace(ALIGNMENT_MARKER, b"")
    xml = data.decode("utf-8")
    xml, part_count = insert_parts(xml)
    xml, described_count, decorative_count = patch_images(xml)
    xml = xml.replace(
        'TOC \\o &quot;1-3&quot;',
        'TOC \\o &quot;1-4&quot;',
    )
    table_count = validate_table_headers(xml)
    return (
        xml.encode("utf-8"),
        alignment_count,
        part_count,
        described_count,
        decorative_count,
        table_count,
    )


def patch_settings(data: bytes) -> bytes:
    xml = data.decode("utf-8")
    update_pattern = re.compile(r'<w:updateFields\b[^>]*/>')
    if update_pattern.search(xml):
        xml = update_pattern.sub('<w:updateFields w:val="true"/>', xml, count=1)
    else:
        xml = xml.replace(
            "</w:settings>",
            '<w:updateFields w:val="true"/></w:settings>',
        )
    return xml.encode("utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Использование: postprocess-editable-docx.py INPUT OUTPUT")
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    target.parent.mkdir(parents=True, exist_ok=True)

    removed = inserted = described = decorative = tables = 0
    with ZipFile(source, "r") as archive_in, ZipFile(target, "w", ZIP_DEFLATED) as archive_out:
        names = set(archive_in.namelist())
        if "word/document.xml" not in names or "word/settings.xml" not in names:
            raise RuntimeError("В DOCX отсутствуют обязательные части WordprocessingML")
        styles = archive_in.read("word/styles.xml")
        if b'w:styleId="PartTitle"' not in styles:
            raise RuntimeError("В reference DOCX отсутствует стиль Part Title")

        for info in archive_in.infolist():
            data = archive_in.read(info.filename)
            if info.filename == "word/document.xml":
                (
                    data,
                    removed,
                    inserted,
                    described,
                    decorative,
                    tables,
                ) = patch_document(data)
            elif info.filename == "word/settings.xml":
                data = patch_settings(data)
            archive_out.writestr(info, data)

    print(f"Удалено маркеров aligned: {removed}")
    print(f"Добавлено заголовков частей: {inserted}")
    print(f"Описано содержательных изображений: {described}")
    print(f"Помечено декоративных изображений: {decorative}")
    print(f"Проверено таблиц со строкой заголовков: {tables}")
    print(target)


if __name__ == "__main__":
    main()
