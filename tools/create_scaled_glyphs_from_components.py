# MenuTitle: Create Scaled Glyphs from Component List
# -*- coding: utf-8 -*-
"""Create glyphs from out/new_glyphs.txt using statistics from the open font.

Run in Glyphs 3 (Scripts menu or Macro Panel). Pure parsing and affine helpers
can also be imported outside Glyphs for testing.
"""

import math
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from statistics import NormalDist, mean, pstdev


IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
POSITIONS = {"⿰": ("left", "right"), "⿱": ("top", "bottom")}
IDS_ARITY = dict.fromkeys("⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿼⿽㇯", 2)
IDS_ARITY.update(dict.fromkeys("⿲⿳", 3))
IDS_ARITY.update(dict.fromkeys("⿾⿿", 1))
KANGXI = {unicodedata.normalize("NFKC", chr(n))
          for n in range(0x2F00, 0x2FD6)}
RADICAL_VARIANTS = set("亻刂忄扌氵氺灬犭礻衤罒耂艹訁讠釒钅飠饣纟糹牜阝辶龵爫丬戸户青黄麦齐齿龙龟门见贝车长韦页风飞马鱼鸟卤黾")


class InputError(ValueError):
    pass


class InvalidCurrentComponent(InputError):
    """Stop the batch before editing when its current component is unusable."""


@dataclass(frozen=True)
class Alias:
    reference: str


@dataclass
class Source:
    components: list
    # A direct smart glyph, or None for a group expanded from a character.
    glyph: object = None
    # Read while attached: detached GSComponent copies cannot resolve their glyph
    # or render meaningful bounds until inserted into the destination layer.
    parts: object = None


@dataclass(frozen=True)
class Subpart:
    glyph: object
    sample: object


@dataclass(frozen=True)
class Sample:
    width: object
    height: object
    transform: tuple
    bounds: object = None


@dataclass(frozen=True)
class Placement:
    # Fractions within the rendered bounding box (0=edge, .5=center, 1=edge).
    anchor: tuple
    # None leaves that coordinate untouched.
    position: tuple


@dataclass(frozen=True)
class Adjustment:
    width: object
    height: object
    transform: tuple
    placement: object = None
    preserve_y: bool = False


def proxy_value(mapping, key):
    """Glyphs proxies need indexed access; some do not implement dict.get()."""
    if mapping is None:
        return None
    try:
        return mapping[key]
    except KeyError:
        return None


def smart_axes(glyph):
    result = {}
    # Glyphs' empty axes proxy has len == 0 but its __iter__ returns None.
    # Normalize it before iteration, including ordinary reference components.
    for axis in glyph.smartComponentAxes or ():
        if axis.name in result:
            raise InputError("Duplicate smart axis %s in %s" % (axis.name, glyph.name))
        result[axis.name] = axis
    return result


def axis_id(axis):
    return axis.id


def smart_value(component, glyph, axis, master_id):
    value = proxy_value(component.smartComponentValues, axis_id(axis))
    if value is None:
        source_master = getattr(component, "componentMasterId", None) or master_id
        base_layer = glyph.layers[source_master]
        if base_layer is None:
            raise InputError("Missing master %s in %s" % (source_master, glyph.name))
        pole = proxy_value(base_layer.smartComponentPoleMapping, axis_id(axis))
        if pole not in (1, 2):
            raise InputError("Missing default pole for %s / %s / %s"
                             % (glyph.name, source_master, axis.name))
        value = axis.bottomValue if pole == 1 else axis.topValue
    value = float(value)
    if not math.isfinite(value):
        raise InputError("Non-finite smart value in " + glyph.name)
    return value


def component_sample(component, master_id):
    glyph = component.component
    if glyph is None:
        raise InputError("Broken reference: " + component.componentName)
    axes = smart_axes(glyph)
    values = [smart_value(component, glyph, axes[name], master_id) if name in axes else None
              for name in ("Width", "Height")]
    transform = tuple(float(v) for v in component.transform)
    if not all(math.isfinite(v) for v in transform):
        raise InputError("Non-finite transform in " + component.componentName)
    return Sample(*values, transform, component_box(component))


