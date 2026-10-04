"""Places the marks for the MSTRX figures in study 05 (gateau notation v1.2). Hand layout."""


def _deck(x, y, w, h, cls="carrier"):
    """an indexed carrier: the band, with two offset outlines behind it"""
    return (f'<rect class="deck" x="{x+8}" y="{y+8}" width="{w}" height="{h}"/>'
            f'<rect class="deck" x="{x+4}" y="{y+4}" width="{w}" height="{h}"/>'
            f'<rect class="{cls}-solid" x="{x}" y="{y}" width="{w}" height="{h}"/>')


BITS = {"lnk": 73, "slot": 12, "ssym": 288, "v": 8, "str": 288, "len": 24, "sdat": 128, "pix": 192, "olen": 6, "odat": 32, "sid": 2}


def bus(mode="normal", overlay=None):
    """mode: normal | training (MST machinery idle, faded).  overlay: None | checks | cost"""
    checks = overlay == "checks"
    cost = overlay == "cost"
    tr = mode == "training"
    o = []

    def a(s, chk=False, mst=False):
        if mst and tr:
            s = f'<g class="off">{s}</g>'
        o.append(f'<g class="chk">{s}</g>' if chk else s)

    def w(key):
        return f' style="stroke-width:{max(1.2, BITS[key] * 0.06):.2f}"' if cost else ''

    a(f'<svg class="{"ov-checks" if checks else ""}" viewBox="0 0 1200 700" role="img" aria-label="Bus view of the invented multi-stream receiver, {mode} mode{(", " + overlay + " overlay") if overlay else ""}.">')
    a('<defs>'
      '<marker id="m-ink" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-ink"/></marker>'
      '<marker id="m-vid" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-vid"/></marker>'
      '<marker id="m-sdp" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-sdp"/></marker>'
      '<marker id="m-mut" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-muted"/></marker>'
      '</defs>')

    tag = f"mode: {mode}" + (f" · {overlay}" if overlay else "")
    a(f'<rect class="modetag" x="1010" y="640" width="178" height="22" rx="11"/>'
      f'<text class="t-w t-mid" x="1099" y="655" style="fill:var(--fg)">{tag}</text>', chk=True)

    # state
    a('<rect class="store" x="300" y="22" width="440" height="18" rx="9"/>'
      '<text class="t-w" x="320" y="35" style="fill:var(--fg)">vcpt · slot → sid · epoch: active ← shadow at the MTP after ACT</text>', chk=True)
    a('<rect class="store" x="170" y="48" width="96" height="18" rx="9"/>'
      '<text class="t-w t-mid" x="218" y="61" style="fill:var(--fg)">mtp ↻ 64</text>', mst=True)

    # bands
    a('<rect class="carrier" x="116" y="76" width="1072" height="36"/>')
    a('<rect class="band-rigid" x="116" y="124" width="1072" height="64"/>')
    a(_deck(116, 210, 1060, 86, "rigid"))
    a(_deck(116, 318, 1060, 56))
    a(_deck(116, 402, 690, 70))
    a('<rect class="carrier" x="890" y="396" width="298" height="82"/>')
    a(_deck(116, 504, 1060, 60))
    a('<text class="t-w t-end" x="1180" y="137" style="fill:var(--fg)">rigid</text>')

    def lab(name, wd, y, cls="t-name"):
        a(f'<text class="{cls}" x="14" y="{y+4}">{name}</text><text class="t-w t-end" x="110" y="{y+4}">{wd}</text>')
    a('<text class="t-band" x="14" y="84">msg · lnk_clk</text>'); lab("msg", "16b", 96)
    a('<text class="t-band" x="14" y="133">sym · lnk_clk</text>'); lab("lnk ▸", "group", 150); lab("slot", "u6[s]", 172)
    a('<text class="t-band" x="14" y="221">ssym[sid] ×4</text>'); lab("lnk ▸", "[ℓ,s]", 242); lab("v", "bit[s]", 266)
    a('<text class="t-band" x="14" y="329">str[sid] ×4</text>'); lab("sym ▸", "dense", 350)
    a('<text class="t-band t-sdp" x="14" y="412">sdpk[sid] ×4</text>'); lab("len ◆", "u6", 432); lab("dat", "32", 454)
    a('<text class="t-band t-vid" x="14" y="514">pix[sid] ×4</text>'); lab("data", "PPC·3·BPC", 540)
    a('<text class="t-band t-sdp" x="896" y="408">sdpo · all streams</text>')

    for y in (150, 172, 242, 266, 350, 432, 454, 540):
        a(f'<line class="track" x1="116" y1="{y}" x2="1176" y2="{y}"/>')

    # boundaries
    a(''.join(f'<line class="edge" x1="{x}" y1="118" x2="{x}" y2="300"/><text class="t-w t-mid" x="{x}" y="120">{n}</text>'
              for x, n in ((225, "b0"), (345, "b1"), (470, "b2"))), chk=True)
    a('<line class="edge" x1="595" y1="310" x2="595" y2="378"/><text class="t-w t-mid" x="595" y="390" style="fill:var(--accent)">» b3</text>')

    # live rows
    a('<line class="msg" x1="116" y1="94" x2="1176" y2="94"/><line class="msg" x1="116" y1="98" x2="1176" y2="98"/>')
    a(f'<line class="lane" x1="116" y1="150" x2="130" y2="150"{w("lnk")}/>')
    a(f'<line class="lane" x1="210" y1="150" x2="385" y2="150"{w("lnk")}/>', mst=True)
    a(f'<line class="lane" x1="330" y1="172" x2="385" y2="172"{w("slot")}/>', mst=True)
    a(f'<line class="lane" x1="445" y1="242" x2="520" y2="242"{w("ssym")}/><line class="lane" x1="445" y1="266" x2="520" y2="266"{w("v")}/>', mst=True)
    a(f'<line class="lane" x1="580" y1="350" x2="620" y2="350"{w("str")}/>', mst=True)
    a(f'<line class="lane-sdp" x1="740" y1="432" x2="822" y2="432"{w("len")}/><line class="lane-sdp" x1="740" y1="454" x2="822" y2="454"{w("sdat")}/>'
      '<polygon class="tailmark" points="752,426 758,432 752,438 746,432"/>', mst=True)
    a(f'<line class="lane-sdp" x1="890" y1="420" x2="1182" y2="420"{w("sid")}/>'
      '<text class="t-w" x="1150" y="415" style="fill:var(--fg)">sid</text>'
      f'<line class="lane-sdp" x1="890" y1="442" x2="1182" y2="442"{w("olen")}/>'
      '<polygon class="tailmark" points="902,436 908,442 902,448 896,442"/>'
      f'<line class="lane-sdp" x1="890" y1="464" x2="1182" y2="464" marker-end="url(#m-sdp)"{w("odat")}/>', mst=True)
    a(f'<line class="lane-vid" x1="740" y1="540" x2="1176" y2="540" marker-end="url(#m-vid)"{w("pix")}/>'
      '<text class="t-w t-vid t-end" x="1170" y="526">4 outputs, one per vid_clk[sid]</text>', mst=True)
    if cost:
        a('<text class="t-w" x="452" y="205" style="fill:var(--fg)">ssym: 288 b per cycle, ≤ 72 b valid</text>')
    if tr:
        a('<text class="t-w" x="600" y="204" style="fill:var(--fg)">training runs inside LINK (study 04, FIG D2); no MTPs yet</text>')

    # taps
    a('<line class="conn" x1="310" y1="94" x2="310" y2="42" marker-end="url(#m-ink)"/><circle class="dot" cx="310" cy="94" r="3.2"/>'
      '')
    a('<line class="conn" x1="285" y1="150" x2="285" y2="158"/><circle class="dot" cx="285" cy="150" r="3.2"/>', mst=True)
    a('<line class="conn" x1="252" y1="158" x2="252" y2="68" marker-end="url(#m-ink)"/>', mst=True)
    a('<line class="conn" x1="322" y1="158" x2="322" y2="42" marker-end="url(#m-ink)"/><text class="t-w" x="327" y="110" style="fill:var(--fg)">swap</text>', chk=True, mst=True)
    a('<line class="conn" x1="402" y1="40" x2="402" y2="140"/><circle class="dot" cx="402" cy="40" r="3.2"/>', chk=True, mst=True)
    a('<line class="conn" x1="700" y1="228" x2="700" y2="100" marker-end="url(#m-ink)"/>', chk=True, mst=True)

    # boxes
    a('<rect class="box-opt" x="120" y="82" width="40" height="24" rx="3"/><text class="t-sub" x="140" y="98" style="fill:var(--muted)">PM</text>')
    a('<rect class="box" x="130" y="138" width="80" height="24" rx="3"/><text class="t-box" x="170" y="154">LINK ≡ 04</text>')
    a('<rect class="box" x="240" y="158" width="90" height="26" rx="3"/><text class="t-box" x="285" y="175">FRAME</text>', mst=True)
    a('<polygon class="box route" points="385,144 445,128 445,298 385,282"/>'
      '<text class="t-box" x="415" y="212">ROUTE</text><text class="t-sub" x="415" y="228">per s</text>', chk=True, mst=True)
    a('<rect class="box" x="520" y="228" width="60" height="146" rx="3"/><text class="t-box" x="550" y="290">PACK</text>'
      '<text class="t-sub" x="550" y="306">×sid</text><text class="t-sub" x="550" y="320">FIFO 64</text>', chk=True, mst=True)
    a('<rect class="box" x="620" y="228" width="120" height="342" rx="3"/>'
      '<text class="t-box" x="680" y="300">STRM ×sid</text><text class="t-sub" x="680" y="316">PARS · MSA</text>'
      '<text class="t-sub" x="680" y="330">SDP · VID</text><text class="t-sub" x="680" y="344">= study 04</text>', chk=True, mst=True)
    a('<polygon class="box merge" points="822,398 890,410 890,474 822,486"/>'
      '<text class="t-box" x="856" y="446">SDPM</text>', chk=True, mst=True)
    a('<text class="t-sub" x="856" y="462" style="fill:var(--fg)">RR · packet</text>', mst=True)
    a('<polygon class="box merge" points="700,84 730,90 730,102 700,108"/>', chk=True, mst=True)
    a('<text class="t-w" x="736" y="110" style="fill:var(--fg)">MSGM · ring order</text>', mst=True)

    # gutter
    a('<rect class="gutter" x="116" y="604" width="880" height="86" rx="3"/><text class="t-note" x="14" y="624">gutter</text>')
    a('<path class="flow" d="M856,486 L856,636 L700,636 L700,572" marker-end="url(#m-mut)"/>'
      '<text class="t-w" x="712" y="630">flow · SDPM grant → one stream at a time</text>', mst=True)
    a('<path class="back-ctl" d="M650,570 L650,668 L140,668 L140,108" marker-end="url(#m-mut)"/>'
      '<text class="t-w" x="300" y="663">ctrl · per-stream vblank irq → PM</text>', mst=True)

    # check badges
    a('<rect class="badge-ok" x="760" y="22" width="270" height="18" rx="9"/>'
      '<text class="t-w t-ok t-mid" x="895" y="35">✓ epoch: one reader, one swap point</text>', chk=True, mst=True)
    a('<rect class="badge-bad" x="760" y="48" width="300" height="18" rx="9"/>'
      '<text class="t-w t-bad t-mid" x="910" y="61">✗ MSGM: same message ID from 4 streams, no sid</text>', chk=True, mst=True)
    a('<rect class="badge-ok" x="250" y="300" width="200" height="16" rx="8"/>'
      '<text class="t-w t-ok t-mid" x="350" y="312">✓ route covers all 64 slots</text>', chk=True, mst=True)
    a('<rect class="badge-acc" x="430" y="378" width="150" height="16" rx="8"/>'
      '<text class="t-w t-acc t-mid" x="505" y="390">rigid edge: FIFO ≥ run</text>', chk=True, mst=True)
    a('<rect class="badge-ok" x="900" y="484" width="280" height="16" rx="8"/>'
      '<text class="t-w t-ok t-mid" x="1040" y="496">✓ SDPM: creates sid · never splits a packet</text>', chk=True, mst=True)
    a('</svg>')
    return '\n'.join(o)


