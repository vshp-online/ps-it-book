"""Настраивает печатные области ODS без запуска LibreOfficePython.

Запускать из корня репозитория после обновления рабочей книги:
    python code/scripts/workbooks/ch05/configure_forecast_workbook_print.py
"""

from __future__ import annotations

import copy
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "code/data/monthly-orders-forecast-calc.ods"

NAMESPACES = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}
for namespace_prefix, uri in NAMESPACES.items():
    ET.register_namespace(namespace_prefix, uri)


def attribute(prefix: str, name: str) -> str:
    """Возвращает полное имя XML-атрибута."""
    return f"{{{NAMESPACES[prefix]}}}{name}"


def configure_styles(source: bytes) -> bytes:
    """Добавляет отдельные альбомные стили печати для трёх листов."""
    root = ET.fromstring(source)
    automatic_styles = root.find("office:automatic-styles", NAMESPACES)
    if automatic_styles is None:
        raise RuntimeError("В styles.xml не найден раздел автоматических стилей")

    base_layout = next(
        (
            layout
            for layout in automatic_styles.findall("style:page-layout", NAMESPACES)
            if layout.get(attribute("style", "name")) == "Mpm3"
        ),
        None,
    )
    if base_layout is None:
        raise RuntimeError("В styles.xml не найден базовый стиль страницы Mpm3")

    layouts = {
        "Mpm4": "2",
        "Mpm5": "1",
        "Mpm6": "1",
    }
    for layout_name, pages_y in layouts.items():
        layout = copy.deepcopy(base_layout)
        layout.set(attribute("style", "name"), layout_name)
        properties = layout.find("style:page-layout-properties", NAMESPACES)
        if properties is None:
            raise RuntimeError(f"В стиле {layout_name} нет параметров страницы")
        properties.attrib.pop(attribute("style", "scale-to"), None)
        properties.set(attribute("fo", "page-width"), "29.7cm")
        properties.set(attribute("fo", "page-height"), "21.001cm")
        properties.set(attribute("style", "print-orientation"), "landscape")
        properties.set(attribute("fo", "margin-top"), "1.143cm")
        properties.set(attribute("fo", "margin-bottom"), "1.143cm")
        properties.set(attribute("fo", "margin-left"), "0.889cm")
        properties.set(attribute("fo", "margin-right"), "0.889cm")
        properties.set(attribute("style", "scale-to-X"), "1")
        properties.set(attribute("style", "scale-to-Y"), pages_y)
        automatic_styles.append(layout)

    master_styles = root.find("office:master-styles", NAMESPACES)
    if master_styles is None:
        raise RuntimeError("В styles.xml не найден раздел мастер-страниц")
    page_layout_by_style = {
        "PageStyle_5f_Прогнозы": "Mpm4",
        "PageStyle_5f_Проверка": "Mpm5",
        "PageStyle_5f_Ошибки": "Mpm6",
    }
    for master_page in master_styles.findall("style:master-page", NAMESPACES):
        style_name = master_page.get(attribute("style", "name"))
        if style_name in page_layout_by_style:
            master_page.set(
                attribute("style", "page-layout-name"),
                page_layout_by_style[style_name],
            )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def configure_print_ranges(source: bytes) -> bytes:
    """Добавляет печатные области без пересериализации формул OpenFormula."""
    text = source.decode("utf-8")
    print_ranges = {
        "Прогнозы": "Прогнозы.A1:Прогнозы.G52",
        "Проверка": "Проверка.A1:Проверка.K42",
        "Ошибки": "Ошибки.A1:Ошибки.R16",
    }
    seen: set[str] = set()
    for name, print_range in print_ranges.items():
        pattern = re.compile(
            rf'(<table:table\b(?=[^>]*\btable:name="{re.escape(name)}")[^>]*)(>)'
        )

        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"В content.xml не найден лист: {name}")
        tag = match.group(1)
        existing = re.compile(r'\s+table:print-ranges="[^"]*"')
        if existing.search(tag):
            tag = existing.sub(f' table:print-ranges="{print_range}"', tag)
        else:
            tag += f' table:print-ranges="{print_range}"'
        replacement = tag + match.group(2)
        text = text[: match.start()] + replacement + text[match.end() :]
        seen.add(name)
    missing = set(print_ranges) - seen
    if missing:
        raise RuntimeError(f"В content.xml не найдены листы: {sorted(missing)}")
    return text.encode("utf-8")


def rewrite_workbook() -> None:
    """Перезаписывает только styles.xml и content.xml внутри ODS."""
    temporary = WORKBOOK.with_suffix(".ods.tmp")
    with ZipFile(WORKBOOK, "r") as source, ZipFile(temporary, "w") as target:
        for member in source.infolist():
            data = source.read(member.filename)
            if member.filename == "styles.xml":
                data = configure_styles(data)
            elif member.filename == "content.xml":
                data = configure_print_ranges(data)
            target.writestr(member, data)
    os.replace(temporary, WORKBOOK)


def main() -> None:
    """Обновляет настройки печати и проверяет целостность архива."""
    rewrite_workbook()
    with ZipFile(WORKBOOK, "r") as workbook:
        damaged = workbook.testzip()
    if damaged is not None:
        raise RuntimeError(f"Повреждён файл внутри ODS: {damaged}")
    print(WORKBOOK.relative_to(ROOT))


if __name__ == "__main__":
    main()
