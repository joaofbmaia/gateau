"""Places the marks for the DP RX bus-view figures in study 04 (gateau notation v1.1).

svg(mode, overlay) returns one SVG string.
  mode:    "normal" | "training"   (inactive parts are faded, layout never moves)
  overlay: None | "cost" | "checks"
The layout is fixed by hand below; this script only places it.
"""

Y = dict(msg=145, lock=208, k=236, dat=264, sol=298, eol=318, vid=338, sdp=358, msa=378, vbid=398,
         len=472, sdat=492, pix=540)
BITS = dict(lock=1, k=8, dat=64, sol=8, eol=8, vid=8, sdp=8, msa=8, vbid=8, len=6, sdat=32, pix=48)


def svg(mode="normal", overlay=None):
    tr = mode == "training"
    cost = overlay == "cost"
    checks = overlay == "checks"
    uid = f"{mode[0]}{(overlay or 'n')[0]}"
    o = []

    def a(s, chk=False):
        o.append(f'<g class="chk">{s}</g>' if chk else s)

    off = ' class="off"' if tr else ''        # inactive in training
    on_t = '' if tr else ' class="off"'       # active only in training

    def w(row, base="lane"):
        """stroke for a row: fixed in the plain view, proportional to bits in the cost overlay"""
        return f' style="stroke-width:{max(1.2, BITS[row] * 0.16):.2f}"' if cost else ''

    root_cls = "ov-checks" if checks else ""
    a(f'<svg class="{root_cls}" viewBox="0 0 1200 660" role="img" aria-label="DP RX bus view, {mode} mode{", " + overlay + " overlay" if overlay else ""}.">')
    a('<defs>'
      f'<marker id="{uid}-ink" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-ink"/></marker>'
      f'<marker id="{uid}-vid" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-vid"/></marker>'
      f'<marker id="{uid}-mut" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-muted"/></marker>'
      '</defs>')
    ink, vidm, mut = f'url(#{uid}-ink)', f'url(#{uid}-vid)', f'url(#{uid}-mut)'

    tag = f"mode: {mode}" + (f" · {overlay}" if overlay else "")
    a(f'<rect class="modetag" x="1010" y="586" width="178" height="22" rx="11"/>'
      f'<text class="t-w t-mid" x="1099" y="601" style="fill:var(--fg)">{tag}</text>', chk=True)

    # ── state pills (out-of-flow state read from far away is drawn as stubs, rule v1.1)
    a('<rect class="store" x="170" y="22" width="490" height="18" rx="9"/>'
      '<text class="t-w" x="196" y="35" style="fill:var(--fg)">cfg · {lnk_en, lanes, scrm_en, mst_en, bpc}</text>', chk=True)
    a('<rect class="store" x="215" y="48" width="70" height="18" rx="9"/>'
      '<text class="t-w t-mid" x="250" y="61" style="fill:var(--fg)">cfg_tps</text>')
    a('<rect class="store" x="262" y="74" width="150" height="18" rx="9"/>'
      '<text class="t-w" x="300" y="87" style="fill:var(--fg)">ila · lanes aligned</text>', chk=True)
    a(f'<g{off}><rect class="store" x="620" y="74" width="100" height="18" rx="9"/>'
      '<text class="t-w t-mid" x="696" y="87" style="fill:var(--fg)">msa_ram</text></g>')
    a(f'<g{off}><rect class="store-vid" x="880" y="48" width="130" height="18" rx="9"/>'
      '<text class="t-w t-vid" x="912" y="61">vcfg · vid_clk</text></g>')

    # ── carrier bands
    a('<rect class="carrier" x="116" y="122" width="1072" height="46"/>')
    a('<rect class="band-rigid" x="116" y="186" width="744" height="226"/>')
    a('<rect class="carrier" x="860" y="186" width="328" height="226"/>')
    a('<rect class="carrier" x="116" y="448" width="1072" height="56"/>')
    a('<rect class="carrier" x="116" y="516" width="1072" height="44"/>')
    a('<text class="t-w" x="122" y="199" style="fill:var(--fg)">rigid: the link cannot stall</text>')

    def lab(name, wd, y, cls="t-name"):
        if cost and name.split()[0] in ("lock", "k", "dat", "data", "len") or cost and cls == "t-tag":
            pass
        a(f'<text class="{cls}" x="14" y="{y+4}">{name}</text><text class="t-w t-end" x="110" y="{y+4}">{wd}</text>')
    a('<text class="t-band" x="14" y="132">msg · lnk_clk</text>'); lab("msg", "16b ring", Y['msg'])
    a('<text class="t-band" x="14" y="196">sym · lnk_clk</text>')
    if cost:
        lab("lock", "1 b", Y['lock']); lab("k", "8 b", Y['k']); lab("dat", "64 b", Y['dat'])
        for t in ("sol", "eol", "vid", "sdp", "msa", "vbid"):
            lab(t, "8 b", Y[t], "t-tag")
        a('<text class="t-band t-sdp" x="14" y="458">sdpk ⊃ sdpb · sdp_clk</text>')
        lab("len ◆", "6 b", Y['len']); lab("dat", "32 b", Y['sdat'])
        a('<text class="t-band t-vid" x="14" y="526">pix · vid_clk</text>')
        lab("data", "48 b", Y['pix'])
    else:
        lab("lock", "1", Y['lock']); lab("k", "ℓ·s", Y['k']); lab("dat", "ℓ·s·8", Y['dat'])
        for t in ("sol", "eol", "vid", "sdp", "msa", "vbid"):
            lab(t, "ℓ·s", Y[t], "t-tag")
        a('<text class="t-band t-sdp" x="14" y="458">sdpk ⊃ sdpb · sdp_clk</text>')
        lab("len ◆", "u6", Y['len']); lab("dat", "32", Y['sdat'])
        a('<text class="t-band t-vid" x="14" y="526">pix · vid_clk</text>')
        lab("data", "PPC·3·BPC", Y['pix'])

    for r in ("lock", "k", "dat", "sol", "eol", "vid", "sdp", "msa", "vbid", "len", "sdat", "pix"):
        a(f'<line class="track" x1="116" y1="{Y[r]}" x2="1188" y2="{Y[r]}"/>')

    # ── named boundaries (v1.1): PARS and SCRM both sit between b0 and b1
    a('<line class="edge" x1="335" y1="186" x2="335" y2="412"/>'
      '<line class="edge" x1="540" y1="186" x2="540" y2="412"/>'
      '<text class="t-w t-mid" x="335" y="182">b0</text>'
      '<text class="t-w t-mid" x="540" y="182">b1 = b0 + 1</text>', chk=True)

    # ── live rows
    a('<line class="msg" x1="116" y1="143" x2="1176" y2="143"/><line class="msg" x1="116" y1="147" x2="1176" y2="147"/>')
    a(f'<line class="lane" x1="116" y1="236" x2="860" y2="236"{w("k")}/><line class="lane" x1="116" y1="264" x2="860" y2="264"{w("dat")}/>')
    a(f'<line class="lane" x1="520" y1="208" x2="860" y2="208"{w("lock")}/>'
      '<text class="t-w" x="524" y="203" style="fill:var(--fg)">≈</text>')
    tags = ''.join(f'<line class="lane" x1="420" y1="{Y[t]}" x2="{end}" y2="{Y[t]}"{w(t)}/>'
                   for t, end in (("sol", 860), ("eol", 860), ("vid", 860), ("sdp", 720), ("msa", 620), ("vbid", 860)))
    a(f'<g{off}>{tags}</g>')
    if cost:
        a(f'<g{off}><text class="t-w" x="596" y="292" style="fill:var(--fg)">48 b carried · 12 b distinct (Δℓ copies)</text></g>')
    a(f'<g{off}>'
      f'<line class="lane-sdp" x1="790" y1="{Y["len"]}" x2="1182" y2="{Y["len"]}"{w("len")}/>'
      f'<polygon class="tailmark" points="802,{Y["len"]-6} 808,{Y["len"]} 802,{Y["len"]+6} 796,{Y["len"]}"/>'
      f'<line class="lane-sdp" x1="790" y1="{Y["sdat"]}" x2="1182" y2="{Y["sdat"]}"{w("sdat")}/>'
      f'<line class="lane-vid" x1="930" y1="{Y["pix"]}" x2="980" y2="{Y["pix"]}"{w("pix")}/>'
      f'<line class="lane-vid" x1="1050" y1="{Y["pix"]}" x2="1180" y2="{Y["pix"]}" marker-end="{vidm}"{w("pix")}/>'
      '<text class="t-w t-vid t-mid" x="1115" y="532">» VID_RDY</text>'
      '</g>')

    # ── taps
    a(f'<line class="conn" x1="185" y1="135" x2="185" y2="42" marker-end="{ink}"/>')            # CTL writes cfg
    a(f'<line class="conn" x1="245" y1="222" x2="245" y2="68" marker-end="{ink}"/>')            # TRN taps msg, writes cfg_tps
    a(f'<line class="conn" x1="275" y1="222" x2="275" y2="94" marker-end="{ink}"/>', chk=True)  # TRN writes ila
    a(f'<g{off}><line class="conn" x1="405" y1="92" x2="405" y2="288"/><circle class="dot" cx="405" cy="92" r="3.2"/></g>', chk=True)  # PARS requires ila
    a(f'<g{off}><line class="conn" x1="385" y1="236" x2="385" y2="288"/>'
      '<text class="t-w" x="352" y="252" style="fill:var(--fg)">ℓ=0</text></g>')
    a('<line class="conn" x1="485" y1="40" x2="485" y2="196"/>')                                 # SCRM reads cfg (one band: a tap)
    a(f'<g{off}>'
      '<line class="conn" x1="640" y1="40" x2="640" y2="368"/><circle class="dot" cx="640" cy="40" r="3.2"/>'  # MSA reads cfg (one band: a tap), k, dat
      f'<line class="conn" x1="670" y1="368" x2="670" y2="94" marker-end="{ink}"/>'             # MSA writes msa_ram
      f'<line class="conn" x1="685" y1="368" x2="685" y2="150" marker-end="{ink}"/>'            # MSA emits to msg
      '<line class="conn" x1="740" y1="236" x2="740" y2="348"/>'                                # SDP reads k, dat
      f'<line class="conn" x1="775" y1="348" x2="775" y2="150" marker-end="{ink}"/>'            # SDP VSC to msg
      f'<line class="conn" x1="900" y1="196" x2="900" y2="68" marker-end="{ink}"/>'             # VID taps msg, writes vcfg
      '<line class="conn" x1="1015" y1="528" x2="1015" y2="512"/>'                              # vmap reads cfg.bpc, vcfg (stub)
      '<rect class="stub" x="972" y="499" width="86" height="13" rx="6"/><text class="t-stub" x="1015" y="509">cfg.bpc · vcfg</text>'
      '</g>')

    # ── gutter
    a('<rect class="gutter" x="116" y="578" width="880" height="74" rx="3"/>'
      '<text class="t-note" x="14" y="598">gutter</text>')
    a(f'<g{off}><path class="back-ctl" d="M895,560 L895,600 L139,600 L139,159" marker-end="{mut}"/>'
      '<text class="t-w" x="450" y="595">ctrl · end-of-vblank irq → PM (stable video)</text></g>')
    a(f'<g{on_t}><path class="back" style="stroke:var(--fg)" d="M490,278 L490,630 L255,630 L255,280" marker-end="{ink}"/>'
      '<text class="t-w" x="510" y="626" style="fill:var(--fg)">data · descrambled TPS4 → TRN.chk</text></g>')

    # ── boxes
    a('<rect class="box-opt" x="120" y="133" width="40" height="24" rx="3"/><text class="t-sub" x="140" y="149" style="fill:var(--muted)">PM</text>')
    a('<rect class="box" x="168" y="135" width="36" height="20" rx="3"/><text class="t-sub" x="186" y="149" style="fill:var(--fg)">CTL</text>')
    a(f'<rect class="box{" hot" if tr else ""}" x="215" y="222" width="80" height="56" rx="3"/>'
      f'<text class="t-box" x="255" y="246">TRN ×ℓ</text><text class="t-sub" x="255" y="262">{"chk · ila" if tr else "ila"}</text>', chk=True)
    a(f'<g{off}><rect class="box" x="350" y="288" width="70" height="120" rx="3"/><text class="t-box" x="385" y="352">PARS</text></g>', chk=True)
    a('<rect class="box" x="450" y="196" width="70" height="82" rx="3"/><text class="t-box" x="485" y="236">SCRM ×ℓ</text><text class="t-sub" x="485" y="252">∧ → lock</text>', chk=True)
    a(f'<g{off}>'
      '<rect class="box" x="555" y="288" width="30" height="120" rx="3"/><text class="t-sub" x="570" y="352" style="fill:var(--fg)">Δℓ</text>'
      '<rect class="box" x="620" y="368" width="70" height="20" rx="3"/><text class="t-box" x="655" y="382">MSA</text></g>')
    a(f'<g{off}><rect class="box-opt" x="720" y="348" width="70" height="152" rx="3"/><text class="t-box" x="755" y="416">SDP</text><text class="t-sub" x="755" y="432">FIFO 32</text><text class="t-sub" x="755" y="446">+ len 8</text></g>', chk=True)
    a(f'<g{off}>'
      '<rect class="fill-box" x="860" y="196" width="70" height="320"/><rect class="fill-vid-soft" x="860" y="516" width="70" height="44"/><rect class="outline" x="860" y="196" width="70" height="364" rx="3"/>'
      '<text class="t-box" x="895" y="300">VID</text><text class="t-sub" x="895" y="316">lclk · lmap</text><text class="t-sub" x="895" y="542" style="fill:var(--fg)">fifo 64</text></g>', chk=True)
    a(f'<g{off}><rect class="box-vid" x="980" y="528" width="70" height="24" rx="3"/><text class="t-box t-vid" x="1015" y="544">vmap</text></g>')

    # ── dots
    for x, y in [(245, 145), (485, 40), (320, 236), (320, 264)]:
        a(f'<circle class="dot" cx="{x}" cy="{y}" r="3.2"/>')
    a(f'<g{off}>' + ''.join(f'<circle class="dot" cx="{x}" cy="{y}" r="3.2"/>' for x, y in
      [(385, 236), (385, 264), (640, 236), (640, 264), (740, 236), (740, 264), (900, 145)]) + '</g>')

    # ── check badges
    a('<rect class="badge-bad" x="300" y="98" width="172" height="18" rx="9"/>'
      '<text class="t-w t-bad t-mid" x="386" y="111">⚑ cfg.scrm_en never read</text>', chk=True)
    a(f'<g{off}>'
      '<rect class="badge-acc" x="300" y="418" width="260" height="18" rx="9"/>'
      '<text class="t-w t-acc t-mid" x="430" y="431">⟂ lat by construction: both b0 → b1</text></g>', chk=True)
    a(f'<g{off}><rect class="badge-acc" x="940" y="430" width="160" height="16" rx="8"/>'
      '<text class="t-w t-acc t-mid" x="1020" y="442">⟂ fifo(data, len)</text></g>', chk=True)
    a(f'<g{off}><rect class="badge-acc" x="700" y="562" width="290" height="16" rx="8"/>'
      '<text class="t-w t-acc t-mid" x="845" y="574">rigid edge: 64 words vs vid_clk ratio ?</text></g>', chk=True)

    a('</svg>')
    return '\n'.join(o)
