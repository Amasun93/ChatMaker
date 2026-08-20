"""Chinese-capable text rendering that bypasses OpenSCAD's broken ``text()``.

OpenSCAD 2021.01 ships an old FreeType/fontconfig stack that renders CJK
glyphs as tofu boxes regardless of which font file is used. ChatCAD therefore
reads glyph outlines directly via fontTools and emits geometry instead:

- ``.scad`` output uses ``polygon()`` point sets + ``linear_extrude()``,
  never ``text()``, so every OpenSCAD version renders Chinese correctly.
- ``.stl`` output is triangulated in pure Python (ear clipping with hole
  bridging), independent of any desktop font configuration.

Font resolution order: caller-supplied file, the bundled ChatMaker CJK Sans
subset, then platform system fonts.  The bundle covers printable ASCII and
all GB2312 characters, so common Simplified Chinese names and labels work on
a clean Windows, macOS, or Linux computer without desktop fonts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

CURVE_SEGMENTS = 8
BUNDLED_CJK_FONT = Path(__file__).with_name("assets") / "ChatMakerCJK-Regular.otf"

_FONT_CANDIDATES: dict[str, list[str]] = {
    "win32": [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ],
    "darwin": [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ],
    "linux": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ],
}


def find_cjk_font(explicit: str | None = None) -> Path:
    """Return an existing CJK-capable font file path."""
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_file():
            raise ValueError(f"font_file_not_found: {explicit}")
        return candidate
    if BUNDLED_CJK_FONT.is_file():
        return BUNDLED_CJK_FONT
    platform = "win32" if sys.platform.startswith("win") else sys.platform if sys.platform in _FONT_CANDIDATES else "linux"
    for name in _FONT_CANDIDATES.get(platform, []):
        candidate = Path(name)
        if candidate.is_file():
            return candidate
    raise ValueError(
        "no_cjk_font_found: bundled ChatMaker CJK Sans is missing; install Microsoft YaHei/SimHei (Windows), "
        "PingFang (macOS) or Noto Sans CJK (Linux), or pass parameters.engrave_font"
    )


class _OutlinePen:
    """Flattens TrueType quadratic and CFF cubic outlines into polylines."""

    def __init__(self, glyph_set: dict[str, Any]) -> None:
        self._glyph_set = glyph_set
        self.contours: list[list[tuple[float, float]]] = []
        self._current: list[tuple[float, float]] = []

    def _q(self, p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float]) -> None:
        for step in range(1, CURVE_SEGMENTS + 1):
            t = step / CURVE_SEGMENTS
            mt = 1 - t
            self._current.append((
                mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
            ))

    def _c(self, p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> None:
        for step in range(1, CURVE_SEGMENTS + 1):
            t = step / CURVE_SEGMENTS
            mt = 1 - t
            self._current.append((
                mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1],
            ))

    # RecordingPen-style protocol used by glyph.draw()
    def moveTo(self, point: tuple[float, float]) -> None:
        self._current = [point]

    def lineTo(self, point: tuple[float, float]) -> None:
        self._current.append(point)

    def curveTo(self, *points: tuple[float, float]) -> None:
        from fontTools.pens.basePen import decomposeSuperBezierSegment

        p0 = self._current[-1]
        if len(points) == 3:
            self._c(p0, points[0], points[1], points[2])
        else:
            for c1, c2, end in decomposeSuperBezierSegment([p0] + list(points)):
                self._c(p0, c1, c2, end)
                p0 = end

    def qCurveTo(self, *points: tuple[float, float] | None) -> None:
        from fontTools.pens.basePen import decomposeQuadraticSegment

        clean: list[tuple[float, float]] = []
        for point in points:
            if point is not None:
                clean.append((point[0], point[1]))
        if points and points[-1] is None:
            # Implied on-curve end: the last control point closes back toward start.
            if clean:
                first = self._current[-1]
                clean.append(((first[0] + clean[-1][0]) / 2, (first[1] + clean[-1][1]) / 2))
        for control, end in decomposeQuadraticSegment([self._current[-1]] + clean):
            if control is None:
                self._current.append(end)
            else:
                self._q(self._current[-1], control, end)

    def closePath(self) -> None:
        self._finish()

    def endPath(self) -> None:
        self._finish()

    def _finish(self) -> None:
        if len(self._current) >= 3:
            self.contours.append(self._current)
        self._current = []

    def addComponent(self, glyph_name: str, transformation: Any) -> None:
        # Composite glyphs (common in CJK fonts): draw the referenced glyph
        # first, then apply its 2x3 affine transform to the new contours.
        start = len(self.contours)
        saved = self._current
        self._current = []
        self._glyph_set[glyph_name].draw(self)
        xx, _xy, _yx, yy, dx, dy = tuple(transformation)[:6]
        for index in range(start, len(self.contours)):
            self.contours[index] = [
                (x * xx + dx, y * yy + dy) for x, y in self.contours[index]
            ]
        self._current = saved


def _signed_area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for index in range(len(points)):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return total / 2


def glyph_layout(text: str, size: float, font_file: str | None = None) -> dict[str, Any]:
    """Lay out ``text`` horizontally and return scaled glyph contours."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ValueError("fontTools_missing: pip install fonttools") from exc
    path = find_cjk_font(font_file)
    try:
        font = TTFont(str(path), fontNumber=0)
    except Exception:
        font = TTFont(str(path))
    upem = font["head"].unitsPerEm
    scale = size / upem
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    pen = _OutlinePen(glyph_set)
    x = 0.0
    glyphs: list[dict[str, Any]] = []
    for char in text:
        if char.isspace():
            x += size * 0.5
            continue
        glyph_name = cmap.get(ord(char))
        if glyph_name is None:
            raise ValueError(f"no_glyph_in_font: {char!r}")
        pen.contours = []
        glyph_set[glyph_name].draw(pen)
        contours = [
            [(x + vx * scale, vy * scale) for vx, vy in contour]
            for contour in pen.contours
        ]
        glyphs.append({"contours": contours})
        x += hmtx[glyph_name][0] * scale
    return {"width": x, "glyphs": glyphs, "font": str(path)}


