# MenuTitle: Generate Narrow, Short, Small Component Layers
# -*- coding: utf-8 -*-
"""Run in Glyphs 3 on selected glyphs; see WorkFlow.md.

Pure geometry below uses no Glyphs imports, so it can also be tested in Python.
All contours must be CCW strokes with matching sides and straight end caps.
"""

import math
import traceback
from collections import namedtuple
from uuid import uuid4


SCALE_CHOICES = (50, 75)
DEFAULT_SCALE = 75
EPSILON = 1e-9
Point = namedtuple("Point", "x y kind smooth", defaults=("line", False))


def layer_variants(width=DEFAULT_SCALE, height=DEFAULT_SCALE):
    if width not in SCALE_CHOICES or height not in SCALE_CHOICES:
        raise ValueError("Width and Height must each be 50 or 75")
    return (("Narrow", width, 100), ("Short", 100, height), ("Small", width, height))


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def multiply(a, factor):
    return a[0] * factor, a[1] * factor


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def length(a):
    return math.hypot(*a)


def scale_point(point, sx, sy, origin):
    return (origin[0] + sx * (point[0] - origin[0]),
            origin[1] + sy * (point[1] - origin[1]))


def rotate(vector, angle):
    cosine, sine = math.cos(angle), math.sin(angle)
    return (cosine * vector[0] - sine * vector[1],
            sine * vector[0] + cosine * vector[1])


def signed_angle(a, b):
    return math.atan2(cross(a, b), a[0] * b[0] + a[1] * b[1])


def contour_segments(points):
    """Validate line/cubic segment syntax, including the closing segment."""
    segments = []
    start = 0
    controls = []
    for end in list(range(1, len(points))) + [0]:
        kind = points[end].kind
        if kind == "offcurve":
            controls.append(end)
            continue
        expected = 2 if kind == "curve" else 0
        if len(controls) != expected:
            raise ValueError("node %d: %s segment needs %d handles, found %d"
                             % (end + 1, kind, expected, len(controls)))
        segments.append([start] + controls + [end])
        start, controls = end, []
    return segments


def signed_area(points, segments):
    """Exact signed area of lines and cubic Beziers, not their control polygon."""
    total = 0.0
    origin = points[0]
    for segment in segments:
        p = [subtract(points[i], origin) for i in segment]
        if len(p) == 2:
            total += cross(p[0], p[1])
            continue
        coefficients = [
            p[0],
            multiply(subtract(p[1], p[0]), 3),
            multiply(add(subtract(p[2], multiply(p[1], 2)), p[0]), 3),
            subtract(add(subtract(p[3], multiply(p[2], 3)),
                         multiply(p[1], 3)), p[0]),
        ]
        total += sum(cross(a, b) * j / (i + j)
                     for i, a in enumerate(coefficients)
                     for j, b in enumerate(coefficients) if j)
    return total / 2


def split_stroke(points, closed=True):
    """Return forward and reversed-backward sides from the designated start."""
    if not closed:
        raise ValueError("stroke contour must be closed")
    if len(points) < 4 or len(points) % 2:
        raise ValueError("stroke needs an even number of nodes with matching sides")
    if any(p.kind not in ("line", "curve", "offcurve") for p in points):
        raise ValueError("only line segments and cubic Beziers are supported")
    if any(not math.isfinite(v) for p in points for v in p[:2]):
        raise ValueError("node coordinates must be finite")
    half = len(points) // 2
    if (points[0].kind != "line" or points[half].kind != "line"
            or points[half - 1].kind == "offcurve"
            or points[-1].kind == "offcurve"):
        raise ValueError("start at the stroke's right-hand start; both caps must be lines")
    forward, backward = points[:half], list(reversed(points[half:]))
    if any((a.kind == "offcurve") != (b.kind == "offcurve")
           for a, b in zip(forward, backward)):
        raise ValueError("the two stroke sides must have matching nodes and handles")
    segments = contour_segments(points)
    if signed_area(points, segments) <= EPSILON:
        raise ValueError("stroke contour must be counterclockwise with nonzero area")
    return forward, backward