def component_box(component):
    bounds = getattr(component, "bounds", None)
    if bounds is None:
        return None
    box = (float(bounds.origin.x), float(bounds.origin.y),
           float(bounds.size.width), float(bounds.size.height))
    if not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
        raise InputError("Invalid component bounds: " + component.componentName)
    return box


def tokens(text):
    """Treat bracketed radical names as one component, as in the old script."""
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        if char.isspace():
            i += 1
            continue
        if char == "[":
            end = text.find("]", i + 1)
            if end < 0 or end == i + 1:
                raise InputError("Unclosed or empty bracketed component: " + text)
            result.append(text[i + 1:end])
            i = end + 1
        else:
            if char == "]":
                raise InputError("Unexpected closing bracket: " + text)
            result.append(char)
            i += 1
    return result


def read_definitions(path):
    rows = []
    with open(path, encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != 2 or not all(field.strip() for field in fields):
                raise InputError("Malformed new_glyphs line %d" % number)
            target, definition = (field.strip() for field in fields)
            alias = re.fullmatch(r"同「([^「」]+)」", definition)
            if alias:
                reference = alias[1].strip()
                if len(target) != 1 or len(reference) != 1:
                    raise InputError("Alias must name one target and one reference character (line %d)." % number)
                rows.append((target, Alias(reference)))
            elif definition.startswith("同「"):
                raise InputError("Malformed alias on new_glyphs line %d" % number)
            else:
                rows.append((target, tokens(definition)))
    if not rows:
        raise InputError("out/new_glyphs.txt contains no definitions.")
    return rows


def split_definitions(rows):
    glyphs = []
    aliases = {}
    targets = set()
    for target, definition in rows:
        if isinstance(definition, Alias):
            if target in targets or target in aliases and aliases[target] != definition.reference:
                raise InputError("Conflicting definitions for " + target)
            aliases[target] = definition.reference
        else:
            if target in aliases:
                raise InputError("Conflicting definitions for " + target)
            targets.add(target)
            glyphs.append((target, definition))
    return glyphs, aliases


def read_radicals(path):
    result = {}
    with open(path, encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = line.strip().split("\t")
            if len(fields) != 3:
                raise InputError("Malformed radicals.txt line %d" % number)
            token, position, name = fields
            result.setdefault(token, {})[position] = name
    return result


def is_kangxi(token):
    return (unicodedata.normalize("NFKC", token) in KANGXI
            or token in RADICAL_VARIANTS
            or len(token) == 1 and 0x2E80 <= ord(token) <= 0x2EFF)


def current_candidates(rows):
    rows = [row for row in rows if not isinstance(row[1], Alias)]
    counts = Counter(token for _, parts in rows for token in parts
                     if token not in IDS_ARITY)
    if len(rows) == 1:
        return [token for token in counts if not is_kangxi(token)]
    if not counts:
        return []
    maximum = max(counts.values())
    return [token for token, count in counts.items() if count == maximum]


def flat_layout(parts):
    """Only a single IDS operator with immediate leaf components is supported."""
    if (not parts or parts[0] not in IDS_ARITY
            or len(parts) != IDS_ARITY[parts[0]] + 1
            or any(part in IDS_ARITY for part in parts[1:])):
        raise InputError("Expected one flat IDS layout: " + " ".join(parts))
    return parts[0], parts[1:]


def rating_quantile(value):
    try:
        rating = float(value)
    except (TypeError, ValueError):
        raise InputError("Enter a number strictly between 0 and 10.")
    if not math.isfinite(rating) or not 0 < rating < 10:
        raise InputError("Enter a number strictly between 0 and 10.")
    # Evaluate on the lower tail to avoid rounding 1-q to zero near an endpoint.
    tail = min(rating, 10 - rating) / 10
    if tail == 0:
        raise InputError("Rating is too close to zero to represent its quantile.")
    z = NormalDist().inv_cdf(tail)
    return z if rating <= 5 else -z


def compose(outer, inner):
    """Apply inner first, then outer, including translations (Glyphs order)."""
    a, b, c, d, x, y = outer
    e, f, g, h, u, v = inner
    return (a * e + c * f, b * e + d * f,
            a * g + c * h, b * g + d * h,
            a * u + c * v + x, b * u + d * v + y)


def transform_point(transform, point):
    a, b, c, d, x, y = transform
    u, v = point
    return (a * u + c * v + x, b * u + d * v + y)


def estimate(samples, z=0.0):
    return mean(samples) + z * pstdev(samples)


def smart_estimate(samples, layout, z, side=None, current=False):
    preserve_y = current and layout == "⿰"
    values = []
    for dimension in ("width", "height"):
        if preserve_y and dimension == "height":
            values.append(None)
            continue
        available = [getattr(s, dimension) for s in samples if getattr(s, dimension) is not None]
        active = (dimension == "width") == (layout == "⿰")
        values.append(estimate(available, z if active else 0) if available else None)
    # Smart Width/Height carry the proportional adjustment. The ordinary matrix
    # only contributes its mean (including translations), never another quantile.
    transform = tuple(mean(s.transform[i] for s in samples) for i in range(6))
    if preserve_y:
        # Keep the source's vertical scale AND position. Placement must also
        # skip y, including when interpolated children are measured individually.
        a, _, c, _, x, _ = transform
        transform = (a, 0.0, c, 1.0, x, 0.0)
    if not all(math.isfinite(v) for v in values + list(transform) if v is not None):
        raise InputError("Non-finite estimated adjustment.")
    if abs(transform[0] * transform[3] - transform[1] * transform[2]) < 1e-12:
        raise InputError("Reference transforms average to a singular matrix.")
    placement = None
    if side is not None:
        boxes = [s.bounds for s in samples if s.bounds is not None]
        if boxes:
            # Counterparts are different smart drawings: a .left drawing may
            # compress around x=0, while a general drawing uses x=upm plus a
            # negative component offset. Their raw offsets are not transferable.
            # Keep the outside edge in place as the weight changes, centering
            # the perpendicular dimension at the references' mean position.
            anchor = (side, .5) if layout == "⿰" else (.5, 1 - side)
            position = tuple(None if preserve_y and i == 1 else
                             mean(box[i] + anchor[i] * box[i + 2] for box in boxes)
                             for i in range(2))
            placement = Placement(anchor, position)
    return Adjustment(*values, transform, placement, preserve_y)


def fallback_transform(adjustment, origin):
    """Desired group geometry, before moving size changes into child smart axes."""
    sx = adjustment.width / 100 if adjustment.width is not None else 1.0
    sy = adjustment.height / 100 if adjustment.height is not None else 1.0
    if sx <= 0 or sy <= 0:
        raise InputError("Estimated size for the composite fallback is not positive.")
    x, y = origin
    scale = (sx, 0, 0, sy, x * (1 - sx), y * (1 - sy))
    return compose(adjustment.transform, scale)


def place_components(components, placement):
    """Translate an attached, interpolated group together, preserving its layout."""
    if placement is None:
        return
    boxes = [component_box(component) for component in components]
    if not boxes or any(box is None for box in boxes):
        raise InputError("Cannot measure the generated component group.")
    lower = [min(box[i] for box in boxes) for i in range(2)]
    upper = [max(box[i] + box[i + 2] for box in boxes) for i in range(2)]
    delta = [0.0 if placement.position[i] is None else
             placement.position[i] - lower[i] - placement.anchor[i] * (upper[i] - lower[i])
             for i in range(2)]
    for component in components:
        a, b, c, d, x, y = component.transform
        component.transform = (a, b, c, d, x + delta[0], y + delta[1])


def glyph_for_token(font, token):
    if len(token) == 1:
        glyph = font.glyphs["uni%04X" % ord(token)]
        if glyph is not None:
            return glyph
        # Glyphs uses uXXXXX for many supplementary-plane characters.
        if ord(token) > 0xFFFF:
            glyph = font.glyphs["u%X" % ord(token)]
            if glyph is not None:
                return glyph
        glyph = font.glyphs[token]
        if glyph is not None:
            return glyph
        # Also honor custom names and secondary Unicode assignments.
        code = "%04X" % ord(token)
        for glyph in font.glyphs:
            if code in (getattr(glyph, "unicodes", None) or [getattr(glyph, "unicode", None)]):
                return glyph
    return font.glyphs[token]


def glyph_unicodes(glyph):
    codes = getattr(glyph, "unicodes", None)
    if codes:
        return list(codes)
    code = getattr(glyph, "unicode", None)
    return [code] if code else []


def apply_aliases(font, aliases):
    """Add secondary Unicodes after generation, never replacing another glyph."""
    if not aliases:
        return []
    owners = {}
    for glyph in font.glyphs:
        for code in glyph_unicodes(glyph):
            owners.setdefault(int(code, 16), []).append(glyph)

    def resolve(character, visited):
        matches = owners.get(ord(character), [])
        if len(matches) > 1:
            raise InputError("Reference codepoint is assigned to multiple glyphs: " + character)
        if matches:
            return matches[0]
        glyph = glyph_for_token(font, character)
        if glyph is not None:
            return glyph
        if character in visited:
            raise InputError("Circular alias reference: " + " → ".join(visited + [character]))
        if character in aliases:
            return resolve(aliases[character], visited + [character])
        raise InputError("Missing referenced glyph: " + character)

    added = []
    for target, reference in aliases.items():
        try:
            glyph = resolve(reference, [target])
            existing = owners.get(ord(target), [])
            if any(owner.name != glyph.name for owner in existing):
                raise InputError("U+%04X already belongs to %s" %
                                 (ord(target), ", ".join(owner.name for owner in existing)))
            codes = glyph_unicodes(glyph)
            if ord(target) in {int(code, 16) for code in codes}:
                print("Alias already assigned: %s → %s" % (target, glyph.name))
                continue
            code = "%04X" % ord(target)
            # Assign the whole list through Glyphs' setter so its Unicode lookup
            # cache is updated, retaining the primary and all secondary values.
            glyph.unicodes = codes + [code]
            owners[ord(target)] = [glyph]
            added.append((target, glyph.name))
            print("Added Unicode: %s U+%s → %s" % (target, code, glyph.name))
        except InputError as error:
            print("Skipping alias %s 同「%s」: %s" % (target, reference, error))
    return added


def designated_name(radicals, token, position):
    mapping = radicals.get(token)
    if mapping is None:
        return None
    name = mapping.get(position, mapping.get("general"))
    if name is None:
        raise InputError("No %s/general glyph designated for %s" % (position, token))
    return name


def source_components(font, radicals, token, position, master_id, component_factory):
    name = designated_name(radicals, token, position)
    if name is not None:
        glyph = font.glyphs[name]
        if glyph is None:
            raise InputError("Missing designated component: " + name)
        if glyph.smartComponentAxes:
            if glyph.layers[master_id] is None:
                raise InputError("Missing master %s in %s" % (master_id, name))
            return Source([component_factory(name)], glyph)
        # Some entries in radicals.txt are composite characters, not smart glyphs.
        # Expand those by the same strict rule as an unlisted character.
    else:
        glyph = glyph_for_token(font, token)
    if glyph is None:
        raise InputError("Missing component glyph for " + token)
    layer = glyph.layers[master_id]
    if layer is None or layer.paths or not layer.components:
        raise InputError("%s must contain only smart components, with no raw contours (%s)."
                         % (glyph.name, master_id))
    parts = []
    for component in layer.components:
        base = font.glyphs[component.componentName]
        if base is None or not base.smartComponentAxes:
            raise InputError("%s contains a non-smart component: %s"
                             % (glyph.name, component.componentName))
        parts.append(Subpart(base, component_sample(component, master_id)))
    return Source([component.copy() for component in layer.components], parts=parts)


def prompt_text(title, message, default=""):
    """Modal Cocoa prompt works in both the Scripts menu and Macro Panel."""
    from AppKit import NSAlert, NSTextField
    alert = NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    alert.addButtonWithTitle_("Continue")
    alert.addButtonWithTitle_("Cancel")
    field = NSTextField.alloc().initWithFrame_(((0, 0), (340, 24)))
    field.setStringValue_(default)
    alert.setAccessoryView_(field)
    alert.window().setInitialFirstResponder_(field)
    if alert.runModal() != 1000:
        return None
    return str(field.stringValue()).strip()


def read_reference_layouts(path):
    """Existing character layouts only; new targets always use new_glyphs.txt.

    Known enclosures/ambiguous alternatives get a None hint and are excluded.
    A missing dictionary is allowed: conservative geometry is then used.
    """
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.strip().split("\t")
            if len(fields) < 5 or fields[0].startswith("#"):
                continue
            alternatives = [p.strip() for p in fields[4].split("/")]
            operators = {p[0] for p in alternatives if p and p[0] in IDS_ARITY}
            if operators:
                result[fields[0]] = (next(iter(operators)) if len(operators) == 1
                                    and all(p and p[0] in operators for p in alternatives) else None)
    return result


def reference_pair(layer, hint="unknown"):
    """Use known layout metadata; infer only clearly separated unknown layouts."""
    if layer is None or layer.paths or len(layer.components) != 2:
        return None
    if hint != "unknown" and hint not in POSITIONS:
        return None
    components = list(layer.components)
    centers = []
    boxes = []
    for component in components:
        bounds = component.bounds
        if bounds is None or bounds.size.width <= 0 or bounds.size.height <= 0:
            return None
        x, y, w, h = bounds.origin.x, bounds.origin.y, bounds.size.width, bounds.size.height
        if not all(math.isfinite(v) for v in (x, y, w, h)):
            return None
        boxes.append((x, y, x + w, y + h))
        centers.append((x + w / 2, y + h / 2))
    dx = centers[1][0] - centers[0][0]
    dy = centers[1][1] - centers[0][1]
    a, b = boxes
    contains = lambda a, b: a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]
    if contains(a, b) or contains(b, a):
        return None
    if hint == "unknown":
        overlap_x = min(a[2], b[2]) - max(a[0], b[0])
        overlap_y = min(a[3], b[3]) - max(a[1], b[1])
        if overlap_x <= 0 and overlap_y > 0:
            hint = "⿰"
        elif overlap_y <= 0 and overlap_x > 0:
            hint = "⿱"
        else:
            return None
    if hint == "⿰" and abs(dx) > 1e-6:
        return "⿰", components if dx > 0 else components[::-1]
    if hint == "⿱" and abs(dy) > 1e-6:
        return "⿱", components if dy < 0 else components[::-1]
    return None


def reference_index(font, layouts=None):
    """Snapshot before creation, so generated glyphs never enter the statistics."""
    index = {}
    layouts = layouts or {}
    skipped = Counter()
    for glyph in font.glyphs:
        # Component construction glyphs are not example characters.
        if not glyph.unicode:
            continue
        character = chr(int(glyph.unicode, 16))
        hint = layouts.get(character, "unknown")
        for master in font.masters:
            try:
                pair = reference_pair(glyph.layers[master.id], hint)
            except (ValueError, AttributeError) as error:
                skipped[str(error)] += 1
                continue
            if pair is None:
                continue
            layout, components = pair
            try:
                samples = tuple(component_sample(c, master.id) for c in components)
            except InputError as error:
                skipped[str(error)] += 1
                continue
            for side, component in enumerate(components):
                key = (master.id, layout, side, component.componentName)
                index.setdefault(key, []).append(samples)
    for reason, count in skipped.items():
        print("Excluded %d reference layer(s): %s" % (count, reason))
    return index


def partner_names(radicals, token, position, font):
    """Match the actual designated glyph, including a one-child Unicode fallback."""
    name = designated_name(radicals, token, position)
    if name is not None:
        return name
    glyph = glyph_for_token(font, token)
    return glyph.name if glyph is not None else token


def matching_samples(index, master_id, layout, side, name):
    # Different alternate drawings can have unrelated origins and axis ranges.
    # Pooling them by a name prefix corrupts the partner's statistics.
    return index.get((master_id, layout, side, name), [])


def choose_current(rows, prompt=prompt_text):
    candidates = current_candidates(rows)
    if len(candidates) == 1:
        return candidates[0]
    leaves = list(dict.fromkeys(token for _, parts in rows for token in parts
                               if token not in IDS_ARITY))
    allowed = candidates or leaves
    if not allowed:
        raise InputError("No components found in the second column.")
    while True:
        answer = prompt("Choose current component",
                        "The counting/radical rule is ambiguous. Enter one of: "
                        + ", ".join(allowed), allowed[0])
        if answer is None:
            return None
        if answer in allowed:
            return answer


def prepare_jobs(font, rows, radicals, current, component_factory):
    """Resolve all sources first, so an invalid fallback stops before any edit."""
    jobs = []
    seen = set()
    for target, parts in rows:
        if isinstance(parts, Alias):
            continue
        if target in seen or glyph_for_token(font, target) is not None:
            print("Skipping existing/duplicate glyph: " + target)
            continue
        seen.add(target)
        try:
            layout, leaves = flat_layout(parts)
        except InputError as error:
            print("Skipping %s: %s" % (target, error))
            continue
        positions = POSITIONS.get(layout, ("general",) * len(leaves))
        layers = {}
        try:
            for master in font.masters:
                layers[master.id] = []
                for token, position in zip(leaves, positions):
                    try:
                        source = source_components(font, radicals, token, position,
                                                   master.id, component_factory)
                    except InputError as error:
                        if token == current:
                            raise InvalidCurrentComponent(str(error)) from error
                        raise
                    layers[master.id].append(source)
        except InvalidCurrentComponent:
            raise
        except InputError as error:
            print("Skipping %s: %s" % (target, error))
            continue
        current_sides = [i for i, token in enumerate(leaves) if token == current]
        side = current_sides[0] if len(current_sides) == 1 and layout in POSITIONS else None
        jobs.append((target, layout, leaves, layers, side))
    return jobs


def prepare_components(source, adjustment, origin):
    values = {}
    outer = IDENTITY
    if adjustment is not None:
        if source.glyph is None:
            outer = fallback_transform(adjustment, origin)
        else:
            outer = adjustment.transform
            axes = smart_axes(source.glyph)
            for dimension in ("Width", "Height"):
                value = getattr(adjustment, dimension.lower())
                if dimension in axes and value is not None:
                    values[axis_id(axes[dimension])] = value
                elif dimension not in axes and value is not None:
                    print("  %s has no %s axis; keeping that dimension unchanged."
                          % (source.glyph.name, dimension))
    result = []
    for index, source_component in enumerate(source.components):
        component = source_component.copy()
        component.automaticAlignment = False
        transform = compose(outer, tuple(source_component.transform))
        placement = None
        component_values = values.copy()
        if adjustment is not None and source.glyph is None:
            if source.parts is None:
                raise InputError("Missing attached-source smart data for the composite.")
            part = source.parts[index]
            if part.sample.bounds is None:
                raise InputError("Missing source bounds for " + source_component.componentName)
            axes = smart_axes(part.glyph)
            inner = tuple(source_component.transform)
            # Convert the group compression to the child's local directions.
            # This also handles rotated or sheared children. Only the requested
            # smart sizing is absorbed; ordinary reference transforms remain.
            sx = adjustment.width / 100 if adjustment.width is not None else 1.0
            sy = adjustment.height / 100 if adjustment.height is not None else 1.0
            factors = []
            for dimension, column in (("Width", inner[:2]), ("Height", inner[2:4])):
                length = math.hypot(*column)
                if length < 1e-12:
                    raise InputError("Singular source transform: " + source_component.componentName)
                factor = math.hypot(sx * column[0], sy * column[1]) / length
                if dimension in axes:
                    value = getattr(part.sample, dimension.lower()) * factor
                    if not math.isfinite(value):
                        raise InputError("Non-finite smart value in " + part.glyph.name)
                    if abs(factor - 1) > 1e-12:
                        component_values[axis_id(axes[dimension])] = value
                    factors.append(factor)
                else:
                    factors.append(1.0)
                    if abs(factor - 1) > 1e-9:
                        print("  %s has no %s axis; using its ordinary transform for that direction."
                              % (part.glyph.name, dimension))
            # Remove the sizing already supplied by smart interpolation, avoiding
            # a second compression of the outline and its stroke thickness.
            a, b, c, d, x, y = transform
            transform = (a / factors[0], b / factors[0], c / factors[1], d / factors[1], x, y)
            x, y, w, h = part.sample.bounds
            position = transform_point(outer, (x + w / 2, y + h / 2))
            if adjustment.preserve_y:
                position = (position[0], None)
            placement = Placement((.5, .5), position)
        result.append((component, transform, component_values, placement))
    return result


def log_statistics(samples, side):
    cohort = [pair[side] for pair in samples]
    fields = []
    for dimension in ("width", "height"):
        values = [getattr(s, dimension) for s in cohort if getattr(s, dimension) is not None]
        if values:
            fields.append("%s mean=%.3f std=%.3f n=%d" %
                          (dimension, mean(values), pstdev(values), len(values)))
    for i, name in ((4, "x"), (5, "y")):
        values = [s.transform[i] for s in cohort]
        fields.append("%s mean=%.3f std=%.3f" % (name, mean(values), pstdev(values)))
    print("  Side %d: %s" % (side + 1, "; ".join(fields)))


def generate(font, jobs, radicals, current, index, glyph_factory, prompt=prompt_text):
    ratings = {}
    created = []
    for target, layout, leaves, sources, current_side in jobs:
        if current_side is not None and layout not in ratings:
            dimension = "width" if layout == "⿰" else "height"
            validation_message = ""
            while True:
                answer = prompt("Component %s weight" % dimension,
                                "%s: rate the %s of %s (0 < x < 10; decimals allowed). "
                                "Higher values give this component more space."
                                % (target, dimension, current) + validation_message, "5")
                if answer is None:
                    print("Cancelled. Already generated glyphs are kept.")
                    return created
                try:
                    ratings[layout] = rating_quantile(answer)
                    break
                except InputError as error:
                    print(error)
                    validation_message = "\n\n" + str(error)

        prepared = {}
        try:
            for master in font.masters:
                adjustments = [None] * len(leaves)
                if current_side is not None:
                    partner_side = 1 - current_side
                    partner = partner_names(radicals, leaves[partner_side],
                                            POSITIONS[layout][partner_side], font)
                    partner_source = sources[master.id][partner_side]
                    if partner_source.glyph is None and len(partner_source.components) == 1:
                        partner = partner_source.components[0].componentName
                    samples = matching_samples(index, master.id, layout, partner_side, partner)
                    print("%s / %s: %d reference glyphs for %s"
                          % (target, master.name, len(samples), partner))
                    if samples:
                        for side in range(2):
                            z = ratings[layout] * (1 if side == current_side else -1)
                            log_statistics(samples, side)
                            source = sources[master.id][side]
                            # The partner is the same designated smart drawing
                            # as the references. Its mean matrix is transferable;
                            # different current drawings and expanded groups need
                            # positions measured in their shared rendered space.
                            align_side = side if side == current_side or source.glyph is None else None
                            adjustments[side] = smart_estimate(
                                [pair[side] for pair in samples], layout, z, align_side,
                                current=(side == current_side))
                    else:
                        print("  No examples; keeping original component transforms.")
                else:
                    print("%s / %s: no unique current component in a two-part layout; keeping source transforms."
                          % (target, master.name))
                prepared[master.id] = []
                for side, source in enumerate(sources[master.id]):
                    adjustment = adjustments[side]
                    group = prepare_components(
                        source, adjustment, (float(font.upm), float(master.descender)))
                    prepared[master.id].append((group, adjustment.placement if adjustment else None))
        except InputError as error:
            print("Skipping %s: %s" % (target, error))
            continue

        if len(target) == 1:
            name = ("uni%04X" if ord(target) <= 0xFFFF else "u%X") % ord(target)
            glyph = glyph_factory(name)
            glyph.unicode = "%04X" % ord(target)
        else:
            glyph = glyph_factory(target)
        # Recheck because a modal prompt lets the font's state change.
        if glyph_for_token(font, target) is not None or font.glyphs[glyph.name] is not None:
            print("Skipping glyph created since preflight: " + target)
            continue
        font.glyphs.append(glyph)
        try:
            for master in font.masters:
                layer = glyph.layers[master.id]
                for group, placement in prepared[master.id]:
                    for component, transform, values, child_placement in group:
                        layer.components.append(component)
                        # Set after insertion so Glyphs has the correct parent/master.
                        component.automaticAlignment = False
                        for key, value in values.items():
                            component.smartComponentValues[key] = value
                        component.transform = transform
                        # Measure this child's new smart interpolation before
                        # inserting the next one, then restore its group position.
                        place_components([component], child_placement)
                    place_components([component for component, _, _, _ in group], placement)
                layer.width = font.upm
        except Exception:
            del font.glyphs[glyph.name]
            raise
        created.append(glyph.name)
        font.newTab("/" + glyph.name)
        print("Created: " + glyph.name)
    return created


def main():
    from GlyphsApp import Glyphs, GSComponent, GSGlyph, Message

    font = Glyphs.font
    try:
        if font is None or not font.filepath:
            raise InputError("Open and save a font in the project directory first.")
        directory = os.path.dirname(font.filepath)
        rows, aliases = split_definitions(read_definitions(os.path.join(directory, "out", "new_glyphs.txt")))
        if rows and not all(glyph_for_token(font, target) is not None for target, _ in rows):
            radicals = read_radicals(os.path.join(directory, "src", "radicals.txt"))
            current = choose_current(rows)
            if current is None:
                return
            print("Current component: " + current)
            jobs = prepare_jobs(font, rows, radicals, current, GSComponent)
            if jobs:
                layouts = read_reference_layouts(os.path.join(directory, "src", "dictionary.txt"))
                # The explicit prescription always wins for characters also in this file.
                layouts.update({target: parts[0] for target, parts in rows if parts})
                index = reference_index(font, layouts)
                created = generate(font, jobs, radicals, current, index, GSGlyph)
                print("Created glyphs: " + ", ".join(created))
            else:
                print("No missing glyphs to create.")
        elif rows:
            print("No missing glyphs to create.")
        added = apply_aliases(font, aliases)
        if aliases:
            print("Added Unicode aliases: %d" % len(added))
    except (InputError, OSError) as error:
        print("Stopped: " + str(error))
        Message("Glyph generation stopped", str(error))


if __name__ == "__main__":
    main()
