"""The bus-view renderer: structural properties of the SVG, not pixels."""
import xml.etree.ElementTree as ET

import pytest

from gateau import run_all
from gateau.render import BOX_W, X0, carrier_order, layout, render_html, render_svg

from test_examples import EXAMPLES, load

NS = {"s": "http://www.w3.org/2000/svg"}
NAMES = ["dprx", "mstrx", "rocket", "ethernet"]


def model(name):
    mod = load(name)
    d = mod.build()
    return d, run_all(d, mod.OUTSIDE)


def svg(name, **kw):
    d, fs = model(name)
    return d, ET.fromstring(render_svg(d, fs, **kw))


def row_line(root, key):
    return root.find(f".//s:line[@data-row='{key}']", NS)


def item_x(root, name):
    g = root.find(f".//s:g[@data-item='{name}']", NS)
    shape = g[0]
    if shape.tag.endswith("rect"):
        return float(shape.get("x"))
    return min(float(p.split(",")[0]) for p in shape.get("points").split())


@pytest.mark.parametrize("name", NAMES)
def test_every_item_and_carrier_is_drawn(name):
    d, root = svg(name)
    items = {g.get("data-item") for g in root.iterfind(".//s:g[@data-item]", NS)}
    assert items == set(d.order)
    bands = {r.get("data-carrier") for r in root.iterfind(".//s:rect[@class='band']", NS)}
    assert bands == set(d.carriers)
    decks = len(root.findall(".//s:rect[@class='deck']", NS))
    assert decks == 2 * sum(1 for c in d.carriers.values() if c.index)
    width = float(root.get("width"))
    for g in root.iterfind(".//s:g[@data-item]", NS):
        assert item_x(root, g.get("data-item")) + BOX_W <= width


def test_kinds_route_and_merge_are_trapezoids():
    _, root = svg("mstrx")
    for name, kind in (("ROUTE", "route"), ("SDPM", "merge"), ("MSGM", "merge"), ("PACK", "stage")):
        g = root.find(f".//s:g[@data-item='{name}']", NS)
        assert g.get("data-kind") == kind
        assert g[0].tag.endswith("polygon" if kind != "stage" else "rect")


def test_carrier_order_keeps_chains_adjacent():
    d, _ = model("mstrx")
    order = carrier_order(d, layout(d).col)
    assert order[0] == "msg"                                     # rings first
    assert order.index("sdpb") == order.index("sdpk") + 1        # child under parent
    assert order.index("sdpo") < order.index("pix")              # sdpk → sdpo chain before the pixel branch
    d, _ = model("ethernet")
    order = carrier_order(d, layout(d).col)
    assert order == ["blk_rx", "pkt_rx", "beat_rx", "pkt_tx", "beat_tx", "blk_tx"]


def test_rows_end_where_items_leave_and_not_before():
    _, root = svg("dprx")
    assert float(row_line(root, "sym.k").get("x2")) == item_x(root, "VID")      # VID turns symbols into pixels
    _, root = svg("rocket")
    assert float(row_line(root, "inst.valid").get("x2")) > item_x(root, "WB")   # DC0 forks, inst carries on
    assert float(row_line(root, "inst.wdata").get("x2")) == item_x(root, "WB")  # WB consumes wdata
    _, root = svg("mstrx")
    assert float(row_line(root, "sdpob.dat").get("x1")) > item_x(root, "SDPM")  # beats exist once SDPM makes packets
    assert float(row_line(root, "sym.k").get("x2")) == item_x(root, "ROUTE")


def test_rigid_shading_follows_boundaries():
    def shaded(name):
        _, root = svg(name)
        return {r.get("data-carrier") for r in root.iterfind(".//s:rect[@class='rigid']", NS)}
    assert shaded("dprx") == {"sym"}
    assert shaded("rocket") == set()
    # MAC_CRC sits between r1 and r3, so its fcs_ok verdict is rigid from the box to r3
    assert shaded("ethernet") == {"blk_rx", "pkt_rx", "beat_rx", "beat_tx", "blk_tx"}


def test_mode_fades_inactive_items():
    _, root = svg("dprx", mode="training")
    assert root.find(".//s:g[@data-item='MSA']", NS).get("class") == "off"
    assert root.find(".//s:g[@data-item='TRN']", NS).get("class") is None
    _, root = svg("dprx")
    assert root.find(".//s:g[@data-item='MSA']", NS).get("class") is None


