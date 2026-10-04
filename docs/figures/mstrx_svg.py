"""Places the marks for the MSTRX figures in study 05 (gateau notation v1.2). Hand layout."""


def _deck(x, y, w, h, cls="carrier"):
    """an indexed carrier: the band, with two offset outlines behind it"""
    return (f'<rect class="deck" x="{x+8}" y="{y+8}" width="{w}" height="{h}"/>'
            f'<rect class="deck" x="{x+4}" y="{y+4}" width="{w}" height="{h}"/>'
            f'<rect class="{cls}-solid" x="{x}" y="{y}" width="{w}" height="{h}"/>')


def bus(overlay=None):
    checks = overlay == "checks"
    o = []

    def a(s, chk=False):
        o.append(f'<g class="chk">{s}</g>' if chk else s)

    a(f'<svg class="{"ov-checks" if checks else ""}" viewBox="0 0 1200 700" role="img" aria-label="Bus view of the invented multi-stream receiver{", checks overlay" if checks else ""}.">')
    a('<defs>'
      '<marker id="m-ink" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-ink"/></marker>'
      '<marker id="m-vid" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-vid"/></marker>'
      '<marker id="m-sdp" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-sdp"/></marker>'
      '<marker id="m-mut" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-muted"/></marker>'
      '</defs>')

    # state
    a('<rect class="store" x="300" y="22" width="440" height="18" rx="9"/>'
      '<text class="t-w" x="320" y="35" style="fill:var(--fg)">vcpt · slot → sid · epoch: active ← shadow at the MTP after ACT</text>', chk=True)
    a('<rect class="store" x="170" y="48" width="96" height="18" rx="9"/>'
      '<text class="t-w t-mid" x="218" y="61" style="fill:var(--fg)">mtp ↻ 64</text>')

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
    a('<line class="lane" x1="116" y1="150" x2="130" y2="150"/><line class="lane" x1="210" y1="150" x2="380" y2="150"/>')
    a('<line class="lane" x1="330" y1="172" x2="380" y2="172"/>')
    a('<line class="lane" x1="460" y1="242" x2="520" y2="242"/><line class="lane" x1="460" y1="266" x2="520" y2="266"/>')
    a('<line class="lane" x1="580" y1="350" x2="620" y2="350"/>')
    a('<line class="lane-sdp" x1="740" y1="432" x2="822" y2="432"/><line class="lane-sdp" x1="740" y1="454" x2="822" y2="454"/>')
    a('<polygon class="tailmark" points="752,426 758,432 752,438 746,432"/>')
    a('<line class="lane-sdp" x1="890" y1="420" x2="1182" y2="420"/>'
      '<text class="t-w" x="1150" y="415" style="fill:var(--fg)">sid</text>'
      '<line class="lane-sdp" x1="890" y1="442" x2="1182" y2="442"/>'
      '<polygon class="tailmark" points="902,436 908,442 902,448 896,442"/>'
      '<line class="lane-sdp" x1="890" y1="464" x2="1182" y2="464" marker-end="url(#m-sdp)"/>')
    a('<line class="lane-vid" x1="740" y1="540" x2="1176" y2="540" marker-end="url(#m-vid)"/>'
      '<text class="t-w t-vid t-end" x="1170" y="532">4 outputs, one per vid_clk[sid]</text>')

    # taps
    a('<line class="conn" x1="310" y1="94" x2="310" y2="42" marker-end="url(#m-ink)"/><circle class="dot" cx="310" cy="94" r="3.2"/>'
      '')
    a('<line class="conn" x1="285" y1="150" x2="285" y2="158"/><circle class="dot" cx="285" cy="150" r="3.2"/>')
    a('<line class="conn" x1="252" y1="158" x2="252" y2="68" marker-end="url(#m-ink)"/>')
    a('<line class="conn" x1="322" y1="158" x2="322" y2="42" marker-end="url(#m-ink)"/><text class="t-w" x="327" y="110" style="fill:var(--fg)">swap</text>', chk=True)
    a('<line class="conn" x1="402" y1="40" x2="402" y2="156"/><circle class="dot" cx="402" cy="40" r="3.2"/>', chk=True)
    a('<line class="conn" x1="700" y1="228" x2="700" y2="100" marker-end="url(#m-ink)"/>', chk=True)

    # boxes
    a('<rect class="box-opt" x="120" y="82" width="40" height="24" rx="3"/><text class="t-sub" x="140" y="98" style="fill:var(--muted)">PM</text>')
    a('<rect class="box" x="130" y="138" width="80" height="24" rx="3"/><text class="t-box" x="170" y="154">LINK ≡ 04</text>')
    a('<rect class="box" x="240" y="158" width="90" height="26" rx="3"/><text class="t-box" x="285" y="175">FRAME</text>')
    a('<polygon class="box route" points="380,136 460,216 460,296 380,184"/>'
      '<text class="t-box" x="426" y="236">ROUTE</text><text class="t-sub" x="426" y="250">per s</text>', chk=True)
    a('<rect class="box" x="520" y="228" width="60" height="146" rx="3"/><text class="t-box" x="550" y="290">PACK</text>'
      '<text class="t-sub" x="550" y="306">×sid</text><text class="t-sub" x="550" y="320">FIFO 64</text>', chk=True)
    a('<rect class="box" x="620" y="228" width="120" height="342" rx="3"/>'
      '<text class="t-box" x="680" y="300">STRM ×sid</text><text class="t-sub" x="680" y="316">PARS · MSA</text>'
      '<text class="t-sub" x="680" y="330">SDP · VID</text><text class="t-sub" x="680" y="344">= study 04</text>', chk=True)
    a('<polygon class="box merge" points="822,398 890,410 890,474 822,486"/>'
      '<text class="t-box" x="856" y="446">SDPM</text>', chk=True)
    a('<text class="t-sub" x="856" y="462" style="fill:var(--fg)">RR · packet</text>')
    a('<polygon class="box merge" points="700,84 730,90 730,102 700,108"/>', chk=True)
    a('<text class="t-w" x="736" y="110" style="fill:var(--fg)">MSGM · ring order</text>')

    # gutter
    a('<rect class="gutter" x="116" y="604" width="880" height="86" rx="3"/><text class="t-note" x="14" y="624">gutter</text>')
    a('<path class="flow" d="M856,486 L856,636 L700,636 L700,572" marker-end="url(#m-mut)"/>'
      '<text class="t-w" x="712" y="630">flow · SDPM grant → one stream at a time</text>')
    a('<path class="back-ctl" d="M650,570 L650,668 L140,668 L140,108" marker-end="url(#m-mut)"/>'
      '<text class="t-w" x="300" y="663">ctrl · per-stream vblank irq → PM</text>')

    # check badges
    a('<rect class="badge-ok" x="760" y="22" width="270" height="18" rx="9"/>'
      '<text class="t-w t-ok t-mid" x="895" y="35">✓ epoch: one reader, one swap point</text>', chk=True)
    a('<rect class="badge-bad" x="760" y="48" width="300" height="18" rx="9"/>'
      '<text class="t-w t-bad t-mid" x="910" y="61">✗ MSGM: same message ID from 4 streams, no sid</text>', chk=True)
    a('<rect class="badge-ok" x="250" y="300" width="200" height="16" rx="8"/>'
      '<text class="t-w t-ok t-mid" x="350" y="312">✓ route covers all 64 slots</text>', chk=True)
    a('<rect class="badge-acc" x="430" y="378" width="150" height="16" rx="8"/>'
      '<text class="t-w t-acc t-mid" x="505" y="390">rigid edge: FIFO ≥ run</text>', chk=True)
    a('<rect class="badge-ok" x="900" y="484" width="280" height="16" rx="8"/>'
      '<text class="t-w t-ok t-mid" x="1040" y="496">✓ SDPM: creates sid · never splits a packet</text>', chk=True)
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
    o.append('<polygon class="box route" points="580,110 640,80 640,180 580,150"/><text class="t-sub" x="610" y="134" style="fill:var(--fg)">ROUTE</text>')
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
