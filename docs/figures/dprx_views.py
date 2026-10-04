"""Axis and time views of the DP RX for study 04 (hand layout)."""


def axis_view():
    return '''<svg viewBox="0 0 1200 330" role="img" aria-label="Axis view of the DP RX symbol path. The lane axis passes over TRN and SCRM, meaning one per lane. TRN deskews each lane by a delay set from the alignment state. The data forks; PARS takes lane 0 only and its tags are copied back across the lane axis. SCRM's per-lane lock is reduced with AND. VID reshapes lanes and symbols into FIFO stripes, crosses into the video clock domain, and reshapes into pixels.">
  <defs><marker id="ax-vid" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrow-vid"/></marker></defs>
  <text class="t-note" x="22" y="40">dat</text>
  <text class="t-name t-end" x="52" y="64">ℓ</text><text class="t-name t-end" x="52" y="89">s</text><text class="t-name t-end" x="52" y="114">8</text>
  <line class="wire" x1="60" y1="60" x2="640" y2="60"/>
  <line class="wire" x1="60" y1="85" x2="640" y2="85"/>
  <line class="wire" x1="60" y1="110" x2="640" y2="110"/>

  <rect class="box" x="120" y="72" width="70" height="50" rx="3"/><text class="t-box" x="155" y="94">TRN</text>
  <polyline class="conn" points="134,116 134,110 146,110 146,104 158,104 158,98" />
  <text class="t-sub" x="172" y="114" style="fill:var(--fg)">?</text>
  <text class="t-note t-mid" x="140" y="28">ℓ passes over: one per lane</text>
  <text class="t-note t-mid" x="155" y="146">deskew by ila</text>

  <path class="wire" d="M230,60 C270,60 270,190 300,190"/>
  <path class="wire" d="M230,85 C270,85 270,215 330,215"/>
  <path class="wire" d="M230,110 C270,110 270,240 330,240"/>
  <circle class="dot" cx="230" cy="60" r="3.4"/><circle class="dot" cx="230" cy="85" r="3.4"/><circle class="dot" cx="230" cy="110" r="3.4"/>
  <text class="t-note t-mid" x="230" y="44">fork</text>

  <polygon class="box" points="298,182 320,182 328,190 320,198 298,198"/><text class="t-sub" x="311" y="194" style="fill:var(--fg)">0</text>
  <text class="t-note t-mid" x="311" y="276">index ℓ = 0</text>
  <rect class="box" x="330" y="202" width="60" height="50" rx="3"/><text class="t-box" x="360" y="232">PARS</text>
  <line class="wire" x1="390" y1="215" x2="640" y2="215"/><text class="t-w" x="396" y="210" style="fill:var(--fg)">s</text>
  <line class="wire" x1="390" y1="240" x2="640" y2="240"/><text class="t-w" x="396" y="235" style="fill:var(--fg)">6 tags</text>
  <circle class="dot" cx="440" cy="215" r="3.4"/>
  <path class="wire" d="M440,215 C458,215 460,190 480,190 L640,190"/><text class="t-w" x="486" y="185" style="fill:var(--fg)">ℓ</text>
  <text class="t-note t-mid" x="460" y="276">Δℓ: copy to every lane</text>

  <rect class="box" x="330" y="72" width="60" height="50" rx="3"/><text class="t-box" x="360" y="101">SCRM</text>
  <path class="wire" d="M375,122 C375,150 385,150 400,150 L440,150"/><text class="t-w" x="404" y="145" style="fill:var(--fg)">ℓ</text>
  <polygon class="box" points="440,141 460,150 440,159"/>
  <line class="wire" x1="460" y1="150" x2="640" y2="150"/><text class="t-w" x="466" y="145" style="fill:var(--fg)">lock</text>
  <text class="t-note" x="466" y="170">∧ over cfg.lanes</text>

  <rect class="badge-acc" x="500" y="96" width="132" height="34" rx="9"/>
  <text class="t-w t-acc t-mid" x="566" y="110">⟂ zip on ℓ, s</text>
  <text class="t-w t-acc t-mid" x="566" y="124">both b0 → b1</text>

  <rect class="bar" x="640" y="48" width="8" height="204"/>
  <text class="t-note t-mid" x="644" y="38">lmap</text>
  <line class="wire" x1="648" y1="95" x2="760" y2="95"/><text class="t-w" x="654" y="90" style="fill:var(--fg)">stripe 4</text>
  <line class="wire" x1="648" y1="120" x2="760" y2="120"/><text class="t-w" x="654" y="115" style="fill:var(--fg)">segment 4</text>
  <line class="wire" x1="648" y1="145" x2="760" y2="145"/><text class="t-w" x="654" y="140" style="fill:var(--fg)">9 b</text>
  <text class="t-note t-mid" x="660" y="276">reshape ℓ·s → stripes × segments</text>

  <rect class="fill-box" x="760" y="82" width="25" height="76"/><rect class="fill-vid-soft" x="785" y="82" width="25" height="76"/><rect class="outline" x="760" y="82" width="50" height="76" rx="2"/>
  <text class="t-sub" x="785" y="124" style="fill:var(--fg)">FIFO</text><text class="t-sub" x="785" y="138" style="fill:var(--fg)">64</text>
  <line class="wire-vid" x1="810" y1="95" x2="900" y2="95"/>
  <line class="wire-vid" x1="810" y1="120" x2="900" y2="120"/>
  <line class="wire-vid" x1="810" y1="145" x2="900" y2="145"/>
  <text class="t-note t-mid" x="830" y="296">hue change = lnk_clk → vid_clk</text>

  <rect class="bar-vid" x="900" y="78" width="8" height="84"/>
  <text class="t-note t-vid t-mid" x="904" y="70">vmap</text>
  <line class="wire-vid" x1="908" y1="95" x2="1176" y2="95"/><text class="t-w t-vid" x="914" y="90">ppc</text>
  <line class="wire-vid" x1="908" y1="120" x2="1176" y2="120" marker-end="url(#ax-vid)"/><text class="t-w t-vid" x="914" y="115">3</text>
  <line class="wire-vid" x1="908" y1="145" x2="1176" y2="145"/><text class="t-w t-vid" x="914" y="140">bpc</text>
  <text class="t-note t-mid" x="1030" y="276">reshape → pixels, reads cfg.bpc</text>
</svg>'''


