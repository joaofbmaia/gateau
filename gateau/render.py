"""Bus-view renderer (notation v1.2). Produces an SVG string, or an HTML page around it.

Layout is rule-based, not optimised: the rules are the ones in docs/notation-v1.html.
  x      flow order (Design.order), one column per stage, route or merge
  y      carrier bands in declaration order; rows inside a band ordered by the stage that creates them
  above  state pills, packed into as few lines as fit; taps from more than one band away become stubs
  below  the gutter: feedback edges, shortest span nearest the bands
  hue    clock domain only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Optional

from .checks import Finding
from .model import Design, Field, Merge, Route, Stage

LABEL_W, X0, COL, BOX_W = 118, 132, 104, 72
ROW_H, BAND_HEAD, BAND_PAD, BAND_GAP = 24, 20, 10, 16
PILL_H, PILL_GAP, LANE_H = 18, 8, 22
READ_X, TAP_X, EMIT_X = -14, -2, 22  # x slots in a column, from its centre: read connector, state taps, emits
DOT_R = 3.2
BOX_CHAR_W = 7.0                  # advance of one box-label character (11.5 px bold monospace)
STUB_H = 13                       # height of a state stub
INSET = 12                        # slant of the route / merge trapezoids
MAX_ROWS = 18                     # collapse groups when a view would exceed this many rows
GLYPH = {"pass": "✓", "fail": "✗", "unchecked": "?", "info": "·"}
SEVERITY = ["fail", "unchecked", "pass", "info"]          # a badge shows the first of these; info is not a verdict, so it shows only alone


def _t(s) -> str:
    return escape(str(s), quote=True)


@dataclass
class Row:
    key: str                      # field path, group key "car.group.*", or "car:" for a field-less carrier
    label: str
    width: str
    fields: list[Field]
    y: float = 0.0


@dataclass
class Band:
    carrier: str
    rows: list[Row]
    top: float = 0.0
    bottom: float = 0.0


@dataclass
class Box:
    name: str
    x: float
    y0: float
    y1: float
    kind: str = "stage"           # stage | route | merge
    band_top: int = 0             # index of the topmost band the box touches


@dataclass
class Layout:
    width: float = 0.0
    height: float = 0.0
    bands: list[Band] = field(default_factory=list)
    rowmap: dict[str, Row] = field(default_factory=dict)      # field path → row
    boxes: dict[str, Box] = field(default_factory=dict)
    col: dict[str, int] = field(default_factory=dict)
    bx: dict[str, float] = field(default_factory=dict)        # boundary → x
    pills: dict[str, tuple[float, float, float]] = field(default_factory=dict)   # state → (x0, x1, y)
    spans: dict[str, tuple[float, Optional[float]]] = field(default_factory=dict)          # row key → live (x0, x1)


# ── helpers ───────────────────────────────────────────────────────────────

def _items(d: Design):
    for n in d.order:
        yield n, d.stages.get(n) or d.routes.get(n) or d.merges.get(n)


def _cx(L: Layout, name: str) -> float:
    return X0 + 46 + L.col[name] * COL


def _width_label(d: Design, f: Field) -> str:
    w = "?" if f.elem_bits is None else str(f.elem_bits)
    return "·".join(list(f.axes) + [w]) if f.axes else w


def _stage_fields(d: Design, s: Stage, attr: str, carrier: str) -> list[Field]:
    out = []
    for ref in getattr(s, attr):
        try:
            fs = d.resolve(ref, carrier)
        except Exception:
            continue
        out += fs
    return out


def _touch(d: Design, item) -> dict[str, set[str]]:
    """Field paths an item reads, writes, creates and consumes."""
    r = {"reads": set(), "writes": set(), "creates": set(), "consumes": set()}
    if isinstance(item, Stage):
        for attr in ("reads", "reads_at_head"):
            r["reads"] |= {f.path for f in _stage_fields(d, item, attr, item.on)}
        r["writes"] |= {f.path for f in _stage_fields(d, item, "writes", item.on)}
        r["consumes"] |= {f.path for f in _stage_fields(d, item, "consumes", item.on)}
        r["creates"] |= {f.path for f in _stage_fields(d, item, "creates", item.out or item.on)}
        if item.broadcast:
            for ref in item.broadcast[0]:
                r["writes"] |= {f.path for f in d.resolve(ref, item.on)}
    elif isinstance(item, Route):
        r["creates"] |= {f.path for ref in item.creates for f in d.resolve(ref)}
        r["consumes"] |= {f.path for ref in item.consumes for f in d.resolve(ref)}
        if item.selector_field:
            r["reads"] |= {f.path for f in d.resolve(item.selector_field)}
    elif isinstance(item, Merge):
        r["creates"] |= {f.path for ref in item.creates for f in d.resolve(ref)}
    return r


def _producers(d: Design, carrier: str) -> list[str]:
    """Items that produce items onto a carrier: transfer stages, routes and merges."""
    out = []
    for n, it in _items(d):
        if isinstance(it, Stage) and it.out == carrier:
            out.append(n)
        elif isinstance(it, Route) and it.dst == carrier:
            out.append(n)
        elif isinstance(it, Merge) and it.dst == carrier and not _merge_on_dst(d, it):
            out.append(n)
    par = d.carriers[carrier].parent
    return out or (_producers(d, par) if par else [])


def _merge_on_dst(d: Design, m: Merge) -> bool:
    """A merge whose sources emit straight onto the destination carrier (drawn as a small mux on it)."""
    srcs = [d.stages.get(i.source) for i in m.inputs]
    return all(s is not None and any(e.carrier == m.dst for e in s.emits) for s in srcs)


def _merge_input_carrier(d: Design, m: Merge) -> Optional[str]:
    s = d.stages.get(m.inputs[0].source)
    return (s.out or s.on) if s else None


def _domain_class(d: Design, carrier: str) -> str:
    dom = d.carriers[carrier].domain.split("[")[0]
    idx = d.domains.index(dom) if dom in d.domains else 0
    return f"d{min(idx, 4)}"


def _active(item, mode: Optional[str]) -> bool:
    modes = getattr(item, "modes", None)
    return mode is None or modes is None or mode in modes


def _carriers_touched(d: Design, item) -> set[str]:
    out = set()
    if isinstance(item, Stage):
        out |= {item.on, item.out} | {e.carrier for e in item.emits}
        for attr in ("reads", "reads_at_head", "writes", "creates", "consumes"):
            out |= {r.split(".", 1)[0] for r in getattr(item, attr) if r.split(".", 1)[0] in d.carriers}
    elif isinstance(item, Route):
        out |= {item.src, item.dst}
    else:
        out |= {item.dst, _merge_input_carrier(d, item)}
    return out - {None}


def _family(d: Design, c: str) -> str:
    while d.carriers[c].parent:
        c = d.carriers[c].parent
    return c


def _source(d: Design, c: str) -> Optional[str]:
    """The carrier a carrier's items come from: the input of its first producer."""
    for n, it in _items(d):
        if isinstance(it, Stage) and it.out == c and it.on != c:
            return it.on
        if isinstance(it, Route) and it.dst == c:
            return it.src
        if isinstance(it, Merge) and it.dst == c and not _merge_on_dst(d, it):
            return _merge_input_carrier(d, it)
    return None