def test_checks_show_only_in_the_checks_view():
    """Badges and the findings list belong to the checks view; every other view is the plain drawing."""
    d, fs = model("dprx")
    for kw in ({}, {"mode": "training"}, {"overlay": "cost"}):
        root = ET.fromstring(render_svg(d, fs, **kw))
        assert root.find(".//s:g[@class='chk']", NS) is None, kw
        assert "findings" not in " ".join(t.text or "" for t in root.iterfind(".//s:text", NS)), kw
    _, root = svg("dprx", overlay="checks")
    fails = root.findall(".//s:circle[@class='badge-fail']", NS)
    assert len(fails) == 1
    text = " ".join(t.text or "" for t in root.iterfind(".//s:text", NS))
    assert "cfg.scrm_en" in text and "findings" in text
    listed = [t for t in root.iterfind(".//s:text", NS) if (t.get("class") or "").startswith("t-w st-")]
    assert len(listed) == len(fs)                # the checks view lists every finding, passes included


def test_checks_view_is_not_faded():
    """The checks view keeps the drawing at full contrast: badges carry their own colour."""
    d, fs = model("mstrx")
    page = render_html(d, fs, overlay="checks")
    assert "ov-checks >" not in page and "ov-checks>" not in page
    root = ET.fromstring(render_svg(d, fs, overlay="checks"))
    assert not [g for g in root.iter(f"{{{NS['s']}}}g") if g.get("class") == "off"]


def test_cost_overlay_scales_rows_by_bits():
    _, root = svg("dprx", overlay="cost")
    k = float(row_line(root, "sym.k").get("style").split(":")[1])
    dat = float(row_line(root, "sym.dat").get("style").split(":")[1])
    assert dat > k


def test_html_page_and_cli(tmp_path, capsys):
    d, fs = model("mstrx")
    page = render_html(d, fs)
    assert page.startswith("<!doctype html>") and "prefers-color-scheme: dark" in page
    from gateau.__main__ import main
    out = tmp_path / "m.html"
    assert main(["gateau", str(EXAMPLES / "mstrx.py"), "--html", str(out), "--mode", "normal"]) == 1
    assert "<svg" in out.read_text()
    with pytest.raises(SystemExit):
        main(["gateau", str(EXAMPLES / "mstrx.py"), "--mode", "nope"])


def _anchors(root):
    """Vertical edges a row may end on: (x, y_lo, y_hi) for each box side, plus dots as points."""
    edges = []
    for g in root.iterfind(".//s:g[@data-item]", NS):
        shape = g[0]
        if shape.tag.endswith("rect"):
            x, y, w, h = (float(shape.get(k)) for k in ("x", "y", "width", "height"))
            edges += [(x, y, y + h), (x + w, y, y + h)]
        else:
            pts = [tuple(map(float, p.split(","))) for p in shape.get("points").split()]
            for xa in {p[0] for p in pts}:
                ys = [p[1] for p in pts if p[0] == xa]
                edges.append((xa, min(ys), max(ys)))
    dots = [(float(c.get("cx")), float(c.get("cy"))) for c in root.iterfind(".//s:circle[@class='dot']", NS)]
    return edges, dots


@pytest.mark.parametrize("name", NAMES)
def test_no_row_starts_or_ends_in_mid_air(name):
    """Every live row starts on a box side or the left margin, and ends on a box side, its read dot,
    or the right margin."""
    _, root = svg(name)
    width = float(root.get("width"))
    edges, dots = _anchors(root)

    def anchored(x, y):
        return (any(abs(x - ex) < 0.6 and lo - 0.5 <= y <= hi + 0.5 for ex, lo, hi in edges)
                or any(abs(x - dx) < 0.6 and abs(y - dy) < 0.6 for dx, dy in dots))
    loose = []
    for ln in root.iterfind(".//s:line[@data-row]", NS):
        y = float(ln.get("y1"))
        x1, x2 = float(ln.get("x1")), float(ln.get("x2"))
        if not (x1 <= X0 or anchored(x1, y)):
            loose.append(f"{ln.get('data-row')} starts at {x1:.0f}")
        if not (x2 >= width - 22 or anchored(x2, y)):
            loose.append(f"{ln.get('data-row')} ends at {x2:.0f}")
    assert not loose