ALLOC = ['H'] + ['A'] * 24 + ['B'] * 16 + ['C'] * 12 + ['D'] * 8 + ['·'] * 3


def slot_map():
    o = ['<svg viewBox="0 0 1200 300" role="img" aria-label="Slot map of one 64-slot MTP: slot 0 is the header, streams A to D own contiguous slot runs of 24, 16, 12 and 8, and 3 slots are unallocated. At two slots per cycle, the cycle carrying slots 24 and 25 feeds stream A from symbol position 0 and stream B from position 1.">']
    o.append('<text class="t-name" x="60" y="26" style="font-weight:600">one MTP: 64 slots, 8 per row</text>')
    C, G, x0, y0 = 26, 2, 80, 40
    for i, k in enumerate(ALLOC):
        r, c = divmod(i, 8)
        x, y = x0 + c * (C + G), y0 + r * (C + G)
        cls = "c-hdr" if k == 'H' else ("c-trl" if k == '·' else "c-str")
        hi = ' style="stroke:var(--accent);stroke-width:2.2"' if i in (24, 25) else ''
        o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{C}" height="{C}" rx="2"{hi}/>'
                 f'<text class="t-cell" x="{x+C/2}" y="{y+17}">{k}</text>')
    for r in range(8):
        o.append(f'<text class="t-w t-end" x="{x0-6}" y="{y0+r*(C+G)+17}">{r*8}</text>')
    o.append('<text class="t-w" x="80" y="284">H = MTP header · A–D = streams · · = unallocated</text>')
    # the split cycle
    o.append('<text class="t-name" x="420" y="26" style="font-weight:600">one cycle, two streams</text>')
    o.append('<text class="t-note" x="420" y="46">P_SPL = 2: each lnk_clk item carries two slots (s = 0, 1)</text>')
    o.append('<rect class="c-str" x="420" y="110" width="60" height="40" rx="2" style="stroke:var(--accent);stroke-width:2.2"/><text class="t-cell" x="450" y="134">A · 24</text>')
    o.append('<rect class="c-str" x="480" y="110" width="60" height="40" rx="2" style="stroke:var(--accent);stroke-width:2.2"/><text class="t-cell" x="510" y="134">B · 25</text>')
    o.append('<text class="t-w t-mid" x="450" y="166" style="fill:var(--fg)">s = 0</text><text class="t-w t-mid" x="510" y="166" style="fill:var(--fg)">s = 1</text>')
    o.append('<polygon class="box route" points="580,112 640,96 640,164 580,148"/><text class="t-sub" x="610" y="134" style="fill:var(--fg)">ROUTE</text>')
    o.append('<line class="wire" x1="540" y1="130" x2="580" y2="130"/>')
    for i, (st, v, y) in enumerate((("A", "1 0", 96), ("B", "0 1", 164))):
        o.append(f'<line class="wire" x1="640" y1="{y}" x2="700" y2="{y}"/>'
                 f'<rect class="c-str" x="700" y="{y-14}" width="44" height="28" rx="2"/><text class="t-cell" x="722" y="{y+4}">{st}</text>'
                 f'<text class="t-w" x="754" y="{y+4}" style="fill:var(--fg)">ssym[{st}].v = {v}</text>')
    o.append('<text class="t-note" x="420" y="216">A single item feeds two streams, so ROUTE splits along the s axis</text>')
    o.append('<text class="t-note" x="420" y="232">and each stream receives items that are only partly valid. That is</text>')
    o.append('<text class="t-note" x="420" y="248">why PACK exists, and why the route\'s granularity is an attribute:</text>')
    o.append('<text class="t-note" x="420" y="264">routing whole items would be wrong here.</text>')
    o.append('<text class="t-note" x="900" y="94">longest run: stream A,</text>')
    o.append('<text class="t-note" x="900" y="110">24 slots = 12 cycles in a row,</text>')
    o.append('<text class="t-note" x="900" y="126">then nothing for 20 cycles.</text>')
    o.append('<text class="t-note" x="900" y="142">PACK\'s FIFO absorbs the burst.</text>')
    o.append('</svg>')
    return '\n'.join(o)