def carrier_order(d: Design, col: dict[str, int]) -> list[str]:
    """Bands top to bottom: rings first, then a depth-first walk of the flow. Each family (a parent and
    its children) is followed by the families its items flow into, so chains stay adjacent and a box
    crosses tracks that are not yet live rather than live ones."""
    first = {}
    for n, it in _items(d):
        for c in _carriers_touched(d, it):
            first.setdefault(c, col[n])
    decl = list(d.carriers)
    late = len(col)
    fams: dict[str, list[str]] = {}
    for c in decl:
        fams.setdefault(_family(d, c), []).append(c)
    fkey = {r: min(first.get(c, late) for c in cs) for r, cs in fams.items()}
    src_fam = {}
    for r, cs in fams.items():
        srcs = [_source(d, c) for c in cs]
        outside = [_family(d, x) for x in srcs if x and _family(d, x) != r]
        src_fam[r] = outside[0] if outside else None

    def k(r):
        return (not d.carriers[r].ring, fkey[r], decl.index(r))
    out, seen = [], set()

    def visit(r):
        if r in seen:
            return
        seen.add(r)
        out.extend(sorted(fams[r], key=lambda c: (c != r, first.get(c, late), decl.index(c))))
        for ch in sorted((x for x in fams if src_fam[x] == r), key=k):
            visit(ch)
    for r in sorted((x for x in fams if src_fam[x] is None), key=k):
        visit(r)
    for r in sorted(fams, key=k):          # cycles in the flow: whatever is left
        visit(r)
    return out


def _cover(bx: Box, y: float) -> None:
    if bx.kind == "stage":
        bx.y0, bx.y1 = min(bx.y0, y - 11), max(bx.y1, y + 11)
    else:                                    # trapezoids: keep the row clear of the slanted corner
        bx.y0, bx.y1 = min(bx.y0, y - 11 - INSET), max(bx.y1, y + 11 + INSET)


# ── layout ────────────────────────────────────────────────────────────────

