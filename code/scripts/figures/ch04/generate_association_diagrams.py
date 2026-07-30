"""Создаёт вводные диаграммы для раздела о связи между признаками.

Запускать из корня репозитория:
    python code/scripts/figures/ch04/generate_association_diagrams.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[4]
OUTPUT_DIR = ROOT / "book" / "images"
BLUE = "#2878A9"
DARK_BLUE = "#1F5F7A"
LIGHT_BLUE = "#DCEEF7"
ORANGE = "#D97706"
TEXT = "#263238"
GRID = "#D9DEE3"


def save_scatterplot() -> None:
    """Показывает связь нагрузки поддержки со временем первого ответа."""
    random = np.random.default_rng(42)
    load = np.sort(random.uniform(8, 58, 34))
    response = 2.4 + 0.23 * load + random.normal(0, 1.45, load.size)
    incident_load = 34
    incident_response = 20.4

    figure, axis = plt.subplots(figsize=(9.2, 5.2))
    axis.scatter(
        load,
        response,
        s=52,
        color=BLUE,
        edgecolor="white",
        linewidth=0.8,
        alpha=0.9,
        label="Обычные интервалы",
    )
    axis.scatter(
        [incident_load],
        [incident_response],
        s=82,
        color=ORANGE,
        edgecolor="white",
        linewidth=0.9,
        zorder=3,
        label="Инцидент",
    )
    axis.annotate(
        "Сбой системы маршрутизации",
        xy=(incident_load, incident_response),
        xytext=(39, 21.8),
        arrowprops={"arrowstyle": "->", "color": ORANGE, "linewidth": 1.2},
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": ORANGE,
            "linewidth": 0.8,
        },
        color=TEXT,
        fontsize=10,
    )

    axis.set(
        xlabel="Нагрузка, обращений в час",
        ylabel="Медианное время первого ответа, мин",
        xlim=(5, 61),
        ylim=(2, 24),
    )
    axis.grid(color=GRID, linewidth=0.8, alpha=0.85)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False, loc="upper left")
    figure.tight_layout()
    figure.savefig(
        OUTPUT_DIR / "21_support_load_scatterplot.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.08,
    )
    plt.close(figure)


def add_branch(
    axis,
    *,
    root_x: float,
    end_x: float,
    end_y: float,
    category: str,
    causes: tuple[str, str],
) -> None:
    """Добавляет одну крупную ветвь диаграммы Исикавы."""
    axis.plot(
        [root_x, end_x],
        [0, end_y],
        color=DARK_BLUE,
        linewidth=2,
        solid_capstyle="round",
    )
    axis.text(
        end_x,
        end_y,
        category,
        ha="center",
        va="center",
        fontsize=10.5,
        weight="bold",
        color=TEXT,
        bbox={
            "boxstyle": "round,pad=0.42",
            "facecolor": LIGHT_BLUE,
            "edgecolor": BLUE,
            "linewidth": 0.9,
        },
    )

    direction = 1 if end_y > 0 else -1
    for fraction, cause in zip((0.38, 0.66), causes):
        x = root_x + fraction * (end_x - root_x)
        y = fraction * end_y
        tick_x = x - 0.55
        tick_y = y + direction * 0.45
        axis.plot(
            [x, tick_x],
            [y, tick_y],
            color="#718096",
            linewidth=1.1,
        )
        axis.text(
            tick_x - 0.08,
            tick_y + direction * 0.04,
            cause,
            ha="right",
            va="bottom" if direction > 0 else "top",
            fontsize=8.7,
            color=TEXT,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
            },
        )


def save_ishikawa_diagram() -> None:
    """Строит диаграмму возможных причин долгого ответа поддержки."""
    figure, axis = plt.subplots(figsize=(11.4, 6.2))
    axis.set_xlim(0, 12)
    axis.set_ylim(-3.4, 3.4)
    axis.axis("off")

    axis.annotate(
        "",
        xy=(9.6, 0),
        xytext=(0.75, 0),
        arrowprops={
            "arrowstyle": "-|>",
            "color": DARK_BLUE,
            "linewidth": 2.8,
            "mutation_scale": 18,
        },
    )
    axis.text(
        10.45,
        0,
        "Долгое время\nпервого ответа",
        ha="center",
        va="center",
        fontsize=12,
        weight="bold",
        color=TEXT,
        bbox={
            "boxstyle": "round,pad=0.55",
            "facecolor": "#FFF4DB",
            "edgecolor": ORANGE,
            "linewidth": 1.2,
        },
    )

    branches = (
        (3.0, 1.25, 2.45, "Нагрузка", ("пик обращений", "рекламная кампания")),
        (5.8, 4.05, 2.45, "Команда", ("нехватка смены", "новые сотрудники")),
        (8.45, 6.75, 2.45, "Процесс", ("ручная маршрутизация", "долгая эскалация")),
        (3.65, 1.9, -2.45, "Система", ("медленная CRM", "сбой интеграции")),
        (6.35, 4.6, -2.45, "Данные", ("неполный профиль", "нет истории клиента")),
        (8.95, 7.25, -2.45, "Запросы", ("неясная формулировка", "сложный случай")),
    )
    for root_x, end_x, end_y, category, causes in branches:
        add_branch(
            axis,
            root_x=root_x,
            end_x=end_x,
            end_y=end_y,
            category=category,
            causes=causes,
        )

    figure.tight_layout()
    figure.savefig(
        OUTPUT_DIR / "22_support_ishikawa_diagram.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.12,
    )
    plt.close(figure)


def main() -> None:
    """Создаёт обе иллюстрации."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_scatterplot()
    save_ishikawa_diagram()
    print("book/images/21_support_load_scatterplot.png")
    print("book/images/22_support_ishikawa_diagram.png")


if __name__ == "__main__":
    main()