def _grid(ox, title, rows, cells, ncyc=6, x0=150, cw=72, top=48, rh=30):
    o = [f'<text class="t-name" x="{ox+10}" y="20" style="font-weight:600">{title}</text>']
    for i in range(ncyc):
        o.append(f'<text class="t-w t-mid" x="{ox+x0+i*cw+cw/2}" y="{top-8}">c{i}</text>')
    for r, name in enumerate(rows):
        y = top + r * rh
        o.append(f'<text class="t-note" x="{ox+10}" y="{y+17}">{name}</text>')
    for (r, c, txt, cls) in cells:
        y = top + r * rh
        x = ox + x0 + c * cw
        tc = {"cell": "", "cell-acc": " t-acc", "cell-ok": " t-ok", "cell-bad": " t-bad"}[cls]
        fill = ' style="fill:var(--fg)"' if cls == "cell" else ''
        o.append(f'<rect class="{cls}" x="{x+4}" y="{y}" width="{cw-8}" height="22" rx="2"/>'
                 f'<text class="t-w t-mid{tc}" x="{x+cw/2}" y="{y+15}"{fill}>{txt}</text>')
    return '\n'.join(o)


def time_view():
    # left: interlane alignment (illustrative skew)
    arrive = {0: 2, 1: 1, 2: 3, 3: 2}
    cells = []
    for lane, c in arrive.items():
        cells.append((lane, c, "BS", "cell-acc"))
    for lane in range(4):
        cells.append((4 + lane, 4, "BS", "cell-ok"))
    left = _grid(0, "Interlane alignment (TRN.ila)",
                 ["lane 0 in", "lane 1 in", "lane 2 in", "lane 3 in",
                  "lane 0 out", "lane 1 out", "lane 2 out", "lane 3 out"], cells, ncyc=6, x0=110, cw=66, rh=28)
    # right: join at b1
    ox = 620
    cells = [(0, i, f"D{i}", "cell") for i in range(5)]
    cells += [(1, i + 1, f"T{i}", "cell-acc") for i in range(4)]
    cells += [(2, i + 1, f"D{i}′", "cell") for i in range(4)]
    cells += [(3, i + 1, f"D{i}′·T{i}", "cell-ok") for i in range(4)]
    cells += [(4, 1, "?·T0", "cell-bad")] + [(4, i + 2, f"D{i}′·T{i+1}", "cell-bad") for i in range(3)]
    right = _grid(ox, "The join at b1 (PARS ∥ SCRM)",
                  ["TRN out (b0)", "PARS tags", "SCRM dat", "joined at b1", "if SCRM were +2"], cells,
                  ncyc=5, x0=120, cw=84, rh=30)
    return f'''<svg viewBox="0 0 1200 290" role="img" aria-label="Two time views. Left: a blanking-start symbol arrives on four lanes at different cycles and leaves all four lanes in the same cycle after interlane alignment. Right: with both PARS and SCRM one cycle after b0, each joined word pairs data with its own tags; if SCRM took two cycles, every pairing would shift by one symbol.">
{left}
{right}
  <text class="t-note" x="10" y="282">skew values are illustrative</text>
  <text class="t-note" x="630" y="210">This row is why "both b0 → b1" matters: one extra register in SCRM</text>
  <text class="t-note" x="630" y="226">and every word carries the next word's tags. Nothing in the RTL</text>
  <text class="t-note" x="630" y="242">checks it; the model now states it as a boundary, so a tool can.</text>
</svg>'''