def epoch_view():
    cols = ["MTP n−1", "MTP n", "MTP n+1", "MTP n+2"]
    x0, cw, top, rh = 260, 210, 50, 34
    o = ['<svg viewBox="0 0 1200 270" role="img" aria-label="Epoch time view: the policy maker writes the shadow table during MTP n minus 1, the ACT sequence arrives in MTP n, and the active table changes at the start of MTP n plus 1. A router that swaps at that boundary routes correctly; a router that swapped as soon as it detected ACT would route the rest of MTP n with the wrong table.">']
    for i, c in enumerate(cols):
        o.append(f'<text class="t-w t-mid" x="{x0+i*cw+cw/2}" y="{top-10}">{c}</text>')
        o.append(f'<line class="grid" x1="{x0+i*cw}" y1="{top-4}" x2="{x0+i*cw}" y2="{top+5*rh}"/>')
    o.append(f'<line class="grid" x1="{x0+4*cw}" y1="{top-4}" x2="{x0+4*cw}" y2="{top+5*rh}"/>')
    rows = ["PM writes shadow", "MTP header", "vcpt.active", "ROUTE · swap at boundary", "ROUTE · swap on detect"]
    for r, n in enumerate(rows):
        o.append(f'<text class="t-note" x="14" y="{top+r*rh+17}">{n}</text>')

    def cell(r, c, txt, cls, frac=(0, 1)):
        x = x0 + c * cw + 4 + frac[0] * (cw - 8)
        w = (frac[1] - frac[0]) * (cw - 8)
        y = top + r * rh
        tc = {"cell": "", "cell-acc": " t-acc", "cell-ok": " t-ok", "cell-bad": " t-bad"}[cls]
        fill = ' style="fill:var(--fg)"' if cls == "cell" else ''
        o.append(f'<rect class="{cls}" x="{x:.0f}" y="{y}" width="{w:.0f}" height="24" rx="2"/>'
                 f'<text class="t-w t-mid{tc}" x="{x+w/2:.0f}" y="{y+16}"{fill}>{txt}</text>')
    cell(0, 0, "B: 16 → 20 slots", "cell-acc")
    for c, t in enumerate(["MTPH", "ACT", "MTPH", "MTPH"]):
        cell(1, c, t, "cell-acc" if t == "ACT" else "cell")
    for c, t in enumerate(["old", "old", "new", "new"]):
        cell(2, c, t, "cell")
    for c, t in enumerate(["old", "old", "new", "new"]):
        cell(3, c, t, "cell-ok")
    cell(4, 0, "old", "cell-ok")
    cell(4, 1, "old", "cell-ok", (0, 0.2))
    cell(4, 1, "new: wrong table", "cell-bad", (0.2, 1))
    cell(4, 2, "new", "cell-ok"); cell(4, 3, "new", "cell-ok")
    o.append(f'<text class="t-note" x="14" y="{top+5*rh+30}">The epoch check asks two things of every state with an epoch: who reads it, and does each reader switch at the declared point.</text>')
    o.append(f'<text class="t-note" x="14" y="{top+5*rh+46}">Here ROUTE is the only reader, and the model says it switches at the boundary, so it holds. Add a second reader (say PACK) that switches on detect, and it fails.</text>')
    o.append('</svg>')
    return '\n'.join(o)