def path_directions(points):
    """Centered secants of the control polygon (including off-curve handles).

    Endpoints use one-sided directions. Coincident neighbors are skipped.
    A handle is not on the Bezier, so it has no intrinsic Bezier tangent;
    this secant convention defines its local frame without sampling the curve.
    """
    directions = []
    for i, point in enumerate(points):
        before = next((points[j] for j in range(i - 1, -1, -1)
                       if length(subtract(point, points[j])) > EPSILON), None)
        after = next((points[j] for j in range(i + 1, len(points))
                      if length(subtract(points[j], point)) > EPSILON), None)
        if before is None and after is None:
            raise ValueError("stroke centerline is collapsed; direction is undefined")
        direction = subtract(after if after is not None else point,
                             before if before is not None else point)
        if length(direction) <= EPSILON:
            raise ValueError("centerline doubles back at node %d; direction is undefined"
                             % (i + 1))
        directions.append(direction)
    return directions


def align_handles(incoming, node, outgoing):
    """Keep handle lengths, rotating toward their length-weighted mean angle."""
    incoming_direction = subtract(node, incoming)
    outgoing_direction = subtract(outgoing, node)
    in_length, out_length = length(incoming_direction), length(outgoing_direction)
    if min(in_length, out_length) <= EPSILON:
        return incoming, outgoing
    angle = signed_angle(incoming_direction, outgoing_direction)
    # The long handle moves less: in_adjust / out_adjust = out_length / in_length.
    direction = rotate(multiply(incoming_direction, 1 / in_length),
                       angle * out_length / (in_length + out_length))
    return (subtract(node, multiply(direction, in_length)),
            add(node, multiply(direction, out_length)))


def transform_stroke(points, sx, sy, origin, closed=True):
    """Scale midpoints, rotate offsets, then slightly thin along compressed axes.

    Compression is the removed fraction: a scale of .75 compresses by .25.
    Apply thinning AFTER rotation, in the destination's x/y axes. Keep full
    precision here; paired grid rounding belongs at the Glyphs write boundary.
    """
    if not all(math.isfinite(v) for v in (sx, sy, *origin)) or min(sx, sy) <= 0:
        raise ValueError("scales must be positive and the transform must be finite")
    forward, backward = split_stroke(points, closed)
    centers = [multiply(add(a, b), 0.5) for a, b in zip(forward, backward)]
    transformed = [scale_point(p, sx, sy, origin) for p in centers]
    old_directions = path_directions(centers)
    new_directions = path_directions(transformed)
    offset_sx = 1 - max(0, 1 - sx) / 20
    offset_sy = 1 - max(0, 1 - sy) / 20
    sides = [[], []]
    for i, (center, new_center) in enumerate(zip(centers, transformed)):
        angle = signed_angle(old_directions[i], new_directions[i])
        for output, side in zip(sides, (forward, backward)):
            offset = rotate(subtract(side[i], center), angle)
            offset = (offset[0] * offset_sx, offset[1] * offset_sy)
            output.append(add(new_center, offset))

    # Only joins smooth on BOTH original sides qualify. Work in the two open
    # sides so end caps never participate in smoothing.
    for i in range(1, len(forward) - 1):
        if (forward[i].kind == "offcurve"
                or not (forward[i].smooth and backward[i].smooth)):
            continue
        if not all(side[j].kind == "offcurve"
                   for side in (forward, backward) for j in (i - 1, i + 1)):
            continue
        for side in sides:
            side[i - 1], side[i + 1] = align_handles(side[i - 1], side[i], side[i + 1])

    # Restore original traversal, node types, smooth flags and straight caps.
    positions = sides[0] + list(reversed(sides[1]))
    return [p._replace(x=xy[0], y=xy[1]) for p, xy in zip(points, positions)]


