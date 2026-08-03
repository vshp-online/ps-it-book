#!/usr/bin/env python3
"""Доводит Quarto DOCX до редакторской A4-сборки.

Скрипт использует только стандартную библиотеку: добавляет отсутствующие в
Pandoc заголовки частей, включает обновление полей при открытии документа и
удаляет служебные маркеры ``&`` из многострочных формул ``aligned``.
"""

from pathlib import Path
from xml.sax.saxutils import escape
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


def patch_document(data: bytes) -> tuple[bytes, int, int]:
    alignment_count = data.count(ALIGNMENT_MARKER)
    data = data.replace(ALIGNMENT_MARKER, b"")
    xml = data.decode("utf-8")
    xml, part_count = insert_parts(xml)
    xml = xml.replace(
        'TOC \\o &quot;1-3&quot;',
        'TOC \\o &quot;1-4&quot;',
    )
    return xml.encode("utf-8"), alignment_count, part_count


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

    removed = inserted = 0
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
                data, removed, inserted = patch_document(data)
            elif info.filename == "word/settings.xml":
                data = patch_settings(data)
            archive_out.writestr(info, data)

    print(f"Удалено маркеров aligned: {removed}")
    print(f"Добавлено заголовков частей: {inserted}")
    print(target)


if __name__ == "__main__":
    main()
