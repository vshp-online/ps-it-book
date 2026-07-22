"""Создаёт рабочую книгу LibreOffice Calc для примера из § 1.6.

Запускать из корня репозитория:
    python3 code/scripts/workbooks/ch01/create_interval_estimation_workbook.py
"""

from __future__ import annotations

from math import asin, sin, sqrt
from pathlib import Path
from statistics import NormalDist
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / "code/data/interval-estimation-calc.ods"
CHART_TEMPLATE = Path(__file__).with_name("templates") / "interval-chart-template.ods"
DATA = [
    ("Поисковая реклама", 1200, 48),
    ("Партнёрский канал", 310, 9),
    ("Email-рассылка", 95, 2),
    ("Тестовый канал", 60, 1),
]


def cell(value: str, style: str = "") -> str:
    style_attr = f' table:style-name="{style}"' if style else ""
    return f'<table:table-cell office:value-type="string"{style_attr}><text:p>{value}</text:p></table:table-cell>'


def number(value: float, style: str = "") -> str:
    style_attr = f' table:style-name="{style}"' if style else ""
    return (
        f'<table:table-cell office:value-type="float" office:value="{value}"{style_attr}>'
        f"<text:p>{value}</text:p></table:table-cell>"
    )


def formula(expression: str, value: float, style: str = "") -> str:
    style_attr = f' table:style-name="{style}"' if style else ""
    return (
        f'<table:table-cell table:formula="of:={expression}" office:value-type="float" '
        f'office:value="{value}"{style_attr}><text:p>{value}</text:p></table:table-cell>'
    )


def row(cells: list[str], style: str = "") -> str:
    style_attr = f' table:style-name="{style}"' if style else ""
    return f"<table:table-row{style_attr}>{''.join(cells)}</table:table-row>"


def student_critical(degrees_of_freedom: int) -> float:
    """Приближённое значение двустороннего t-критерия для alpha = 0,05."""
    z = NormalDist().inv_cdf(0.975)
    nu = degrees_of_freedom
    return (
        z
        + (z**3 + z) / (4 * nu)
        + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * nu**2)
        + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * nu**3)
    )


def calculation_row(row_number: int, channel: str, n: int, m: int) -> str:
    p = m / n
    validity = n * p * (1 - p)
    standard_error = sqrt(p * (1 - p) / n)
    critical = student_critical(n - 1)
    traditional_min = p - critical * standard_error
    traditional_max = p + critical * standard_error
    phi = 2 * asin(sqrt(p))
    phi_error = 1 / sqrt(n)
    phi_min = phi - critical * phi_error
    phi_max = phi + critical * phi_error
    fisher_min = sin(phi_min / 2) ** 2
    fisher_max = sin(phi_max / 2) ** 2
    lower = traditional_min if validity > 5 else fisher_min
    upper = traditional_max if validity > 5 else fisher_max
    ref = f"{row_number}"

    return row(
        [
            cell(channel, "input"),
            number(n, "input"),
            number(m, "input"),
            formula(f"[.C{ref}]/[.B{ref}]", p, "percent"),
            formula(f"[.B{ref}]*[.D{ref}]*(1-[.D{ref}])", validity, "number"),
            formula(f"SQRT([.D{ref}]*(1-[.D{ref}])/[.B{ref}])", standard_error, "number"),
            formula(f"TINV(0.05;[.B{ref}]-1)", critical, "number"),
            formula(f"[.D{ref}]-[.G{ref}]*[.F{ref}]", traditional_min, "percent"),
            formula(f"[.D{ref}]+[.G{ref}]*[.F{ref}]", traditional_max, "percent"),
            formula(f"2*ASIN(SQRT([.D{ref}]))", phi, "number"),
            formula(f"1/SQRT([.B{ref}])", phi_error, "number"),
            formula(f"[.J{ref}]-[.G{ref}]*[.K{ref}]", phi_min, "number"),
            formula(f"[.J{ref}]+[.G{ref}]*[.K{ref}]", phi_max, "number"),
            formula(f"SIN([.L{ref}]/2)^2", fisher_min, "percent"),
            formula(f"SIN([.M{ref}]/2)^2", fisher_max, "percent"),
            cell("Традиц." if validity > 5 else "Фишер", "result"),
            formula(
                f"IF([.E{ref}]>5;[.H{ref}];[.N{ref}])", lower, "percent"
            ),
            formula(
                f"IF([.E{ref}]>5;[.I{ref}];[.O{ref}])", upper, "percent"
            ),
        ]
    )


