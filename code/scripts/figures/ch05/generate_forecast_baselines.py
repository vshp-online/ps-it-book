"""Сравнивает базовые прогнозы на контрольном участке временного ряда.

Запускать из корня репозитория:
    python code/scripts/figures/ch05/generate_forecast_baselines.py
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[4]
SOURCE_PATH = ROOT / "code" / "data" / "monthly-orders-time-series.csv"
RESULT_PATH = ROOT / "code" / "data" / "monthly-orders-forecast-evaluation.csv"
IMAGE_PATH = ROOT / "book" / "images" / "28_forecast_baselines.png"

BLUE = "#2878A9"
DARK_BLUE = "#1F5F7A"
ORANGE = "#D97706"
GREEN = "#3B7A57"
PURPLE = "#7C5C9E"
GRAY = "#718096"
GRID = "#D9DEE3"


@dataclass(frozen=True)
class ForecastEvaluation:
    """Фактические значения и одношаговые прогнозы контрольного периода."""

    dates: list[date]
    actual: np.ndarray
    naive: np.ndarray
    seasonal_naive: np.ndarray
    drift: np.ndarray
    moving_average_3: np.ndarray


def read_series() -> tuple[list[date], np.ndarray]:
    """Читает месяцы и наблюдаемые заказы из основного CSV."""
    with SOURCE_PATH.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    dates = [date.fromisoformat(row["month"]) for row in rows]
    orders = np.array([float(row["orders"]) for row in rows])
    return dates, orders


def evaluate_forecasts(
    dates: list[date], orders: np.ndarray, *, test_start: int = 36
) -> ForecastEvaluation:
    """Строит одношаговые прогнозы, используя только прошлые наблюдения."""
    naive: list[float] = []
    seasonal_naive: list[float] = []
    drift: list[float] = []
    moving_average_3: list[float] = []

    for index in range(test_start, len(orders)):
        history = orders[:index]
        naive.append(history[-1])
        seasonal_naive.append(orders[index - 12])
        drift.append(history[-1] + (history[-1] - history[0]) / (len(history) - 1))
        moving_average_3.append(float(np.mean(history[-3:])))

    return ForecastEvaluation(
        dates=dates[test_start:],
        actual=orders[test_start:],
        naive=np.array(naive),
        seasonal_naive=np.array(seasonal_naive),
        drift=np.array(drift),
        moving_average_3=np.array(moving_average_3),
    )


def write_evaluation(evaluation: ForecastEvaluation) -> None:
    """Сохраняет контрольные значения и прогнозы в CSV."""
    with RESULT_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            (
                "month",
                "actual",
                "naive",
                "seasonal_naive",
                "drift",
                "moving_average_3",
            )
        )
        for values in zip(
            evaluation.dates,
            evaluation.actual,
            evaluation.naive,
            evaluation.seasonal_naive,
            evaluation.drift,
            evaluation.moving_average_3,
            strict=True,
        ):
            month, actual, naive, seasonal, drift, moving_average = values
            writer.writerow(
                (
                    month.isoformat(),
                    f"{actual:.1f}",
                    f"{naive:.1f}",
                    f"{seasonal:.1f}",
                    f"{drift:.1f}",
                    f"{moving_average:.1f}",
                )
            )


def error_metrics(actual: np.ndarray, forecast: np.ndarray) -> tuple[float, ...]:
    """Возвращает MAE, RMSE и MAPE для одного набора прогнозов."""
    errors = actual - forecast
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    mape = float(np.mean(np.abs(errors / actual)) * 100)
    return mae, rmse, mape


def save_figure(
    dates: list[date], orders: np.ndarray, evaluation: ForecastEvaluation
) -> None:
    """Показывает обучающий участок, контрольные значения и четыре прогноза."""
    figure, axis = plt.subplots(figsize=(10.2, 5.5))
    test_start = evaluation.dates[0]

    axis.axvspan(test_start, evaluation.dates[-1], color="#FFF4DB", alpha=0.72)
    axis.plot(
        dates,
        orders,
        color=GRAY,
        linewidth=1.6,
        alpha=0.72,
        label="Фактический ряд",
    )
    axis.plot(
        evaluation.dates,
        evaluation.actual,
        color=DARK_BLUE,
        linewidth=2.4,
        marker="o",
        markersize=4.2,
        label="Факт: контрольный участок",
    )

    forecast_lines = (
        (evaluation.naive, "Наивный", ORANGE, "--"),
        (evaluation.seasonal_naive, "Сезонный наивный", GREEN, ":"),
        (evaluation.drift, "С дрейфом", PURPLE, "-."),
        (evaluation.moving_average_3, "Скользящая средняя, 3", BLUE, "--"),
    )
    for values, label, color, linestyle in forecast_lines:
        axis.plot(
            evaluation.dates,
            values,
            color=color,
            linewidth=1.8,
            linestyle=linestyle,
            label=label,
        )

    axis.axvline(test_start, color=ORANGE, linewidth=1.1)
    axis.text(
        test_start,
        axis.get_ylim()[1],
        "  начало проверки",
        color=ORANGE,
        fontsize=9,
        va="top",
    )
    axis.set(xlabel="Месяц", ylabel="Заказы")
    axis.xaxis.set_major_locator(mdates.YearLocator())
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axis.grid(color=GRID, linewidth=0.75, alpha=0.85)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False, ncol=2, loc="upper left")
    figure.tight_layout()
    figure.savefig(
        IMAGE_PATH,
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.08,
    )
    plt.close(figure)


def main() -> None:
    """Генерирует результаты проверки и сравнительный рисунок."""
    dates, orders = read_series()
    evaluation = evaluate_forecasts(dates, orders)
    write_evaluation(evaluation)
    save_figure(dates, orders, evaluation)

    methods = {
        "naive": evaluation.naive,
        "seasonal_naive": evaluation.seasonal_naive,
        "drift": evaluation.drift,
        "moving_average_3": evaluation.moving_average_3,
    }
    for name, forecast in methods.items():
        mae, rmse, mape = error_metrics(evaluation.actual, forecast)
        print(f"{name}: MAE={mae:.1f}; RMSE={rmse:.1f}; MAPE={mape:.1f}%")


if __name__ == "__main__":
    main()