@pytest.mark.parametrize("name", NAMES)
def test_stubs_sit_in_free_space(name):
    """A state stub never touches a live row line (3 px clearance) or another box: it sits in a gap."""
    _, root = svg(name)
    lines = [(float(ln.get("x1")), float(ln.get("x2")), float(ln.get("y1")))
             for ln in root.iterfind(".//s:line[@data-row]", NS)]
    boxes = []
    for g in root.iterfind(".//s:g[@data-item]", NS):
        sh = g[0]
        if sh.tag.endswith("rect"):
            x, y, w, h = (float(sh.get(k)) for k in ("x", "y", "width", "height"))
        else:
            pts = [tuple(map(float, p.split(","))) for p in sh.get("points").split()]
            x, y = min(p[0] for p in pts), min(p[1] for p in pts)
            w, h = max(p[0] for p in pts) - x, max(p[1] for p in pts) - y
        boxes.append((g.get("data-item"), x, y, w, h))
    stubs = root.findall(".//s:rect[@data-stub]", NS)
    clashes = []
    for st in stubs:
        x, y, w, h = (float(st.get(k)) for k in ("x", "y", "width", "height"))
        for lx0, lx1, ly in lines:
            if lx0 - 3.2 < x + w and lx1 + 3.2 > x and y - 3 <= ly <= y + h + 3:   # dot radius, 3 px clearance
                clashes.append(f"{st.get('data-stub')} stub on the row at y={ly:.0f}")
        for n, bx, by, bw, bh in boxes:
            if bx < x + w and bx + bw > x and by < y + h and by + bh > y:
                clashes.append(f"{st.get('data-stub')} stub on box {n}")
    assert not clashes
    if name == "mstrx":
        assert any(st.get("data-stub") == "STRM" for st in stubs)


@pytest.mark.parametrize("name", NAMES)
def test_no_connector_runs_through_a_badge(name):
    """Check badges sit on box corners; no tap, read or emit connector may touch one."""
    d, fs = model(name)
    root = ET.fromstring(render_svg(d, fs, overlay="checks"))
    badges = [(float(c.get("cx")), float(c.get("cy")), float(c.get("r")))
              for c in root.iter(f"{{{NS['s']}}}circle") if (c.get("class") or "").startswith("badge-")]
    hits = []
    for ln in root.iterfind(".//s:line[@class='conn']", NS):
        x, ya, yb = float(ln.get("x1")), float(ln.get("y1")), float(ln.get("y2"))
        if x != float(ln.get("x2")):
            continue
        for bx, by, r in badges:
            if abs(x - bx) < r + 1 and min(ya, yb) < by + r and max(ya, yb) > by - r:
                hits.append(f"connector at x={x:.0f} over badge at ({bx:.0f}, {by:.0f})")
    assert not hits


@pytest.mark.parametrize("name", NAMES)
def test_one_badge_per_subject_covers_every_finding(name):
    """Badges never stack: a subject with several findings gets one badge showing the worst status and
    a count, and every finding still reaches a badge (or the list) and its tooltip."""
    d, fs = model(name)
    root = ET.fromstring(render_svg(d, fs, overlay="checks"))
    groups = [g for g in root.iterfind(".//s:g[@data-findings]", NS)]
    spots = [(float(g[0].get("cx")), float(g[0].get("cy"))) for g in groups]
    assert len(spots) == len(set(spots))
    for i, (xa, ya) in enumerate(spots):
        for xb, yb in spots[i + 1:]:
            assert (xa - xb) ** 2 + (ya - yb) ** 2 >= 16 ** 2
    tips = " ".join(g.find("s:title", NS).text for g in groups)
    for f in fs:
        if f.subject.split()[0] in d.order or f.subject.split(".")[0] in d.states:
            assert f.message in tips
    if name == "dprx":
        doubles = sorted(g[0].get("class") for g in groups if g.get("data-findings") == "2")
        assert doubles == ["badge-pass", "badge-unchecked"]               # PARS: 2 pass; SDP: 2 unchecked


def test_badge_status_prefers_verdicts_over_info():
    """ROUTE has two passes and a cost note: its badge is a pass, not the info dot."""
    d, fs = model("mstrx")
    root = ET.fromstring(render_svg(d, fs, overlay="checks"))
    route = [g for g in root.iterfind(".//s:g[@data-findings='3']", NS)]
    assert [g[0].get("class") for g in route] == ["badge-pass"]