def make_fods() -> str:
    headers = [
        "Канал",
        "n",
        "m",
        "p*",
        "Критерий применимости",
        "СКО p*",
        "t(0,05)",
        "Нижняя граница: традиц.",
        "Верхняя граница: традиц.",
        "φ",
        "СКО φ",
        "Нижняя граница φ",
        "Верхняя граница φ",
        "Нижняя граница: Фишер",
        "Верхняя граница: Фишер",
        "Метод",
        "Нижн. 95%",
        "Верхн. 95%",
    ]
    widths = ["4.0cm", "1.2cm", "1.2cm", "1.6cm"] + ["2.2cm"] * 11 + ["2.2cm", "2.1cm", "2.1cm"]
    columns = "".join(
        f'<table:table-column table:style-name="col{index}"'
        f'{" table:visibility=" + chr(34) + "collapse" + chr(34) if 5 <= index <= 15 else ""}/>'
        for index, _ in enumerate(widths, start=1)
    )
    column_styles = "".join(
        f'<style:style style:name="col{index}" style:family="table-column">'
        f'<style:table-column-properties style:column-width="{width}"/>'
        f"</style:style>"
        for index, width in enumerate(widths, start=1)
    )
    data_rows = "".join(
        calculation_row(index, *values) for index, values in enumerate(DATA, start=2)
    )
    header_cells = "".join(cell(header, "header") for header in headers)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.spreadsheet">
  <office:automatic-styles>
    {column_styles}
    <style:style style:name="header-row" style:family="table-row"><style:table-row-properties style:row-height="0.7cm" style:use-optimal-row-height="false"/></style:style>
    <style:style style:name="header" style:family="table-cell"><style:table-cell-properties fo:background-color="#D9EAF0" fo:border="0.06pt solid #6B7A80" style:vertical-align="middle"/><style:paragraph-properties fo:text-align="center"/><style:text-properties fo:font-weight="bold" fo:font-size="9pt"/></style:style>
    <style:style style:name="input" style:family="table-cell"><style:table-cell-properties fo:background-color="#FFF4CC" fo:border="0.06pt solid #A0A0A0"/></style:style>
    <style:style style:name="number" style:family="table-cell"><style:table-cell-properties fo:border="0.06pt solid #A0A0A0"/><style:text-properties fo:font-size="9pt"/></style:style>
    <style:style style:name="percent" style:family="table-cell" style:data-style-name="percent2"><style:table-cell-properties fo:border="0.06pt solid #A0A0A0"/></style:style>
    <style:style style:name="result" style:family="table-cell"><style:table-cell-properties fo:background-color="#E8F1E2" fo:border="0.06pt solid #A0A0A0"/></style:style>
    <number:percentage-style style:name="percent2"><number:number number:decimal-places="3" number:min-decimal-places="3"/><number:text>%</number:text></number:percentage-style>
  </office:automatic-styles>
  <office:body>
    <office:spreadsheet>
      <table:table table:name="Расчёт">
        {columns}
        {row([header_cells], "header-row")}
        {data_rows}
      </table:table>
    </office:spreadsheet>
  </office:body>
</office:document>
'''


def chart_sheet() -> str:
    """Возвращает связанный с расчётами лист данных для диаграммы."""
    chart_rows = []
    short_names = ["Поиск", "Партнёры", "Email", "Тест"]
    for row_number, (short_name, (_, n, m)) in enumerate(
        zip(short_names, DATA, strict=True), start=2
    ):
        p = m / n
        validity = n * p * (1 - p)
        critical = student_critical(n - 1)
        standard_error = sqrt(p * (1 - p) / n)
        traditional_min = p - critical * standard_error
        traditional_max = p + critical * standard_error
        phi = 2 * asin(sqrt(p))
        phi_error = 1 / sqrt(n)
        fisher_min = sin((phi - critical * phi_error) / 2) ** 2
        fisher_max = sin((phi + critical * phi_error) / 2) ** 2
        lower = traditional_min if validity > 5 else fisher_min
        upper = traditional_max if validity > 5 else fisher_max
        chart_rows.append(
            "<table:table-row>"
            f'<table:table-cell office:value-type="string"><text:p>{short_name}</text:p></table:table-cell>'
            f'<table:table-cell table:style-name="percent" table:formula="of:=[Расчёт.R{row_number}]" office:value-type="percentage" office:value="{upper}"><text:p>{upper}</text:p></table:table-cell>'
            f'<table:table-cell table:style-name="percent" table:formula="of:=[Расчёт.Q{row_number}]" office:value-type="percentage" office:value="{lower}"><text:p>{lower}</text:p></table:table-cell>'
            f'<table:table-cell table:style-name="percent" table:formula="of:=[Расчёт.D{row_number}]" office:value-type="percentage" office:value="{p}"><text:p>{p}</text:p></table:table-cell>'
            "</table:table-row>"
        )

    return f'''