def layout(d: Design) -> Layout:
    L = Layout()
    for i, (n, _) in enumerate(_items(d)):
        L.col[n] = i
    touches = {n: _touch(d, it) for n, it in _items(d)}

    creator = {}
    for n, t in touches.items():
        for p in t["creates"]:
            creator.setdefault(p, n)

    total_fields = sum(max(1, len(d.carrier_fields(c))) for c in d.carriers)
    collapse = total_fields > MAX_ROWS

    y = 0.0
    for c in carrier_order(d, L.col):
        fs = d.carrier_fields(c)
        order = {f.path: (L.col.get(creator.get(f.path), -1), i) for i, f in enumerate(fs)}
        fs = sorted(fs, key=lambda f: order[f.path])
        rows: list[Row] = []
        seen = set()
        for f in fs:
            if collapse and f.group and len([g for g in fs if g.group == f.group]) >= 3:
                if f.group in seen:
                    continue
                seen.add(f.group)
                members = [g for g in fs if g.group == f.group]
                bits = [d.bits(g) for g in members]
                w = f"{sum(bits)}" if None not in bits else "group"
                rows.append(Row(f"{c}.{f.group}.*", f"{f.group} ▸", w, members))
            else:
                rows.append(Row(f.path, f.name + (" ◆" if f.availability == "tail" else ""),
                                _width_label(d, f), [f]))
        if not rows:
            rows.append(Row(f"{c}:", c, "ring" if d.carriers[c].ring else "", []))
        band = Band(c, rows, top=y)
        ry = y + BAND_HEAD
        for r in rows:
            r.y = ry + ROW_H / 2
            ry += ROW_H
            for f in r.fields:
                L.rowmap[f.path] = r
            if not r.fields:
                L.rowmap[r.key] = r
        band.bottom = ry + BAND_PAD
        L.bands.append(band)
        y = band.bottom + BAND_GAP
    L.width = X0 + 46 + len(L.col) * COL + 90

    band_index = {b.carrier: i for i, b in enumerate(L.bands)}

    def band_rows(c):
        return L.bands[band_index[c]].rows

    # boxes
    for n, it in _items(d):
        t = touches[n]
        cx = _cx(L, n)
        ys = []
        if isinstance(it, Stage):
            for p in t["writes"] | t["consumes"] | t["creates"]:
                if p in L.rowmap:
                    ys.append(L.rowmap[p].y)
            if it.out and it.out != it.on:
                # transfer: from the input-band row nearest the output band to the rows it creates;
                # other reads hang off a connector
                down = band_index[it.out] > band_index[it.on]
                near = [L.rowmap[p].y for p in t["reads"] if p in L.rowmap and L.rowmap[p] in band_rows(it.on)]
                if not near:
                    near = [r.y for r in band_rows(it.on)]
                ys += [max(near) if down else min(near)]
                made = [y for y in ys if y not in near]
                if not any(r.y in made for r in band_rows(it.out)):
                    ys += [band_rows(it.out)[0].y if down else band_rows(it.out)[-1].y]
            if not ys and it.buffer:
                ys = [r.y for r in band_rows(it.on)]
            if not ys:
                ys = [band_rows(it.on)[0].y]
            bands_touched = {it.on} | ({it.out} if it.out else set())
        elif isinstance(it, Route):
            ys = [r.y for r in band_rows(it.src)] + [r.y for r in band_rows(it.dst)]
            bands_touched = {it.src, it.dst}
            ys = [min(ys) - 3, max(ys) + 3]
        else:
            if _merge_on_dst(d, it):
                ys = [band_rows(it.dst)[0].y]
                bands_touched = {it.dst}
            else:
                src = _merge_input_carrier(d, it)
                fam = [c for c in d.carriers if c == src or d.carriers[c].parent == src]
                ys = [r.y for c in fam for r in band_rows(c)] + [r.y for r in band_rows(it.dst)]
                bands_touched = set(fam) | {it.dst}
                ys = [min(ys) - 3, max(ys) + 3]
        y0, y1 = min(ys) - 11, max(ys) + 11
        if y1 - y0 < 34 and isinstance(it, Stage) and (it.broadcast or it.buffer):
            y0, y1 = (y0 + y1) / 2 - 17, (y0 + y1) / 2 + 17
        kind = "stage" if isinstance(it, Stage) else ("route" if isinstance(it, Route) else "merge")
        L.boxes[n] = Box(n, cx - BOX_W / 2, y0, y1, kind, min(band_index[b] for b in bands_touched))

    # Every live row must start on a box and end on a box or on its read dot. Rows are placed
    # by column, boxes by the rows they name, so reconcile the two here: an end that the item
    # reads from outside its box stops at the dot on the read connector; anything else grows
    # the box to cover the row.
    items = dict(_items(d))
    for b in L.bands:
        for r in b.rows:
            start, end = _row_owners(d, L, items, touches, r)
            x0 = X0 if start is None else _cx(L, start) + BOX_W / 2
            x1 = None                        # the right edge, resolved once the width is final
            if start is not None:
                _cover(L.boxes[start], r.y)
            if end is not None:
                bx = L.boxes[end]
                read = {f.path for f in r.fields} & touches[end]["reads"]
                if read and not bx.y0 <= r.y <= bx.y1:
                    x1 = _cx(L, end) + READ_X
                else:
                    _cover(bx, r.y)
                    x1 = _cx(L, end) - BOX_W / 2
            L.spans[r.key] = (x0, x1)

    # boundaries
    outs, ins = {}, {}
    for n, it in _items(d):
        btw = getattr(it, "between", None)
        if btw:
            ins.setdefault(btw[0], []).append(_cx(L, n) - COL / 2)
            outs.setdefault(btw[1], []).append(_cx(L, n) + COL / 2 - 6)
    for b in d.boundaries:
        if b in outs:
            L.bx[b] = max(outs[b])
        elif b in ins:
            L.bx[b] = min(ins[b])

    # state pills, packed into lines
    lines: list[list[tuple[float, float]]] = []
    spans = {}
    for st in d.states.values():
        xs = [_cx(L, n) for n, it in _items(d) if _state_taps(it, st.name)]
        if not xs:
            continue
        label = _pill_label(st)
        x0 = min(xs) - 34
        x1 = max(max(xs) + 34, x0 + len(label) * 6.4 + 24)
        for i, line in enumerate(lines):
            if all(x1 + 12 < a or x0 > b + 12 for a, b in line):
                line.append((x0, x1)); spans[st.name] = (x0, x1, i); break
        else:
            lines.append([(x0, x1)]); spans[st.name] = (x0, x1, len(lines) - 1)
    top = 16 + len(lines) * (PILL_H + PILL_GAP) + 18
    for name, (x0, x1, i) in spans.items():
        L.pills[name] = (x0, x1, 16 + i * (PILL_H + PILL_GAP))
    # shift everything below the pills
    for b in L.bands:
        b.top += top; b.bottom += top
        for r in b.rows:
            r.y += top
    for bx in L.boxes.values():
        bx.y0 += top; bx.y1 += top
    L.width = max(L.width, max((p[1] for p in L.pills.values()), default=0) + 20)
    gutter_lanes = len(d.feedback)
    L.height = L.bands[-1].bottom + 18 + max(1, gutter_lanes) * LANE_H + 12 + 20
    return L


def _state_taps(item, state: str):
    taps = []
    for attr in ("state_reads", "state_writes", "requires"):
        for t in getattr(item, attr, ()):
            if t.state == state:
                taps.append((attr, t))
    return taps