def pack_fifo():
    """time view: PACK FIFO occupancy for stream A over one MTP (32 cycles)"""
    X0, Y0, W, H = 120, 40, 900, 200       # plot area
    cyc, ymax = 32, 16
    sx = lambda c: X0 + c * W / cyc
    sy = lambda v: Y0 + H - v * H / ymax
    pts, peak = [], (0, 0)
    for k in range(0, cyc * 4 + 1):
        c = k / 4
        arrived = min(24, max(0, int(2 * c) + 1)) if c < 12.5 else 24     # slots 1..24 at two per cycle
        occ = max(0.0, arrived - 0.75 * c)
        pts.append(f"{sx(c):.1f},{sy(occ):.1f}")
        if occ > peak[1]:
            peak = (c, occ)
    o = ['<svg viewBox="0 0 1200 300" role="img" aria-label="Line chart of PACK FIFO occupancy for stream A across one MTP: it rises to about 14 slots while stream A\'s 24 slots arrive in the first 12 cycles, then drains to zero by cycle 32 at the stream\'s average rate of 0.75 slots per cycle.">']
    o.append(f'<rect class="band" x="{sx(0):.0f}" y="{Y0}" width="{sx(12)-sx(0):.0f}" height="{H}"/>')
    o.append(f'<text class="t-w" x="{sx(0)+6:.0f}" y="{Y0+14}" style="fill:var(--fg)">stream A\'s slots arrive (24 slots, 12 cycles)</text>')
    for v in (0, 4, 8, 12, 16):
        o.append(f'<line class="grid" x1="{X0}" y1="{sy(v):.0f}" x2="{X0+W}" y2="{sy(v):.0f}"/>'
                 f'<text class="t-w t-end" x="{X0-8}" y="{sy(v)+4:.0f}">{v}</text>')
    for c in (0, 8, 16, 24, 32):
        o.append(f'<text class="t-w t-mid" x="{sx(c):.0f}" y="{Y0+H+18}">{c}</text>')
    o.append(f'<text class="t-w t-mid" x="{X0+W/2:.0f}" y="{Y0+H+36}">lnk_clk cycles within one MTP</text>')
    o.append(f'<text class="t-w" x="{X0-8}" y="{Y0-14}" style="text-anchor:end">slots</text>')
    o.append(f'<polyline class="occ" points="{" ".join(pts)}"><title>PACK[A] occupancy</title></polyline>')
    px, py = sx(peak[0]), sy(peak[1])
    o.append(f'<circle class="occ-pt" cx="{px:.1f}" cy="{py:.1f}" r="4.5"><title>peak ≈ {peak[1]:.1f} slots at cycle {peak[0]:.0f}</title></circle>')
    o.append(f'<text class="t-w" x="{px+10:.0f}" y="{py-8:.0f}" style="fill:var(--fg)">peak ≈ {peak[1]:.0f} slots</text>')
    o.append(f'<text class="t-note" x="{X0+W+14}" y="{Y0+20}">capacity 64</text>')
    o.append(f'<text class="t-note" x="{X0+W+14}" y="{Y0+36}">(off scale)</text>')
    o.append(f'<text class="t-note" x="{X0+W+14}" y="{Y0+70}">drain: 24 slots</text>')
    o.append(f'<text class="t-note" x="{X0+W+14}" y="{Y0+86}">per 32 cycles</text>')
    o.append(f'<text class="t-note" x="{X0+W+14}" y="{Y0+102}">= 0.75 / cycle</text>')
    o.append('</svg>')
    return "\n".join(o)