<table:table table:name="Диаграмма">
  <table:table-column table:style-name="col1"/>
  <table:table-column table:style-name="col16" table:number-columns-repeated="3"/>
  <table:table-row table:style-name="header-row">
    <table:table-cell table:style-name="header" office:value-type="string"><text:p>Канал</text:p></table:table-cell>
    <table:table-cell table:style-name="header" office:value-type="string"><text:p>Верхн. 95%</text:p></table:table-cell>
    <table:table-cell table:style-name="header" office:value-type="string"><text:p>Нижн. 95%</text:p></table:table-cell>
    <table:table-cell table:style-name="header" office:value-type="string"><text:p>Частость</text:p></table:table-cell>
  </table:table-row>
  {''.join(chart_rows)}
  <table:table-row>
    <table:table-cell>
      <draw:frame table:end-cell-address="Диаграмма.H30" table:end-x="0cm" table:end-y="0cm" draw:z-index="0" draw:name="Chart" draw:style-name="gr1" draw:text-style-name="P1" svg:width="15.287cm" svg:height="10.053cm" svg:x="0cm" svg:y="0cm">
        <draw:object draw:notify-on-update-of-ranges="Диаграмма.A2:Диаграмма.A5 Диаграмма.B2:Диаграмма.B5 Диаграмма.C2:Диаграмма.C5 Диаграмма.D2:Диаграмма.D5" xlink:href="./Object 1" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"><loext:p/></draw:object>
        <draw:image xlink:href="./ObjectReplacements/Object 1" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/>
      </draw:frame>
    </table:table-cell>
  </table:table-row>
</table:table>
'''


def add_chart(workbook: Path, temporary_directory: Path) -> None:
    """Добавляет в ODS связанный лист и нативную биржевую диаграмму Calc."""
    output = temporary_directory / "interval-estimation-with-chart.ods"
    graphic_styles = (
        '<style:style style:name="gr1" style:family="graphic" style:parent-style-name="Default">'
        '<style:graphic-properties draw:stroke="none" svg:stroke-width="0cm" draw:fill="none" '
        'draw:textarea-horizontal-align="center" draw:textarea-vertical-align="top" '
        'draw:auto-grow-height="false" fo:padding-top="0.125cm" fo:padding-bottom="0.125cm" '
        'fo:padding-left="0.25cm" fo:padding-right="0.25cm" fo:wrap-option="wrap" '
        'draw:ole-draw-aspect="1"/></style:style>'
        '<style:style style:name="P1" style:family="paragraph">'
        '<style:paragraph-properties fo:text-align="left"/></style:style>'
    )
    manifest_entries = '''
 <manifest:file-entry manifest:full-path="Object 1/" manifest:media-type="application/vnd.oasis.opendocument.chart"/>
 <manifest:file-entry manifest:full-path="Object 1/meta.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="Object 1/styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="Object 1/content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="ObjectReplacements/Object 1" manifest:media-type="application/vnd.sun.star.oleobject"/>
'''

    with ZipFile(workbook) as source, ZipFile(CHART_TEMPLATE) as template, ZipFile(output, "w") as destination:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "content.xml":
                content = data.decode("utf-8")
                content = content.replace(
                    "</office:automatic-styles>",
                    graphic_styles + "</office:automatic-styles>",
                )
                content = content.replace(
                    "<table:named-expressions/>",
                    chart_sheet() + "<table:named-expressions/>",
                )
                data = content.encode("utf-8")
            elif item.filename == "META-INF/manifest.xml":
                manifest = data.decode("utf-8").replace(
                    "</manifest:manifest>",
                    manifest_entries + "</manifest:manifest>",
                )
                data = manifest.encode("utf-8")
            compression = ZIP_STORED if item.filename == "mimetype" else ZIP_DEFLATED
            destination.writestr(item, data, compress_type=compression)

        for name in (
            "Object 1/meta.xml",
            "Object 1/styles.xml",
            "Object 1/content.xml",
            "ObjectReplacements/Object 1",
        ):
            data = template.read(name)
            if name == "Object 1/content.xml":
                chart = data.decode("utf-8")
                chart = chart.replace(
                    "Частота заказа и 95%-ный доверительный интервал",
                    "Частость и 95%-ные интервалы",
                )
                chart = chart.replace(
                    'fo:font-size="18pt" fo:font-weight="bold"',
                    'fo:font-size="11pt" fo:font-weight="bold"',
                ).replace(
                    'style:font-size-asian="18pt"',
                    'style:font-size-asian="11pt"',
                ).replace(
                    'style:font-size-complex="18pt"',
                    'style:font-size-complex="11pt"',
                )
                chart = chart.replace(
                    '<style:graphic-properties draw:stroke="none" svg:stroke-color="#99ccff"/>',
                    '<style:graphic-properties draw:stroke="solid" svg:stroke-width="0.06cm" svg:stroke-color="#1d4e60"/>',
                )
                data = chart.encode("utf-8")
            destination.writestr(name, data, compress_type=ZIP_DEFLATED)

    output.replace(workbook)


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        fods_path = temp_path / "interval-estimation-calc.fods"
        fods_path.write_text(make_fods(), encoding="utf-8")
        run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "ods",
                "--outdir",
                str(OUTPUT.parent),
                str(fods_path),
            ],
            check=True,
        )
        add_chart(OUTPUT, temp_path)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