def _pill_label(st) -> str:
    s = st.name
    if st.fields:
        s += " · {" + ", ".join(st.fields) + "}"
    if st.cyclic:
        s += f" · ↻ {st.cyclic}"
    if st.epoch:
        s += f" · epoch at {st.epoch.swap_point}"
    if st.writer == "shared":
        s += " · shared"
    return s


# ── drawing ───────────────────────────────────────────────────────────────

def render_svg(d: Design, findings: Optional[list[Finding]] = None, mode: Optional[str] = None,
               overlay: Optional[str] = None) -> str:
    L = layout(d)
    cost = overlay == "cost"
    checks = overlay == "checks"
    o: list[str] = []
    a = o.append
    touches = {n: _touch(d, it) for n, it in _items(d)}
    items = dict(_items(d))
    band_index = {b.carrier: i for i, b in enumerate(L.bands)}

    fy = L.height
    # checks are an analysis of the drawing, not part of it: only the checks view shows them
    shown = list(findings or []) if checks else []
    fl = shown
    if fl:
        fy += 30 + len(fl) * 18
    a(f'<svg xmlns="http://www.w3.org/2000/svg" class="gateau{" ov-checks" if checks else ""}" '
      f'width="{L.width:.0f}" viewBox="0 0 {L.width:.0f} {fy:.0f}" role="img" aria-label="{_t(d.name)} bus view'
      f'{", mode " + mode if mode else ""}{", " + overlay + " overlay" if overlay else ""}">')
    a('<defs>' + ''.join(
        f'<marker id="g-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" '
        f'markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="ah-{k}"/></marker>'
        for k in ("ink", "mut", "d1", "d2", "d3", "d4")) + '</defs>')

    def fade(item) -> str:
        return "" if _active(item, mode) else ' class="off"'

    # bands
    for b in L.bands:
        car = d.carriers[b.carrier]
        h = b.bottom - b.top
        if car.index:
            a(f'<rect class="deck" x="{X0-4+8}" y="{b.top+8}" width="{L.width-X0-12}" height="{h}"/>'
              f'<rect class="deck" x="{X0-4+4}" y="{b.top+4}" width="{L.width-X0-12}" height="{h}"/>')
        a(f'<rect class="band" data-carrier="{_t(b.carrier)}" x="{X0-4}" y="{b.top}" width="{L.width-X0-12}" height="{h}"/>')
        live_end = max((_live_span(d, L, items, touches, r)[1] for r in b.rows), default=X0)
        for x0, x1 in _rigid_spans(d, L, b.carrier, live_end):
            a(f'<rect class="rigid" data-carrier="{_t(b.carrier)}" x="{x0:.0f}" y="{b.top}" width="{x1-x0:.0f}" height="{h}"/>')
        idx = f" ×{d.axes[car.index]}" if car.index else ""
        a(f'<text class="t-band" x="12" y="{b.top+12}">{_t(car.name + idx)} · {_t(car.domain)}</text>')
        for r in b.rows:
            width = r.width
            bits = [d.bits(f) for f in r.fields]
            if cost and r.fields and None not in bits:
                width = f"{sum(bits) * d.copies(b.carrier)} b"
            a(f'<text class="t-name" x="12" y="{r.y+4}">{_t(r.label)}</text>'
              f'<text class="t-w t-end" x="{LABEL_W-6}" y="{r.y+4}">{_t(width)}</text>'
              f'<line class="track" x1="{X0}" y1="{r.y}" x2="{L.width-20}" y2="{r.y}"/>')

    # boundaries
    for name, x in L.bx.items():
        bd = d.boundaries[name]
        lat = f" +{bd.latency}" if bd.after and isinstance(bd.latency, int) else ""
        mark = "» " if bd.coupling == "elastic" else ""
        a(f'<line class="edge" x1="{x:.0f}" y1="{L.bands[0].top-6}" x2="{x:.0f}" y2="{L.bands[-1].bottom}"/>'
          f'<text class="t-w t-mid" x="{x:.0f}" y="{L.bands[0].top-10}">{_t(mark + name + lat)}</text>')

    # rows: live segments
    for b in L.bands:
        dc = _domain_class(d, b.carrier)
        for r in b.rows:
            x0, x1 = _live_span(d, L, items, touches, r)
            if x1 <= x0:
                continue
            style = ""
            if cost and r.fields:
                bits = [d.bits(f) for f in r.fields]
                if None not in bits:
                    style = f' style="stroke-width:{max(1.2, sum(bits) * d.copies(b.carrier) * 0.06):.2f}"'
            cls = "msg" if not r.fields else f"lane {dc}"
            makers = [items[n] for n, t in touches.items() if {f.path for f in r.fields} & t["creates"]]
            if makers and not any(_active(m, mode) for m in makers):
                a('<g class="off">')
            else:
                a('<g>')
            if not r.fields:
                a(f'<line class="lane {dc}" x1="{x0:.0f}" y1="{r.y-2}" x2="{x1:.0f}" y2="{r.y-2}" style="stroke-width:1.1"/>'
                  f'<line class="lane {dc}" x1="{x0:.0f}" y1="{r.y+2}" x2="{x1:.0f}" y2="{r.y+2}" style="stroke-width:1.1"/>')
            else:
                a(f'<line class="{cls}" data-row="{_t(r.key)}" x1="{x0:.0f}" y1="{r.y}" x2="{x1:.0f}" y2="{r.y}"{style}/>')
            if any(f.availability == "tail" for f in r.fields):
                a(f'<polygon class="tail {dc}" points="{x0+6},{r.y-5} {x0+11},{r.y} {x0+6},{r.y+5} {x0+1},{r.y}"/>')
            a('</g>')

    # state pills and taps
    for name, (x0, x1, y) in L.pills.items():
        st = d.states[name]
        a(f'<g class="chk-state" data-subject="{_t(name)}"><rect class="pill" x="{x0:.0f}" y="{y}" width="{x1-x0:.0f}" height="{PILL_H}" rx="9"/>'
          f'<text class="t-w" x="{x0+12:.0f}" y="{y+13}" style="fill:var(--fg)">{_t(_pill_label(st))}</text></g>')
        for n, it in _items(d):
            for attr, t in _state_taps(it, name):
                bx = L.boxes[n]
                mine = [(s_, at) for s_ in L.pills for at, _ in _state_taps(it, s_)]
                i = mine.index((name, attr))
                x = _cx(L, n) + TAP_X + i * 10
                far = bx.band_top > 1 and st.writer == "out-of-flow"
                g = f'<g{fade(it)}>'
                if far:
                    lbl = name + (f".{t.sub}" if t.sub else "")
                    w = len(lbl) * 5.6 + 12
                    sx = x - 6                     # grows rightwards, clear of the read connector
                    sy = _free_y(L, items, touches, sx, sx + w, bx.y0 - 4, STUB_H)
                    a(g + f'<line class="conn" x1="{x}" y1="{bx.y0}" x2="{x}" y2="{sy+STUB_H}"/>'
                      f'<rect class="stub" data-stub="{_t(n)}" x="{sx:.0f}" y="{sy:.0f}" width="{w:.0f}" height="{STUB_H}" rx="6"/>'
                      f'<text class="t-stub" x="{sx+w/2:.0f}" y="{sy+10:.0f}">{_t(lbl)}</text></g>')
                elif attr == "state_writes":
                    a(g + f'<line class="conn" x1="{x}" y1="{bx.y0}" x2="{x}" y2="{y+PILL_H+1}" marker-end="url(#g-ink)"/></g>')
                else:
                    a(g + f'<line class="conn" x1="{x}" y1="{y+PILL_H}" x2="{x}" y2="{bx.y0}"/>'
                      f'<circle class="dot" cx="{x}" cy="{y+PILL_H}" r="3"/></g>')

    # read dots and connectors
    for n, it in _items(d):
        bx = L.boxes[n]
        cx = _cx(L, n)
        ys_above = [L.rowmap[p].y for p in touches[n]["reads"] if p in L.rowmap and L.rowmap[p].y < bx.y0]
        ys_below = [L.rowmap[p].y for p in touches[n]["reads"] if p in L.rowmap and L.rowmap[p].y > bx.y1]
        ys_in = [L.rowmap[p].y for p in touches[n]["reads"] if p in L.rowmap and bx.y0 <= L.rowmap[p].y <= bx.y1]
        g = [f'<g{fade(it)}>']
        if ys_above:
            g.append(f'<line class="conn" x1="{cx+READ_X}" y1="{min(ys_above)}" x2="{cx+READ_X}" y2="{bx.y0}"/>')
            g += [f'<circle class="dot" cx="{cx+READ_X}" cy="{yy}" r="3.2"/>' for yy in ys_above]
        if ys_below:
            g.append(f'<line class="conn" x1="{cx+READ_X}" y1="{max(ys_below)}" x2="{cx+READ_X}" y2="{bx.y1}"/>')
            g += [f'<circle class="dot" cx="{cx+READ_X}" cy="{yy}" r="3.2"/>' for yy in ys_below]
        g += [f'<circle class="dot" cx="{bx.x-5}" cy="{yy}" r="3.2"/>' for yy in ys_in]
        g.append('</g>')
        a(''.join(g))
        # emits
        if isinstance(it, Stage):
            for e in it.emits:
                ry = L.rowmap.get(f"{e.carrier}:") or (L.bands[band_index[e.carrier]].rows[0])
                ty = ry.y + (4 if ry.y > bx.y0 else -4)
                sy = bx.y0 if ry.y < bx.y0 else bx.y1
                a(f'<g{fade(it)}><line class="conn" x1="{cx+EMIT_X}" y1="{sy}" x2="{cx+EMIT_X}" y2="{ty}" marker-end="url(#g-ink)"/></g>')

    # boxes
    for n, it in _items(d):
        bx = L.boxes[n]
        h = bx.y1 - bx.y0
        label = n
        sub = ""
        if isinstance(it, Stage):
            if it.replicate:
                label += f" ×{it.replicate}"
            if it.broadcast:
                sub = f"Δ{it.broadcast[1]}"
            elif it.buffer and it.buffer.depth:
                sub = f"buf {it.buffer.depth}"
        elif isinstance(it, Route) and it.granularity.startswith("axis "):
            sub = "per " + it.granularity.split()[1]
        elif isinstance(it, Merge):
            sub = it.policy
        cls = "box-opt" if isinstance(it, Stage) and it.condition else "box"
        g = f'<g{fade(it)}>'
        if bx.kind == "stage":
            shape = f'<rect class="{cls}" x="{bx.x}" y="{bx.y0}" width="{BOX_W}" height="{h}" rx="3"/>'
        elif bx.kind == "route":
            k = INSET
            shape = (f'<polygon class="box" points="{bx.x},{bx.y0+k} {bx.x+BOX_W},{bx.y0} '
                     f'{bx.x+BOX_W},{bx.y1} {bx.x},{bx.y1-k}"/>')
        else:
            if _merge_on_dst(d, it):
                yc = (bx.y0 + bx.y1) / 2
                shape = (f'<polygon class="box" points="{bx.x+20},{yc-14} {bx.x+52},{yc-7} '
                         f'{bx.x+52},{yc+7} {bx.x+20},{yc+14}"/>')
            else:
                k = INSET
                shape = (f'<polygon class="box" points="{bx.x},{bx.y0} {bx.x+BOX_W},{bx.y0+k} '
                         f'{bx.x+BOX_W},{bx.y1-k} {bx.x},{bx.y1}"/>')
        ty = (bx.y0 + bx.y1) / 2 + 4
        if bx.kind == "merge" and _merge_on_dst(d, it):
            text = f'<text class="t-sub" x="{bx.x+58}" y="{ty+14}" style="text-anchor:start;fill:var(--fg)">{_t(n)} · {_t(it.policy)}</text>'
        else:
            fit = (f' textLength="{BOX_W - 8}" lengthAdjust="spacingAndGlyphs"'
                   if len(label) * BOX_CHAR_W > BOX_W - 8 else "")      # squeeze a label that would spill out
            text = f'<text class="t-box" x="{bx.x+BOX_W/2}" y="{ty - (6 if sub else 0)}"{fit}>{_t(label)}</text>'
            if sub:
                text += f'<text class="t-sub" x="{bx.x+BOX_W/2}" y="{ty+8}">{_t(sub)}</text>'

        a(g.replace("<g", f'<g data-item="{_t(n)}" data-kind="{bx.kind}"', 1) + shape + text + '</g>')

    # gutter: paths first, then labels on top with a halo
    gtop = L.bands[-1].bottom + 18
    a(f'<rect class="gutter" x="{X0-4}" y="{gtop}" width="{L.width-X0-12}" height="{max(1,len(d.feedback))*LANE_H+12}" rx="3"/>'
      f'<text class="t-note" x="12" y="{gtop+14}">gutter</text>')
    fbs = sorted(d.feedback, key=lambda f: abs(_end_x(L, f.src) - _end_x(L, f.dst)))
    labels = []
    for k, fb in enumerate(fbs):
        y = gtop + 20 + k * LANE_H
        sx, dx = _end_x(L, fb.src) + 6, _end_x(L, fb.dst) - 6
        sb = L.boxes.get(fb.src.split(".")[0])
        db = L.boxes.get(fb.dst.split(".")[0])
        sy = sb.y1 if sb else gtop
        dy = db.y1 + 2 if db else gtop
        cls = {"data": "fb-data", "ctrl": "fb-ctrl", "flow": "fb-flow"}[fb.kind]
        off = "" if mode is None or fb.modes is None or mode in fb.modes else ' class="off"'
        a(f'<g{off}><path class="{cls}" d="M{sx},{sy} L{sx},{y} L{dx},{y} L{dx},{dy}" marker-end="url(#g-mut)"/></g>')
        note = f"{fb.kind} · {fb.note}" if fb.note else fb.kind
        w = len(note) * 6.1
        lo, hi = min(sx, dx), max(sx, dx)
        if hi - lo > w + 24:
            labels.append(f'<g{off}><text class="t-w t-mid halo" x="{(lo+hi)/2:.0f}" y="{y-4}">{_t(note)}</text></g>')
        else:
            labels.append(f'<g{off}><text class="t-w halo" x="{hi+8:.0f}" y="{y-4}">{_t(note)}</text></g>')
    o.extend(labels)

    # finding badges on their subjects, and the list below the gutter
    if shown:
        # one badge per subject: the worst status, a count when there are several, all of them in the tooltip
        groups: dict[tuple[float, float], list[Finding]] = {}
        for f in findings:
            target = _subject_box(d, L, f)
            if target is not None:
                groups.setdefault(target, []).append(f)
        for (x, y), fs_ in groups.items():
            st = min((f.status for f in fs_), key=SEVERITY.index)
            tip = "&#10;".join(f"{GLYPH[f.status]} {_t(f.check)} · {_t(f.subject)}: {_t(f.message)}" for f in fs_)
            count = (f'<text class="t-count" x="{x+9:.0f}" y="{y-5:.0f}">{len(fs_)}</text>' if len(fs_) > 1 else "")
            a(f'<g class="chk" data-findings="{len(fs_)}"><circle class="badge-{st}" cx="{x:.0f}" cy="{y:.0f}" r="8"/>'
              f'<text class="t-badge" x="{x:.0f}" y="{y+4:.0f}">{GLYPH[st]}</text>{count}<title>{tip}</title></g>')
        ly = L.height + 14
        if fl:
            a(f'<text class="t-band" x="12" y="{ly}">findings</text>')
        for i, f in enumerate(fl):
            a(f'<g class="chk"><text class="t-w st-{f.status}" x="12" y="{ly+18+i*18}">{GLYPH[f.status]} '
              f'{_t(f.check)} · {_t(f.subject)}: {_t(f.message)}</text></g>')
    if mode or overlay:
        tag = " · ".join(x for x in (f"mode: {mode}" if mode else "", overlay or "") if x)
        a(f'<text class="t-w t-end" x="{L.width-24:.0f}" y="12">{_t(tag)}</text>')
    a('</svg>')
    return "\n".join(o)