def regular_axis_links(regular):
    """Coordinate equalities for Regular's lines and anchor-to-handle vectors."""
    links = ([], [])
    for segment in contour_segments(regular):
        edges = [segment] if len(segment) == 2 else [segment[:2], segment[-2:]]
        for a, b in edges:
            for axis in (0, 1):
                if abs(regular[a][axis] - regular[b][axis]) <= EPSILON:
                    links[axis].append((a, b))
    return links


def group_root(parents, node):
    while parents[node] != node:
        parents[node] = parents[parents[node]]
        node = parents[node]
    return node


def coordinate_groups(count, links):
    parents = list(range(count))
    for a, b in links:
        parents[group_root(parents, b)] = group_root(parents, a)
    return [group_root(parents, i) for i in range(count)]


def snap_from_regular(regular, points):
    """Restore Regular's exact axes after smoothing; leave other directions alone.

    For a straight run, average its generated perpendicular coordinates. Move
    its attached handles with their anchors before snapping eligible handles by
    rotation, preserving their lengths. Never use an angular proximity test.
    """
    segments = contour_segments(regular)
    links = ([], [])
    for segment in segments:
        if len(segment) != 2:
            continue
        a, b = segment
        for axis in (0, 1):
            if abs(regular[a][axis] - regular[b][axis]) <= EPSILON:
                links[axis].append((a, b))
    positions = [list(p[:2]) for p in points]
    for axis in (0, 1):
        groups = {}
        for i, root in enumerate(coordinate_groups(len(points), links[axis])):
            groups.setdefault(root, []).append(i)
        for members in groups.values():
            coordinate = sum(points[i][axis] for i in members) / len(members)
            for i in members:
                positions[i][axis] = coordinate
    for segment in segments:
        if len(segment) != 4:
            continue
        for anchor, handle in ((segment[0], segment[1]), (segment[3], segment[2])):
            vector = subtract(points[handle], points[anchor])
            source = subtract(regular[handle], regular[anchor])
            if abs(source[0]) <= EPSILON and abs(source[1]) <= EPSILON:
                vector = (0, 0)
            elif abs(source[0]) <= EPSILON:
                vector = (0, math.copysign(length(vector), source[1]))
            elif abs(source[1]) <= EPSILON:
                vector = (math.copysign(length(vector), source[0]), 0)
            positions[handle] = add(positions[anchor], vector)
    return [p._replace(x=xy[0], y=xy[1]) for p, xy in zip(points, positions)]


