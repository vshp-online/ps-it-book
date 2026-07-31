"""Создаёт данные и рисунок для раздела о компонентах временного ряда.

Запускать из корня репозитория:
    python code/scripts/figures/ch05/generate_time_series_components.py
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
DATA_PATH = ROOT / "code" / "data" / "monthly-orders-time-series.csv"
IMAGE_PATH = ROOT / "book" / "images" / "27_time_series_components.png"

BLUE = "#2878A9"
DARK_BLUE = "#1F5F7A"
ORANGE = "#D97706"
GREEN = "#3B7A57"
GRAY = "#718096"
TEXT = "#263238"
GRID = "#D9DEE3"


@dataclass(frozen=True)
class TimeSeriesComponents:
    """Наблюдаемый временной ряд и его известные учебные компоненты."""

    dates: list[date]
    orders: np.ndarray
    trend: np.ndarray
    seasonality: np.ndarray
    cycle: np.ndarray
    random: np.ndarray


def build_series() -> TimeSeriesComponents:
    """Возвращает синтетический месячный ряд с известными компонентами."""
    periods = 48
    time = np.arange(periods)
    dates = [date(2022 + index // 12, index % 12 + 1, 1) for index in time]

    trend = 1050 + 14 * time
    monthly_pattern = np.array(
        [-140, -100, -50, -10, 20, 10, -30, -20, 30, 70, 100, 120],
        dtype=float,
    )
    seasonality = np.resize(monthly_pattern, periods)
    cycle = 65 * np.sin(2 * np.pi * time / 30)
    random = np.random.default_rng(20260731).normal(0, 34, periods)
    orders = np.rint(trend + seasonality + cycle + random).astype(int)
    return TimeSeriesComponents(
        dates=dates,
        orders=orders,
        trend=trend,
        seasonality=seasonality,
        cycle=cycle,
        random=random,
    )


def write_data(series: TimeSeriesComponents) -> None:
    """Сохраняет наблюдаемый ряд и известные учебные компоненты в CSV."""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ("month", "orders", "trend", "seasonality", "cycle", "random")
        )
        for values in zip(
            series.dates,
            series.orders,
            series.trend,
            series.seasonality,
            series.cycle,
            series.random,
            strict=True,
        ):
            month, observed, trend_value, seasonal, cycle_value, residual = values
            writer.writerow(
                (
                    month.isoformat(),
                    int(observed),
                    f"{trend_value:.1f}",
                    f"{seasonal:.1f}",
                    f"{cycle_value:.1f}",
                    f"{residual:.1f}",
                )
            )


def style_axis(axis: plt.Axes, *, zero_line: bool = False) -> None:
    """Применяет общий стиль к панели рисунка."""
    axis.grid(color=GRID, linewidth=0.75, alpha=0.85)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(colors=TEXT, labelsize=8.5)
    if zero_line:
        axis.axhline(0, color=GRAY, linewidth=0.9)


def save_figure(series: TimeSeriesComponents) -> None:  # pylint: disable=too-many-locals
    """Строит наблюдаемый ряд и четыре известные учебные компоненты."""
    figure = plt.figure(figsize=(10.2, 8.6))
    grid = figure.add_gridspec(3, 2, height_ratios=(1.25, 1, 1))
    observed_axis = figure.add_subplot(grid[0, :])
    trend_axis = figure.add_subplot(grid[1, 0], sharex=observed_axis)
    seasonal_axis = figure.add_subplot(grid[1, 1], sharex=observed_axis)
    cycle_axis = figure.add_subplot(grid[2, 0], sharex=observed_axis)
    random_axis = figure.add_subplot(grid[2, 1], sharex=observed_axis)

    observed_axis.plot(series.dates, series.orders, color=DARK_BLUE, linewidth=2.0)
    observed_axis.scatter(
        series.dates,
        series.orders,
        s=19,
        color=BLUE,
        edgecolor="white",
        linewidth=0.45,
        zorder=3,
    )
    observed_axis.set_title("Наблюдаемый ряд", loc="left", weight="bold")
    observed_axis.set_ylabel("Заказы")
    style_axis(observed_axis)

    panels = (
        (trend_axis, series.trend, "Тренд", BLUE, False),
        (seasonal_axis, series.seasonality, "Сезонность", ORANGE, True),
        (cycle_axis, series.cycle, "Длительное колебание", GREEN, True),
        (random_axis, series.random, "Случайный остаток", GRAY, True),
    )
    for axis, values, title, color, zero_line in panels:
        axis.plot(series.dates, values, color=color, linewidth=1.8)
        axis.set_title(title, loc="left", weight="bold", fontsize=10)
        style_axis(axis, zero_line=zero_line)

    for axis in (observed_axis, trend_axis, seasonal_axis, cycle_axis, random_axis):
        axis.xaxis.set_major_locator(mdates.YearLocator())
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for axis in (observed_axis, trend_axis, seasonal_axis):
        axis.tick_params(labelbottom=False)

    figure.tight_layout(h_pad=1.25, w_pad=1.2)
    IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        IMAGE_PATH,
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.08,
    )
    plt.close(figure)


def main() -> None:
    """Генерирует CSV и PNG из одного набора компонентов."""
    series = build_series()
    write_data(series)
    save_figure(series)


if __name__ == "__main__":
    main()