def _free_y(L: Layout, items, touches, x0: float, x1: float, below: float, h: float) -> float:
    """The lowest y with y + h <= below where a label [x0, x1] × [y, y + h] clears every live row line
    and every box, searching upwards. Labels sit in the gaps between rows, never on top of one."""
    lines = []
    for b in L.bands:
        for r in b.rows:
            lx0, lx1 = _live_span(None, L, items, touches, r)
            if lx0 - DOT_R < x1 and lx1 + DOT_R > x0:          # a row may end on a read dot
                lines.append(r.y)
    boxes = [(bx.y0, bx.y1) for bx in L.boxes.values() if bx.x < x1 and bx.x + BOX_W > x0]
    y = below - h
    while y > 0:
        if (all(not (y - 3 <= ly <= y + h + 3) for ly in lines)
                and all(y + h < b0 - 1 or y > b1 + 1 for b0, b1 in boxes)):
            return y
        y -= 1
    return below - h


def _end_x(L: Layout, end: str) -> float:
    name = end.split(".")[0]
    return _cx(L, name) if name in L.col else X0 + 10


def _subject_box(d: Design, L: Layout, f: Finding) -> Optional[tuple[float, float]]:
    import re
    names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", f.subject)
    for n in names:
        if n in L.boxes:
            b = L.boxes[n]
            return b.x + BOX_W - 2, b.y0 + 2
    for n in names:
        if n in L.pills:
            x0, x1, y = L.pills[n]
            return x1 - 2, y + 2
    for n in names:
        for r in L.rowmap.values():
            if r.fields and any(fl.path == f.subject or fl.name == n for fl in r.fields):
                return LABEL_W - 4, r.y - 8
    return None


