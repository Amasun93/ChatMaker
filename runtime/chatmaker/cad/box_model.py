"""Small parameterized rectangular finger-joint box model.

The model deliberately emits only orthogonal closed contours.  It is an
independent ChatMaker implementation; public box generators were used only to
confirm the responsibilities of thickness, finger/space and fit compensation.
"""

from __future__ import annotations

import math
from typing import Any


PANEL_LABELS = {
    "top": "顶板",
    "bottom": "底板",
    "front": "前板",
    "back": "后板",
    "left": "左板",
    "right": "右板",
}

# Edge order is top, right, bottom, left while walking clockwise.
EDGE_CONTRACT = {
    "top": (("length", "male"), ("width", "male"), ("length", "male"), ("width", "male")),
    "bottom": (("length", "male"), ("width", "male"), ("length", "male"), ("width", "male")),
    "front": (("length", "female"), ("height", "male"), ("length", "female"), ("height", "male")),
    "back": (("length", "female"), ("height", "male"), ("length", "female"), ("height", "male")),
    "left": (("width", "female"), ("height", "female"), ("width", "female"), ("height", "female")),
    "right": (("width", "female"), ("height", "female"), ("width", "female"), ("height", "female")),
}


def panels(g: dict[str, Any]) -> list[dict[str, Any]]:
    """Lay out all enabled box faces in a compact two-column sheet."""

    width = float(g["outer_width"])
    depth = float(g["outer_depth"])
    height = float(g["outer_height"])
    gap = max(12.0, float(g["material_thickness"]) * 5)
    result: list[dict[str, Any]] = []

    x = gap
    if g["include_top"]:
        result.append(_panel("top", x, gap, width, depth))
        x += width + gap
    if g["include_bottom"]:
        result.append(_panel("bottom", x, gap, width, depth))

    side_y = depth + gap * 3 if result else gap
    result.extend(
        [
            _panel("front", gap, side_y, width, height),
            _panel("back", gap + width + gap, side_y, width, height),
            _panel("left", gap, side_y + height + gap * 2, depth, height),
            _panel("right", gap + depth + gap, side_y + height + gap * 2, depth, height),
        ]
    )
    return result


def _panel(name: str, x: float, y: float, width: float, depth: float) -> dict[str, Any]:
    return {
        "name": name,
        "label": PANEL_LABELS[name],
        "x": x,
        "y": y,
        "width": width,
        "depth": depth,
        "edges": [
            {"axis": axis, "polarity": polarity}
            for axis, polarity in EDGE_CONTRACT[name]
        ],
    }


def finger_intervals(
    length: float,
    target: float,
    thickness: float,
    polarity: str,
    compensation: float,
) -> list[tuple[float, float]]:
    """Return centered finger/groove intervals along one edge.

    Positive compensation expands male fingers and contracts female grooves.
    End margins remain symmetric and at least one material thickness whenever
    the edge is long enough.
    """

    if length <= 0 or target <= 0 or thickness <= 0:
        raise ValueError("invalid_finger_edge")
    if polarity not in {"male", "female"}:
        raise ValueError("invalid_finger_polarity")

    end_margin = min(thickness, length / 4)
    usable = max(length - 2 * end_margin, thickness)
    finger = min(target, usable)
    count = max(1, int((usable + finger) // (2 * finger)))
    while count > 1 and count * finger + (count - 1) * finger > usable:
        count -= 1
    used = count * finger + (count - 1) * finger
    margin = (length - used) / 2
    adjust = min(abs(compensation) / 2, max(0.0, finger / 2 - 0.05))
    if compensation < 0:
        adjust = -adjust

    intervals = []
    for index in range(count):
        start = margin + index * finger * 2
        end = start + finger
        if polarity == "male":
            start -= adjust
            end += adjust
        else:
            start += adjust
            end -= adjust
        intervals.append((max(0.0, start), min(length, end)))
    return intervals


def panel_outline(panel: dict[str, Any], g: dict[str, Any]) -> list[tuple[float, float]]:
    """Generate one closed orthogonal panel contour."""

    x = float(panel["x"])
    y = float(panel["y"])
    width = float(panel["width"])
    depth = float(panel["depth"])
    corners = ((x, y), (x + width, y), (x + width, y + depth), (x, y + depth))
    normals = ((0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0))
    points: list[tuple[float, float]] = []

    for index in range(4):
        start = corners[index]
        end = corners[(index + 1) % 4]
        edge = panel["edges"][index]
        edge_points = _edge_points(
            start,
            end,
            normals[index],
            float(g["material_thickness"]),
            float(g[f"joint_size_{edge['axis']}"]),
            str(edge["polarity"]),
            float(g["laser_compensation"]),
        )
        points.extend(edge_points if not points else edge_points[1:])

    return _deduplicate(points)


def _edge_points(
    start: tuple[float, float],
    end: tuple[float, float],
    normal: tuple[float, float],
    thickness: float,
    target: float,
    polarity: str,
    compensation: float,
) -> list[tuple[float, float]]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    offset = thickness if polarity == "male" else -thickness
    result = [start]
    for interval_start, interval_end in finger_intervals(
        length, target, thickness, polarity, compensation
    ):
        base_start = (start[0] + ux * interval_start, start[1] + uy * interval_start)
        base_end = (start[0] + ux * interval_end, start[1] + uy * interval_end)
        result.extend(
            [
                base_start,
                (base_start[0] + normal[0] * offset, base_start[1] + normal[1] * offset),
                (base_end[0] + normal[0] * offset, base_end[1] + normal[1] * offset),
                base_end,
            ]
        )
    result.append(end)
    return _deduplicate(result)


def _deduplicate(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        rounded = (round(point[0], 9), round(point[1], 9))
        if not result or rounded != result[-1]:
            result.append(rounded)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def sheet_size(panel_list: list[dict[str, Any]], g: dict[str, Any]) -> tuple[float, float]:
    margin = max(12.0, float(g["material_thickness"]) * 5)
    return (
        max(float(panel["x"]) + float(panel["width"]) for panel in panel_list) + margin,
        max(float(panel["y"]) + float(panel["depth"]) for panel in panel_list) + margin,
    )


def diagonal_segments(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Diagnostic helper used by focused geometry tests."""

    return [
        (start, end)
        for start, end in zip(points, points[1:] + points[:1])
        if not math.isclose(start[0], end[0]) and not math.isclose(start[1], end[1])
    ]