def sdpm_view():
    """time view: round-robin, packet-atomic merge of four streams' SDP packets"""
    arrivals = [("A1", 0, 0, 3), ("B1", 1, 0, 2), ("C1", 2, 1, 4), ("D1", 3, 3, 2), ("A2", 0, 4, 3)]
    # round-robin over A,B,C,D, whole packets
    t, grants = 0, []
    pending = sorted(arrivals, key=lambda p: p[2])
    order = []
    rr = 0
    queue = list(arrivals)
    while queue:
        ready = [p for p in queue if p[2] <= t]
        if not ready:
            t += 1; continue
        ready.sort(key=lambda p: ((p[1] - rr) % 4, p[2]))
        p = ready[0]
        grants.append((p, t)); t += p[3]; rr = (p[1] + 1) % 4; queue.remove(p)
    x0, cw, top, rh, ncyc = 200, 58, 50, 34, 15
    o = ['<svg viewBox="0 0 1200 290" role="img" aria-label="Time view of the SDP merge: packets from four streams arrive, wait, and are granted one whole packet at a time in round-robin order, so the output never interleaves beats of different packets.">']
    for i in range(ncyc):
        o.append(f'<text class="t-w t-mid" x="{x0+i*cw+cw/2}" y="{top-10}">{i}</text>')
    o.append(f'<text class="t-w" x="{x0}" y="{top-26}" style="fill:var(--fg)">sdp_clk beats</text>')
    rows = ["stream A in", "stream B in", "stream C in", "stream D in", "SDPM out"]
    for r, n in enumerate(rows):
        o.append(f'<text class="t-note" x="14" y="{top+r*rh+17}">{n}</text>')
    o.append(f'<line class="grid" x1="{x0}" y1="{top+4*rh-6}" x2="{x0+ncyc*cw}" y2="{top+4*rh-6}"/>')
    for (name, sid, arr, ln), g in grants:
        y = top + sid * rh
        if g > arr:
            o.append(f'<rect class="cell-wait" x="{x0+arr*cw+3}" y="{y}" width="{(g-arr)*cw-6}" height="24" rx="2"/>'
                     f'<text class="t-w t-mid" x="{x0+arr*cw+(g-arr)*cw/2}" y="{y+16}">waits {g-arr}</text>')
        o.append(f'<rect class="cell-acc" x="{x0+g*cw+3}" y="{y}" width="{ln*cw-6}" height="24" rx="2"/>'
                 f'<text class="t-w t-mid t-acc" x="{x0+g*cw+ln*cw/2}" y="{y+16}">{name}</text>')
        yo = top + 4 * rh
        o.append(f'<rect class="cell-ok" x="{x0+g*cw+3}" y="{yo}" width="{ln*cw-6}" height="24" rx="2"/>'
                 f'<text class="t-w t-mid t-ok" x="{x0+g*cw+ln*cw/2}" y="{yo+16}">{name} · sid {sid}</text>')
    o.append(f'<text class="t-note" x="14" y="{top+5*rh+24}">Round-robin from A. Each grant lasts a whole packet, so beats of different packets never interleave (atomicity), and every output packet carries sid (identity).</text>')
    o.append(f'<text class="t-note" x="14" y="{top+5*rh+40}">The longest wait here is A2\'s: it arrived just after A had its turn. In the worst case an input waits for three maximum-size packets, which sets the depth each stream\'s SDP FIFO needs.</text>')
    o.append('</svg>')
    return "\n".join(o)