def _point_in_triangle(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(area) < 1e-12:
        return False
    d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    d2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
    d3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
    if area > 0:
        return d1 > 1e-12 and d2 > 1e-12 and d3 > 1e-12
    return d1 < -1e-12 and d2 < -1e-12 and d3 < -1e-12


def _point_in_polygon(p: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    inside = False
    count = len(polygon)
    for index in range(count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % count]
        if (y1 > p[1]) != (y2 > p[1]):
            slope = (x2 - x1) / (y2 - y1)
            cross_x = x1 + slope * (p[1] - y1)
            if cross_x > p[0]:
                inside = not inside
    return inside


def _bridge_holes(outer: list[tuple[float, float]], holes: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Merge holes into the outer contour by duplicating bridge vertices."""
    merged = outer[:]
    for hole in holes:
        # Holes must walk clock-wise inside a counter-clockwise outer ring.
        oriented = hole if _signed_area(hole) < 0 else list(reversed(hole))
        bridge_from = max(range(len(oriented)), key=lambda index: oriented[index][0])
        right = oriented[bridge_from]
        candidates = sorted(
            (vertex for vertex in merged if vertex[0] >= right[0] - 1e-9 and vertex != right),
            key=lambda vertex: (vertex[0] - right[0]) ** 2 + (vertex[1] - right[1]) ** 2,
        )
        target = None
        for vertex in candidates:
            mid = ((vertex[0] + right[0]) / 2, (vertex[1] + right[1]) / 2)
            if _point_in_polygon(mid, merged) and not any(_point_in_polygon(mid, h) for h in holes):
                target = vertex
                break
        if target is None:
            continue  # bridging failed: hole is dropped (printed solid)
        walk = merged.index(target)
        ring = oriented[bridge_from:] + oriented[:bridge_from]
        merged = merged[:walk + 1] + ring + [ring[0], target] + merged[walk:]
    return merged


def _ear_clip(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]:
    indices = list(range(len(points)))
    triangles: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]] = []
    guard = 0
    while len(indices) > 3 and guard < len(points) * 10:
        guard += 1
        clipped = False
        for position in range(len(indices)):
            previous = indices[position - 1]
            current = indices[position]
            following = indices[(position + 1) % len(indices)]
            a, b, c = points[previous], points[current], points[following]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-9:
                continue
            if any(
                _point_in_triangle(points[other], a, b, c)
                for other in indices
                if other not in (previous, current, following)
            ):
                continue
            triangles.append((a, b, c))
            indices.pop(position)
            clipped = True
            break
        if not clipped:
            for position in range(len(indices)):
                previous = indices[position - 1]
                current = indices[position]
                following = indices[(position + 1) % len(indices)]
                a, b, c = points[previous], points[current], points[following]
                cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                if cross > 1e-9:
                    triangles.append((a, b, c))
                    indices.pop(position)
                    break
            else:
                break
    if len(indices) == 3:
        triangles.append((points[indices[0]], points[indices[1]], points[indices[2]]))
    return triangles


def _orient(points: list[tuple[float, float]], positive: bool) -> list[tuple[float, float]]:
    return points if (_signed_area(points) > 0) == positive else list(reversed(points))


def _group_contours(contours: list[list[tuple[float, float]]]) -> list[tuple[list[tuple[float, float]], list[list[tuple[float, float]]]]]:
    """Group glyph contours into solid rings with holes.

    Contour direction conventions differ between TrueType (outer clockwise)
    and CFF (outer counter-clockwise), so grouping uses containment topology:
    even nesting depth is solid, odd depth is a hole of its parent.
    """
    count = len(contours)
    container = [-1] * count
    for index in range(count):
        best, best_area = -1, float("inf")
        for other in range(count):
            if other == index:
                continue
            if _point_in_polygon(contours[index][0], contours[other]):
                area = abs(_signed_area(contours[other]))
                if area < best_area:
                    best, best_area = other, area
        container[index] = best

    def depth(index: int) -> int:
        level, cursor = 0, container[index]
        while cursor != -1:
            level += 1
            cursor = container[cursor]
        return level

    groups: list[tuple[list[tuple[float, float]], list[list[tuple[float, float]]]]] = []
    for index in range(count):
        if depth(index) % 2 == 0:
            outer = _orient(contours[index], positive=True)
            holes = [
                _orient(contours[hole], positive=False)
                for hole in range(count)
                if container[hole] == index
            ]
            groups.append((outer, holes))
    return groups


def scad_polygons_from_layout(
    layout: dict[str, Any],
    offset: tuple[float, float] = (0.0, 0.0),
) -> list[str]:
    """Turn an existing layout into ``polygon()`` statements (no extrusion).

    Extrusion is left to the caller so SCAD customizer parameters (e.g. the
    Bambu Studio Custom 3D Print lab) can still drive text depth and scale.
    """
    dx, dy = offset
    statements: list[str] = []
    for glyph in layout["glyphs"]:
        if not glyph["contours"]:
            continue
        points: list[tuple[float, float]] = []
        paths: list[list[int]] = []
        for contour in glyph["contours"]:
            paths.append(list(range(len(points), len(points) + len(contour))))
            points.extend(contour)
        points_code = ", ".join(f"[{x + dx:.4f},{y + dy:.4f}]" for x, y in points)
        paths_code = ", ".join(str(path) for path in paths)
        statements.append(f"polygon(points=[{points_code}], paths=[{paths_code}]);")
    return statements


def scad_text_polygons(
    text: str,
    size: float,
    font_file: str | None = None,
    offset: tuple[float, float] = (0.0, 0.0),
) -> tuple[list[str], float]:
    layout = glyph_layout(text, size, font_file)
    return scad_polygons_from_layout(layout, offset), layout["width"]


def scad_text(
    text: str,
    size: float,
    height: float,
    font_file: str | None = None,
    offset: tuple[float, float] = (0.0, 0.0),
) -> str:
    """Emit OpenSCAD polygon()+linear_extrude() geometry for ``text``.

    Never uses ``text()`` so every OpenSCAD build renders Chinese correctly.
    """
    statements, _width = scad_text_polygons(text, size, font_file, offset)
    return "\n".join(
        f"linear_extrude(height={height:.4f}) {statement}"
        for statement in statements
    )


def triangles_from_layout(
    layout: dict[str, Any],
    height: float,
    base_z: float = 0.0,
    offset: tuple[float, float] = (0.0, 0.0),
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Extrude an existing layout into STL triangles."""
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []
    dx, dy = offset
    for glyph in layout["glyphs"]:
        for outer, holes in _group_contours(glyph["contours"]):
            contour = [(x + dx, y + dy) for x, y in _bridge_holes(outer, holes)]
            if len(contour) < 3:
                continue
            top = [(x, y, base_z + height) for x, y in contour]
            bottom = [(x, y, base_z) for x, y in contour]
            for a, b, c in _ear_clip(contour):
                triangles.append(((a[0], a[1], base_z + height), (b[0], b[1], base_z + height), (c[0], c[1], base_z + height)))
                triangles.append(((a[0], a[1], base_z), (c[0], c[1], base_z), (b[0], b[1], base_z)))
            count = len(contour)
            for index in range(count):
                following = (index + 1) % count
                triangles.append((top[index], top[following], bottom[following]))
                triangles.append((top[index], bottom[following], bottom[index]))
    return triangles


def text_triangles(
    text: str,
    size: float,
    height: float,
    base_z: float = 0.0,
    offset: tuple[float, float] = (0.0, 0.0),
    font_file: str | None = None,
) -> tuple[
    list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    dict[str, Any],
]:
    """Return extruded text as STL triangles plus layout info."""
    layout = glyph_layout(text, size, font_file)
    return triangles_from_layout(layout, height, base_z, offset), layout