def _moves_out(d: Design, item, carrier: str) -> bool:
    """True if the item takes whole items off `carrier` and puts them on another family."""
    if isinstance(item, Stage):
        return item.on == carrier and item.out is not None and _family(d, item.out) != _family(d, carrier)
    if isinstance(item, Route):
        return item.src == carrier
    if isinstance(item, Merge) and not _merge_on_dst(d, item):
        src = _merge_input_carrier(d, item)
        return src is not None and _family(d, carrier) == _family(d, src)
    return False


def _row_owners(d: Design, L: Layout, items, touches, r: Row) -> tuple[Optional[str], Optional[str]]:
    """The items a row starts from and ends at; None means the left or right edge of the drawing.
    A row starts at the item that creates it, or else at the first producer of its carrier. It ends
    at the item that consumes it, or at the last item touching its carrier if that item moves the
    carrier's items elsewhere; otherwise it leaves the design at the right edge."""
    paths = {f.path for f in r.fields}
    carrier = r.fields[0].carrier if r.fields else r.key.rstrip(":")
    makers = [n for n, t in touches.items() if paths & t["creates"]] or _producers(d, carrier)
    start = min(makers, key=lambda n: L.col[n]) if makers else None
    after = (lambda n: start is None or L.col[n] > L.col[start])
    ends = [n for n, t in touches.items() if paths & t["consumes"] and after(n)]
    last = None
    for n, it in items.items():
        if carrier in _carriers_touched(d, it) or _moves_out(d, it, carrier):
            last = n
    if last is not None and _moves_out(d, items[last], carrier) and after(last):
        ends.append(last)
    end = min(ends, key=lambda n: L.col[n]) if ends else None
    return start, end