def axis_view():
    """axis view: ROUTE adds the sid axis; replication runs over it; SDPM serialises it back into time"""
    o = ['<svg viewBox="0 0 1200 340" role="img" aria-label="Axis view of MSTRX. FRAME adds a slot index per symbol position. ROUTE introduces a new axis, sid, with a validity mask over sid and s. The sid wire passes over PACK and STRM, meaning one per stream. On the SDP branch the merge ends the sid axis: streams are serialised in time and sid survives only as a two-bit field. On the pixel branch the sid axis continues to four separate outputs.">',
         '<defs><marker id="ax5-vid" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-vid"/></marker>'
         '<marker id="ax5-sdp" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-sdp"/></marker></defs>']
    a = o.append
    # input axes
    for y, n in ((90, "ℓ"), (115, "s"), (140, "8")):
        a(f'<text class="t-name t-end" x="52" y="{y+4}">{n}</text><line class="wire" x1="60" y1="{y}" x2="540" y2="{y}"/>')
    a('<text class="t-note" x="22" y="70">dat</text>')
    # FRAME: slot index per s
    a('<rect class="box" x="130" y="104" width="60" height="22" rx="3"/><text class="t-sub" x="160" y="119" style="fill:var(--fg)">FRAME</text>')
    a('<line class="wire" x1="190" y1="170" x2="260" y2="170"/><path class="wire" d="M175,126 C175,170 185,170 190,170"/>'
      '<text class="t-w" x="200" y="186" style="fill:var(--fg)">slot · 6b per s</text>')
    # ROUTE: new axis
    a('<polygon class="box route" points="260,96 300,84 300,196 260,184"/><text class="t-sub" x="280" y="144" style="fill:var(--fg)">ROUTE</text>')
    a('<line class="wire" x1="300" y1="40" x2="1176" y2="40"/><path class="wire" d="M300,96 C300,60 300,40 320,40"/>'
      '<text class="t-w" x="326" y="34" style="fill:var(--fg)">sid · 4 (a new axis)</text>')
    a('<line class="wire" x1="300" y1="170" x2="400" y2="170"/><text class="t-w" x="304" y="186" style="fill:var(--fg)">v · bit[sid, s]</text>')
    a('<text class="t-note t-mid" x="270" y="226">route: adds an axis,</text><text class="t-note t-mid" x="270" y="242">items become sparse along it</text>')
    # PACK: s compacts, sid passes over
    a('<rect class="box" x="400" y="104" width="60" height="78" rx="3"/><text class="t-sub" x="430" y="148" style="fill:var(--fg)">PACK</text>')
    a('<line class="wire" x1="460" y1="115" x2="540" y2="115"/><text class="t-w" x="466" y="110" style="fill:var(--fg)">s′ dense</text>')
    a('<text class="t-note t-mid" x="430" y="226">sid passes over:</text><text class="t-note t-mid" x="430" y="242">one PACK per stream</text>')
    # STRM
    a('<rect class="box" x="540" y="78" width="80" height="150" rx="3"/><text class="t-sub" x="580" y="150" style="fill:var(--fg)">STRM</text>')
    a('<text class="t-note t-mid" x="580" y="70">one per stream</text>')
    # SDP branch
    a('<line class="wire-sdp" x1="620" y1="110" x2="760" y2="110"/><text class="t-w t-sdp" x="626" y="104">sdp beat · 32</text>')
    a('<circle class="dot" cx="700" cy="40" r="3.4"/><path class="wire" d="M700,40 C720,40 730,70 760,78"/>')
    a('<polygon class="box merge" points="760,66 810,78 810,122 760,134"/><text class="t-sub" x="785" y="104" style="fill:var(--fg)">SDPM</text>')
    a('<line class="wire-sdp" x1="810" y1="88" x2="1176" y2="88"/><text class="t-w t-sdp" x="830" y="83">sid · 2b field</text>')
    a('<line class="wire-sdp" x1="810" y1="112" x2="1176" y2="112" marker-end="url(#ax5-sdp)"/><text class="t-w t-sdp" x="830" y="127">32 · one stream at a time</text>')
    a('<text class="t-note t-mid" x="900" y="160">merge: the sid axis ends here.</text><text class="t-note t-mid" x="900" y="176">streams take turns in time, and</text><text class="t-note t-mid" x="900" y="192">sid survives as a field</text>')
    # pixel branch keeps the axis
    a('<line class="wire-vid" x1="620" y1="270" x2="1176" y2="270"/><line class="wire-vid" x1="620" y1="295" x2="1176" y2="295" marker-end="url(#ax5-vid)"/><line class="wire-vid" x1="620" y1="320" x2="1176" y2="320"/>'
      '<path class="wire-vid" d="M600,228 C600,270 610,270 620,270"/><path class="wire-vid" d="M590,228 C590,295 610,295 620,295"/><path class="wire-vid" d="M580,228 C580,320 610,320 620,320"/>'
      '<text class="t-w t-vid" x="640" y="265">ppc</text><text class="t-w t-vid" x="640" y="290">3</text><text class="t-w t-vid" x="640" y="315">bpc</text>')
    a('<text class="t-note t-vid t-end" x="1170" y="258">pixels keep the sid axis: four outputs, four vid_clk</text>')
    a('</svg>')
    return "\n".join(o)