def round_stroke_pairs(points, grid_length, regular=None):
    """Round paired gaps once, keeping Regular's axis equalities when supplied.

    Treat coordinates linked by a horizontal/vertical feature as one group.
    Round gaps between groups, then position each connected set on the grid.
    Exact integer gaps have priority, so e.g. 79 cannot turn into 78 or 80.
    Noninteger gaps form a spanning tree: when a cycle's independently rounded
    gaps conflict, axis alignment and exact gaps take precedence. A zero grid
    keeps floats. Without axis links this is ordinary paired midpoint rounding.
    """
    if not math.isfinite(grid_length) or grid_length < 0:
        raise ValueError("font grid length must be finite and nonnegative")
    result = list(points)
    if grid_length == 0:
        return result
    links = regular_axis_links(regular) if regular is not None else ([], [])
    positions = [list(p[:2]) for p in points]
    count = len(points)
    for axis in (0, 1):
        roots = coordinate_groups(count, links[axis])
        groups = {}
        for i, root in enumerate(roots):
            groups.setdefault(root, []).append(i)
        edges = []
        for i in range(count // 2):
            j = count - i - 1
            gap = (points[j][axis] - points[i][axis]) / grid_length
            steps = math.floor(abs(gap) + 0.5 + EPSILON)
            if gap < 0:
                steps = -steps
            edges.append((abs(gap - steps) > EPSILON, points[i].kind == "offcurve",
                          i, roots[i], roots[j], steps))
        parents = list(range(count))
        forest = {root: [] for root in groups}
        for _, _, _, a, b, steps in sorted(edges):
            ra, rb = group_root(parents, a), group_root(parents, b)
            if ra != rb:
                parents[rb] = ra
                forest[a].append((b, steps))
                forest[b].append((a, -steps))
        seen = set()
        for root in groups:
            if root in seen:
                continue
            offsets = {root: 0}
            pending = [root]
            while pending:
                a = pending.pop()
                for b, steps in forest[a]:
                    if b not in offsets:
                        offsets[b] = offsets[a] + steps
                        pending.append(b)
            seen.update(offsets)
            origins = [points[i][axis] / grid_length - offset
                       for group, offset in offsets.items() for i in groups[group]]
            base = math.floor(sum(origins) / len(origins) + 0.5 + EPSILON)
            for group, offset in offsets.items():
                for i in groups[group]:
                    positions[i][axis] = (base + offset) * grid_length
    return [p._replace(x=xy[0], y=xy[1]) for p, xy in zip(points, positions)]


def glyphs_path_points(path, api):
    """Honor Glyphs' actual start node, independently of its storage index."""
    nodes = list(path.nodes)
    if not nodes:
        raise ValueError("empty contour")
    start = path.findStartNode()
    if start is None:
        raise ValueError("stroke contour must be closed")
    start_index = start.index
    order = list(range(start_index, len(nodes))) + list(range(start_index))
    kinds = {api.LINE: "line", api.CURVE: "curve", api.OFFCURVE: "offcurve"}
    points = [Point(float(nodes[i].position.x), float(nodes[i].position.y),
                    kinds.get(nodes[i].type, "unsupported"), bool(nodes[i].smooth))
              for i in order]
    return points, order


def prepare_layers(source, variants, origin, api, grid_length):
    """Build every requested layer detached; validation never edits the font."""
    if source.components:
        raise ValueError("Regular must contain stroke contours, not components")
    # Glyphs' paths iterator stops at an empty contour, silently hiding later
    # strokes. Components are excluded above, so traverse the full shapes array
    # and retain its indices when writing the copied layer.
    strokes = []
    for index, path in enumerate(source.shapes):
        if not len(path.nodes):
            continue
        try:
            points, order = glyphs_path_points(path, api)
            split_stroke(points, path.closed)
            strokes.append((index, points, order))
        except ValueError as error:
            raise ValueError("contour %d: %s" % (index + 1, error)) from error
    if not strokes:
        raise ValueError("Regular contains no stroke contours")
    layers = []
    for name, width, height in variants:
        sx, sy = width / 100, height / 100
        layer = source.copy()
        layer.layerId = str(uuid4()).upper()
        layer.associatedMasterId = source.associatedMasterId
        layer.name = name
        for index, points, order in strokes:
            path = layer.shapes[index]
            try:
                result = transform_stroke(points, sx, sy, origin)
                result = snap_from_regular(points, result)
                result = round_stroke_pairs(result, grid_length, regular=points)
            except ValueError as error:
                raise ValueError("contour %d: %s" % (index + 1, error)) from error
            for node_index, point in zip(order, result):
                path.nodes[node_index].position = (point.x, point.y)
        for anchor in layer.anchors:
            anchor.position = scale_point((anchor.position.x, anchor.position.y),
                                          sx, sy, origin)
        # Copying retains the component's advance width and metrics. Width and
        # Height above are smart-axis percentages, not advances in font units.
        layers.append((layer, width, height))
    return layers


def existing_smart_axes(glyph):
    """Read supported axis ranges without changing the glyph."""
    axes = {}
    # Glyphs' empty smartComponentAxes proxy can return None from __iter__.
    # Read its backing array, which legitimately is nil before axes exist.
    existing_axes = list(glyph.partsSettings() or ())
    for name in ("Width", "Height"):
        matches = [axis for axis in existing_axes if axis.name == name]
        if len(matches) > 1:
            raise ValueError("multiple %s smart axes exist" % name)
        if matches:
            axis = matches[0]
            if axis.bottomValue not in SCALE_CHOICES or axis.topValue != 100:
                raise ValueError(
                    "%s smart axis has unexpected range %s–%s; expected 50–100 or 75–100"
                    % (name, axis.bottomValue, axis.topValue))
            axes[name] = axis
    return axes


def selected_scale_defaults(selected):
    """Validate the whole selection and find a shared default for each axis."""
    defaults, owners, seen = {}, {}, set()
    for layer in selected:
        glyph = layer.parent
        if glyph.name in seen:
            continue
        seen.add(glyph.name)
        try:
            axes = existing_smart_axes(glyph)
        except ValueError as error:
            raise ValueError("%s: %s" % (glyph.name, error)) from error
        for name, axis in axes.items():
            value = axis.bottomValue
            if name in defaults and defaults[name] != value:
                raise ValueError(
                    "%s settings differ: %s uses %s–100, but %s uses %s–100. "
                    "Run these glyphs separately."
                    % (name, owners[name], defaults[name], glyph.name, value))
            defaults[name], owners[name] = value, glyph.name
    return (defaults.get("Width", DEFAULT_SCALE), defaults.get("Height", DEFAULT_SCALE))


def generate_layers(glyph, master_id, api, width=DEFAULT_SCALE, height=DEFAULT_SCALE):
    """Create missing variants and configure smart axes and all four mappings."""
    variants = layer_variants(width, height)
    related = [layer for layer in glyph.layers if layer.associatedMasterId == master_id]
    regular = [layer for layer in related if layer.name == "Regular"]
    if len(regular) != 1:
        raise ValueError("expected exactly one Regular layer for the selected master")
    source = regular[0]
    existing = {}
    for name, _, _ in variants:
        matches = [layer for layer in related if layer.name == name]
        if len(matches) > 1:
            raise ValueError("multiple %s layers exist for the selected master" % name)
        if matches:
            existing[name] = matches[0]
    axes = existing_smart_axes(glyph)
    missing = [variant for variant in variants if variant[0] not in existing]
    # The Chinese character box is one em wide, with its bottom at the master
    # descender: (1000, -120) in this font. Do not use the ink bounding box.
    origin = (float(glyph.parent.upm), float(source.master.descender))
    prepared = (prepare_layers(source, missing, origin, api, float(glyph.parent.gridLength))
                if missing else [])
    glyph.beginUndo()
    try:
        for name, minimum in (("Width", width), ("Height", height)):
            if name not in axes:
                axis = api.GSSmartComponentAxis()
                axis.name = name
                glyph.smartComponentAxes.append(axis)
                axes[name] = axis
            # Keep existing axis objects/IDs so component references stay valid.
            axes[name].topValue = 100
            axes[name].bottomValue = minimum
        for layer, _, _ in prepared:
            glyph.layers.append(layer)
        # Attach first, then assign a fresh dictionary to each layer. This also
        # repairs missing/wrong mappings on Regular and previously named layers.
        retained = [(existing[name], w, h) for name, w, h in variants if name in existing]
        for layer, layer_width, layer_height in [(source, 100, 100)] + retained + prepared:
            mapping = dict(layer.partSelection() or {})
            mapping[axes["Width"].id] = 2 if layer_width == 100 else 1
            mapping[axes["Height"].id] = 2 if layer_height == 100 else 1
            # smartComponentPoleMapping is a read-only proxy in Glyphs 3.
            # Its native setter installs an independent mutable dictionary.
            layer.setPartSelection_(api.objcObject(mapping))
    finally:
        glyph.endUndo()
    return [layer.name for layer, _, _ in prepared]


def generate_selected(font, selected, api, width, height):
    seen = set()
    completed, problems = [], []
    if not selected:
        return completed, ["Select one or more glyphs first."]
    # Recheck on Generate in case settings changed while the dialog was open.
    # Unexpected settings anywhere must stop the batch before any glyph is edited.
    try:
        layer_variants(width, height)
        selected_scale_defaults(selected)
    except ValueError as error:
        return completed, ["Warning: generation stopped before making changes.\n%s" % error]
    font.disableUpdateInterface()
    try:
        for layer in selected:
            glyph = layer.parent
            key = glyph.name, layer.associatedMasterId
            if key in seen:
                continue
            seen.add(key)
            try:
                generated = generate_layers(glyph, key[1], api, width, height)
                completed.append(glyph.name)
                kept = [name for name, _, _ in layer_variants(width, height)
                        if name not in generated]
                print("%s: generated %s; kept %s; Width %d–100, Height %d–100"
                      % (glyph.name, ", ".join(generated) or "none",
                         ", ".join(kept) or "none", width, height))
            except ValueError as error:
                problem = "%s: skipped — %s" % (glyph.name, error)
                problems.append(problem)
                print(problem)
            except Exception as error:
                problem = "%s: failed — %s: %s" % (glyph.name, type(error).__name__, error)
                problems.append(problem)
                print(problem)
                traceback.print_exc()
    finally:
        font.enableUpdateInterface()
    return completed, problems


class ComponentLayerDialog:
    def __init__(self, font, api, ui):
        self.font, self.api = font, api
        self.selected = list(font.selectedLayers)
        width, height = selected_scale_defaults(self.selected)
        self.w = ui.FloatingWindow((360, 215), "Generate Component Layers")
        self.w.widthLabel = ui.TextBox((15, 17, 110, 20), "Scale width to:")
        self.w.width = ui.PopUpButton((140, 12, 200, 25), ["50%", "75%"])
        self.w.heightLabel = ui.TextBox((15, 57, 110, 20), "Scale height to:")
        self.w.height = ui.PopUpButton((140, 52, 200, 25), ["50%", "75%"])
        self.w.width.set(SCALE_CHOICES.index(width))
        self.w.height.set(SCALE_CHOICES.index(height))
        self.w.helpText = ui.TextBox(
            (15, 95, 330, 60),
            "Regular is 100%. Generate adds missing Narrow, Short, and Small "
            "layers, keeps existing outlines, and configures Width and Height.")
        self.w.cancel = ui.Button((140, 175, 90, 24), "Cancel", callback=self.cancel)
        self.w.generate = ui.Button((245, 175, 100, 24), "Generate", callback=self.generate)
        self.w.setDefaultButton(self.w.generate)
        self.w.open()

    def generate(self, sender):
        width = SCALE_CHOICES[self.w.width.get()]
        height = SCALE_CHOICES[self.w.height.get()]
        self.w.generate.enable(False)
        try:
            completed, problems = generate_selected(self.font, self.selected, self.api, width, height)
        except Exception as error:
            traceback.print_exc()
            completed, problems = [], ["%s: %s" % (type(error).__name__, error)]
        finally:
            self.w.generate.enable(True)
        if completed:
            self.w.close()
            title = "Component layers ready"
            message = "Processed:\n" + "\n".join(completed[:8])
            if len(completed) > 8:
                message += "\nand %d more glyphs." % (len(completed) - 8)
            message += ("\n\nExisting layers were kept; only missing layers were generated."
                        "\nView the results in the Layers palette.")
        else:
            title = "No layers generated"
            message = ""
        if problems:
            self.api.Glyphs.showMacroWindow()
            message += "\n\n" + "\n".join(problems[:8])
            if len(problems) > 8:
                message += "\nSee the Macro Panel for the remaining messages."
        self.api.Message(title, message.strip())

    def cancel(self, sender):
        self.w.close()


def main():
    try:
        import GlyphsApp as api
        import vanilla
    except ImportError:
        raise SystemExit("Run this script inside Glyphs 3 with Vanilla installed.")
    font = api.Glyphs.font
    if font is None or not font.selectedLayers:
        api.Message("No glyphs selected", "Select one or more glyphs in an open font first.")
        return
    try:
        return ComponentLayerDialog(font, api, vanilla)
    except ValueError as error:
        api.Message("Unexpected smart component settings",
                    "%s\n\nStopped without making changes." % error)


if __name__ == "__main__":
    # Keep the controller alive while the nonmodal dialog is open.
    component_layer_dialog = main()