def _live_span(d: Design, L: Layout, items, touches, r: Row) -> tuple[float, float]:
    x0, x1 = L.spans[r.key]
    return x0, (L.width - 22 if x1 is None else x1)


def _rigid_spans(d: Design, L: Layout, carrier: str, live_end: float):
    """Shade where a band's items cannot stall: between rigid boundaries on the carrier, from a rigid
    boundary up to the box that buffers into an elastic one, from the left edge when the carrier comes
    from outside, and after the last rigid boundary when no unannotated stage follows it."""
    marks, extra = set(), set()
    for n, it in _items(d):
        btw = getattr(it, "between", None)
        if not btw:
            continue
        src = getattr(it, "on", None) or getattr(it, "src", None)
        dst = getattr(it, "out", None) or getattr(it, "dst", None)
        if src == carrier:
            marks.update(btw)
        if dst == carrier:
            marks.add(btw[1])
            if btw[1] in L.bx and d.boundaries[btw[1]].coupling == "rigid":
                extra.add((_cx(L, n) + BOX_W / 2, "rigid"))      # the box's rigid output side
    xs = sorted({(L.bx[b], d.boundaries[b].coupling) for b in marks if b in L.bx} | extra)
    spans = []
    if not xs:
        return spans
    if xs[0][1] == "rigid" and not _producers(d, carrier):
        spans.append((X0 - 4, xs[0][0]))
    for (xa, ca), (xb, cb) in zip(xs, xs[1:]):
        if ca == "rigid":
            spans.append((xa, xb if cb == "rigid" else xb - (COL / 2 - 6) - BOX_W / 2))
    xl = xs[-1][0]
    loose = [n for n, it in _items(d) if carrier in _carriers_touched(d, it)
             and not getattr(it, "between", None) and _cx(L, n) > xl]
    if xs[-1][1] == "rigid" and not loose and live_end > xl:
        spans.append((xl, min(live_end + 8, L.width - 16)))
    return [(a, b) for a, b in spans if b > a]


# ── page ──────────────────────────────────────────────────────────────────

