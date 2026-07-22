"""Создаёт иллюстрацию таблицы и диаграммы Calc из § 1.6.

Запускать из корня репозитория:
    python3 code/scripts/figures/ch01/generate_interval_workbook_chart.py
"""

from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "code/data/interval-estimation-calc.ods"
OUTPUT = ROOT / "book/images/11_interval-estimation-calc-chart.png"


def trim(image: Image.Image, padding: int = 12) -> Image.Image:
    """Обрезает белые поля вокруг таблицы и диаграммы."""
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, "white")
    bounds = ImageChops.difference(rgb, background).getbbox()
    if bounds is None:
        raise RuntimeError("На втором листе не найдены таблица и диаграмма")
    left, top, right, bottom = bounds
    return rgb.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(rgb.width, right + padding),
            min(rgb.height, bottom + padding),
        )
    )


def main() -> None:
    """Экспортирует второй лист Calc и сохраняет компактную иллюстрацию."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_path),
                str(WORKBOOK),
            ],
            check=True,
        )
        pdf_path = temp_path / f"{WORKBOOK.stem}.pdf"
        prefix = temp_path / "worksheet"
        run(
            [
                "pdftoppm",
                "-f",
                "2",
                "-l",
                "2",
                "-png",
                "-r",
                "150",
                str(pdf_path),
                str(prefix),
            ],
            check=True,
        )
        page = Image.open(temp_path / "worksheet-2.png")
        preview = trim(page.crop((70, 70, 1100, 1100)))
        preview.save(OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
