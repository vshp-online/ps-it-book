"""Создаёт QR-код и иллюстрацию диаграммы из рабочей книги регрессии.

Запускать из корня репозитория:
    python code/scripts/figures/ch04/generate_regression_workbook_assets.py
"""

from pathlib import Path
from subprocess import check_output, run
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from urllib.request import urlopen

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "code/data/support-regression-calc.ods"
QR_OUTPUT = ROOT / "book/images/24_support-regression-calc-qr.png"
CHART_OUTPUT = ROOT / "book/images/25_support-regression-calc-chart.png"
TARGET = (
    "https://github.com/vshp-online/ps-it-book/"
    "blob/main/code/data/support-regression-calc.ods"
)


def trim_white_canvas(image: Image.Image, padding: int = 18) -> Image.Image:
    """Обрезает белый холст, сохраняя одинаковое поле вокруг диаграммы."""
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, "white")
    bounds = ImageChops.difference(rgb, background).getbbox()
    if bounds is None:
        raise RuntimeError("В экспортированном листе не найдена диаграмма")
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
    query = urlencode({"size": "360x360", "format": "png", "data": TARGET})
    url = f"https://api.qrserver.com/v1/create-qr-code/?{query}"
    with urlopen(url, timeout=30) as response:
        QR_OUTPUT.write_bytes(response.read())


def export_calc_chart() -> None:
    """Экспортирует в PNG отдельный лист с нативной диаграммой Calc."""
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
        info = check_output(["pdfinfo", str(pdf_path)], text=True)
        pages = int(
            next(line.split(":", 1)[1] for line in info.splitlines() if line.startswith("Pages:"))
        )
        prefix = temporary_path / "regression-chart"
        run(
            [
                "pdftoppm",
                "-f",
                str(pages),
                "-l",
                str(pages),
                "-png",
                "-r",
                "180",
                str(pdf_path),
                str(prefix),
            ],
            check=True,
        )
        with Image.open(temporary_path / f"regression-chart-{pages}.png") as page:
            trim_white_canvas(page).save(CHART_OUTPUT)


def main() -> None:
    """Обновляет связанные с рабочей книгой изображения."""
    (ROOT / "tmp").mkdir(exist_ok=True)
    QR_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    create_qr_code()
    export_calc_chart()
    for output in (QR_OUTPUT, CHART_OUTPUT):
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