CSS = """
:root { --bg:#F3F5F7; --surface:#FFFFFF; --fg:#18212B; --muted:#5E6B78; --rule:#CBD3DB; --track:#B3BDC8;
  --soft:#E4E9EE; --band:#F0F3F6; --rigid:#DCE2E9; --accent:#2F5BD3; --accent-soft:#E2E9FB;
  --d1:#B5560B; --d2:#7B3FB5; --d3:#0F7A7A; --d4:#8A6D00;
  --ok:#2D7A4B; --ok-soft:#DDF0E4; --bad:#C0312B; --bad-soft:#F8DEDC; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#0E1318; --surface:#151C23; --fg:#E4E9EF;
  --muted:#93A1AF; --rule:#2B3540; --track:#3E4A57; --soft:#24303B; --band:#19212A; --rigid:#26313D; --accent:#7C9DFF; --accent-soft:#1D2A4A;
  --d1:#F0A25A; --d2:#C49AF5; --d3:#5CC8C8; --d4:#E0C060; --ok:#62C98C; --ok-soft:#173326; --bad:#FF7A72; --bad-soft:#3D1D1B; color-scheme:dark; } }
:root[data-theme="dark"] { --bg:#0E1318; --surface:#151C23; --fg:#E4E9EF; --muted:#93A1AF; --rule:#2B3540; --track:#3E4A57;
  --soft:#24303B; --band:#19212A; --rigid:#26313D; --accent:#7C9DFF; --accent-soft:#1D2A4A; --d1:#F0A25A; --d2:#C49AF5; --d3:#5CC8C8; --d4:#E0C060;
  --ok:#62C98C; --ok-soft:#173326; --bad:#FF7A72; --bad-soft:#3D1D1B; color-scheme:dark; }
svg.gateau { display:block; max-width:none; height:auto; font-family:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace; }
svg.gateau text { fill:var(--fg); }
.gateau .band { fill:var(--band); } .gateau .rigid { fill:var(--rigid); } .gateau .deck { fill:var(--surface); stroke:var(--track); }
.gateau .track { stroke:var(--track); stroke-width:1; stroke-dasharray:2 4; }
.gateau .lane { stroke:var(--fg); stroke-width:2; fill:none; }
.gateau .lane.d1 { stroke:var(--d1); } .gateau .lane.d2 { stroke:var(--d2); } .gateau .lane.d3 { stroke:var(--d3); } .gateau .lane.d4 { stroke:var(--d4); }
.gateau .tail { fill:var(--fg); } .gateau .tail.d1 { fill:var(--d1); } .gateau .tail.d2 { fill:var(--d2); }
.gateau .conn { stroke:var(--fg); stroke-width:1.2; fill:none; } .gateau .dot { fill:var(--fg); }
.gateau .box { fill:var(--surface); stroke:var(--fg); stroke-width:1.2; }
.gateau .box-opt { fill:var(--surface); stroke:var(--fg); stroke-width:1.2; stroke-dasharray:4 3; }
.gateau .pill, .gateau .stub { fill:var(--soft); stroke:var(--fg); stroke-width:1; }
.gateau .edge { stroke:var(--muted); stroke-width:1; stroke-dasharray:3 3; }
.gateau .gutter { fill:var(--bg); stroke:var(--rule); }
.gateau .fb-data { stroke:var(--fg); stroke-width:1.4; fill:none; }
.gateau .fb-ctrl { stroke:var(--muted); stroke-width:1.4; stroke-dasharray:5 3; fill:none; }
.gateau .fb-flow { stroke:var(--muted); stroke-width:1.5; stroke-dasharray:1.5 3.5; fill:none; }
.gateau .ah-ink { fill:var(--fg); } .gateau .ah-mut { fill:var(--muted); } .gateau .ah-d1 { fill:var(--d1); } .gateau .ah-d2 { fill:var(--d2); }
.gateau .ah-d3 { fill:var(--d3); } .gateau .ah-d4 { fill:var(--d4); }
.gateau .t-name { font-size:12px; } .gateau .t-w { font-size:10px; } .gateau text.t-w { fill:var(--muted); }
.gateau .t-band { font-size:10px; font-weight:600; letter-spacing:.05em; } .gateau text.t-band { fill:var(--muted); }
.gateau .t-box { font-size:11.5px; font-weight:600; text-anchor:middle; } .gateau .t-sub { font-size:9.5px; text-anchor:middle; }
.gateau text.t-sub { fill:var(--muted); } .gateau .t-stub { font-size:9px; text-anchor:middle; }
.gateau .t-note { font-size:10px; } .gateau text.t-note { fill:var(--muted); }
.gateau .halo { paint-order:stroke; stroke:var(--bg); stroke-width:4px; stroke-linejoin:round; }
.gateau .t-mid { text-anchor:middle; } .gateau .t-end { text-anchor:end; }
.gateau .t-badge { font-size:10px; font-weight:700; text-anchor:middle; }
.gateau .t-count { font-size:8.5px; font-weight:700; } .gateau text.t-count { fill:var(--muted); }
.gateau .badge-pass { fill:var(--ok-soft); stroke:var(--ok); } .gateau .badge-fail { fill:var(--bad-soft); stroke:var(--bad); }
.gateau .badge-unchecked { fill:var(--accent-soft); stroke:var(--accent); } .gateau .badge-info { fill:var(--soft); stroke:var(--muted); }
.gateau text.st-pass { fill:var(--ok); } .gateau text.st-fail { fill:var(--bad); } .gateau text.st-unchecked { fill:var(--accent); }
.gateau .off { opacity:.18; }
"""


def render_html(d: Design, findings: Optional[list[Finding]] = None, mode=None, overlay=None, title=None) -> str:
    svg = render_svg(d, findings, mode, overlay)
    title = title or f"{d.name} bus view"
    return (f"<!doctype html><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
            f"<title>{_t(title)}</title><style>{CSS} body{{background:var(--bg);color:var(--fg);margin:0;padding:16px;"
            f"font-family:system-ui,sans-serif}} .sheet{{background:var(--surface);border:1px solid var(--rule);"
            f"border-radius:4px;padding:12px;overflow-x:auto}}</style>"
            f"<div class=\"sheet\">{svg}</div>")
