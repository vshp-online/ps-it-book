"""Диаграмма симметрической разности двух событий."""

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.patheffects as path_effects
from matplotlib.path import Path
from shapely.affinity import scale, translate
from shapely.geometry import Point

meta = {
    "title": "Симметрическая разность событий A и B",
    "book_ref": "Раздел 1.2 / Рисунок 1.5",
    "description": "Диаграмма Венна для симметрической разности событий A и B",
    "authors": [
        {"name": "П.С. Ткачев", "email": "p.tkachev@vshp.online"},
        {"name": "Н.Н. Зубов", "email": "nick-work@bk.ru"},
    ],
}


def ellipse_as_shapely(x, y, width, height):
    """Создаёт эллипс в форме, пригодной для операций над множествами."""
    circle = Point(0, 0).buffer(1, resolution=256)
    ellipse = scale(circle, width / 2, height / 2)
    return translate(ellipse, xoff=x, yoff=y)


def shape_to_patches(shape, **kwargs):
    """Преобразует геометрию Shapely в один или несколько патчей Matplotlib."""
    if shape.geom_type == 'Polygon':
        coords = shape.exterior.coords[:]
        path = Path(coords, [Path.MOVETO] + [Path.LINETO] * (len(coords) - 2) + [Path.CLOSEPOLY])
        return [PathPatch(path, **kwargs)]
    if shape.geom_type == 'MultiPolygon':
        return [patch for part in shape.geoms for patch in shape_to_patches(part, **kwargs)]
    raise ValueError(f"Неподдерживаемая геометрия: {shape.geom_type}")


def draw(ax):
    """Рисует области, принадлежащие ровно одному из двух событий."""
    formula_box = {'facecolor': 'white', 'edgecolor': 'none', 'pad': 6}
    ax.add_patch(Rectangle((0, 0), 6, 4, edgecolor='black', facecolor='white'))

    a = ellipse_as_shapely(2, 2, 3, 2)
    b = ellipse_as_shapely(4, 2, 3, 2)

    for patch in shape_to_patches(a.symmetric_difference(b), facecolor='lightblue', edgecolor='none'):
        ax.add_patch(patch)
    for shape in [a, b]:
        for patch in shape_to_patches(shape, facecolor='none', edgecolor='black'):
            ax.add_patch(patch)

    for label, x in [('A', 2.0), ('B', 4.0)]:
        text = ax.text(x, 2, label, ha='center', va='center', fontsize=18, fontstyle='italic')
        text.set_path_effects([path_effects.Stroke(linewidth=4, foreground='white'), path_effects.Normal()])
    ax.text(3, 0.55, 'A △ B', ha='center', va='center', fontsize=14, fontstyle='italic', bbox=formula_box)

    ax.set_xlim(0, 6)
    ax.set_ylim(0, 4)
    ax.set_aspect('equal')
    ax.axis('off')
