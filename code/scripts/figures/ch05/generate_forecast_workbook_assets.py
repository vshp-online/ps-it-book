"""Создаёт QR-код и иллюстрации из рабочей книги прогнозирования.

Запускать из корня репозитория:
    python code/scripts/figures/ch05/generate_forecast_workbook_assets.py
"""

from __future__ import annotations

from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from urllib.request import urlopen

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "code/data/monthly-orders-forecast-calc.ods"
QR_OUTPUT = ROOT / "book/images/29_time-series-forecast-calc-qr.png"
PREVIEW_OUTPUT = ROOT / "book/images/30_time-series-forecast-calc-preview.png"
CHART_OUTPUT = ROOT / "book/images/31_time-series-forecast-calc-chart.png"
TARGET = (
    "https://github.com/vshp-online/ps-it-book/"
    "blob/main/code/data/monthly-orders-forecast-calc.ods"
)


def trim_white_canvas(image: Image.Image, padding: int = 16) -> Image.Image:
    """Обрезает белый холст, сохраняя равное поле вокруг содержимого."""
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, "white")
    bounds = ImageChops.difference(rgb, background).getbbox()
    if bounds is None:
        raise RuntimeError("В экспортированном фрагменте не найдено содержимое")
    left, top, right, bottom = bounds
    return rgb.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(rgb.width, right + padding),
            min(rgb.height, bottom + padding),
        )
    )


def create_qr_code() -> None:
    """Сохраняет QR-код со ссылкой на рабочую книгу в GitHub."""
    query = urlencode({"size": "320x320", "format": "png", "data": TARGET})
    url = f"https://api.qrserver.com/v1/create-qr-code/?{query}"
    with urlopen(url, timeout=30) as response:
        QR_OUTPUT.write_bytes(response.read())


def export_calc_assets() -> None:
    """Экспортирует лист проверки Calc и вырезает таблицу и диаграмму."""
    with TemporaryDirectory(dir=ROOT / "tmp") as temporary:
        temporary_path = Path(temporary)
        profile = temporary_path / "lo-profile"
        profile.mkdir()
        run(
            [
                "soffice",
                "--headless",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temporary_path),
                str(WORKBOOK),
            ],
            check=True,
        )
        pdf_path = temporary_path / f"{WORKBOOK.stem}.pdf"
        prefix = temporary_path / "forecast-workbook"
        run(
            [
                "pdftoppm",
                "-f",
                "3",
                "-l",
                "3",
                "-png",
                "-r",
                "180",
                str(pdf_path),
                str(prefix),
            ],
            check=True,
        )
        page_path = temporary_path / "forecast-workbook-3.png"
        with Image.open(page_path) as page:
            width, height = page.size
            preview = page.crop((0, 0, width, round(height * 0.47)))
            chart = page.crop(
                (0, round(height * 0.45), width, round(height * 0.88))
            )
            trim_white_canvas(preview).save(PREVIEW_OUTPUT)
            trim_white_canvas(chart).save(CHART_OUTPUT)


def main() -> None:
    """Обновляет все иллюстрации, связанные с рабочей книгой."""
    (ROOT / "tmp").mkdir(exist_ok=True)
    QR_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    create_qr_code()
    export_calc_assets()
    for output in (QR_OUTPUT, PREVIEW_OUTPUT, CHART_OUTPUT):
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
