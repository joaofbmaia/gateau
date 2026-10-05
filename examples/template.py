"""TEMPLATE: copy this file to start a model. Every line runs; replace the invented design with yours.

The invented design: a streaming receiver. Words arrive on a link that cannot stall, a CRC checker
runs beside a delay line, and the result goes through a frame FIFO to a consumer that can stall.

Comments mark where each fact usually comes from: [doc] the documentation, [rtl] the RTL.
Leave a fact as None when you don't know it. The check reports `?` instead of guessing.
"""
from gateau import Buffer, Design

OUTSIDE = ("PHY", "APP")                         # actors you don't model, named so feedback can end there


def build() -> Design:
    # Design-wide names: axes are named dimensions of fields, used in widths and replication.
    d = Design("template", params=dict(P_LANES=4), axes=dict(lane=4, byte=8))
    d.domains += ["lnk_clk", "app_clk"]          # [doc] clocking
    d.modes += ["normal", "test"]                # [doc] operating modes; stages can be limited to some

    # Carriers: what flows, at what rate. A child carrier runs at a finer rate inside its parent.
    d.carrier("wrd", "one 32-bit word per lnk_clk", "lnk_clk")                  # [doc] datapath overview
    d.carrier("frm", "one frame", "app_clk")
    d.carrier("beat", "one 64-bit beat", "app_clk", parent="frm")

    # Fields: element width in bits × named axes. Group related fields so they can be read as "grp.*".
    d.field("wrd", "dat", 8, ("lane",))                                         # [rtl] port widths
    d.field("wrd", "sof", 1)
    d.field("wrd", "eof", 1)
    d.field("beat", "tdata", 8, ("byte",))
    d.field("beat", "tlast", 1)
    d.field("frm", "crc_ok", 1, availability="tail")     # known only once the whole frame has passed
    d.group("frm", "hdr", ["kind", "len"], 16)           # header fields, read together as "hdr.*"

    # State: storage outside the flow. Configuration is out-of-flow; list its fields so the
    # state-use check can find fields nobody reads.
    d.state("cfg", "out-of-flow", fields=["enable", "strip_crc"])               # [doc] register map

    # Boundaries: vertical cuts. rigid = cannot stall; elastic = ready/valid; lockstep = stalls together.
    d.boundary("b0", coupling="rigid")                                          # [rtl] register stages
    d.boundary("b2", after="b0", latency=2, coupling="rigid")
    d.boundary("bf", coupling="elastic")                                        # [rtl] FIFO output

    # Stages, in flow order (the order here sets the drawing's columns). Names in reads/writes
    # resolve on the stage's own carrier; "car.field" reaches another carrier; creates resolve on `out`.
    d.stage("ALIGN", "wrd", replicate="lane", writes=["dat"], state_reads=["cfg.enable"],
            note="per-lane word alignment")
    d.stage("DLY", "wrd", out="beat", between=("b0", "b2"), reads=["dat", "sof", "eof"],
            creates=["tdata", "tlast"], note="holds data 2 cycles for the CRC verdict")
    d.stage("CRC", "wrd", out="frm", between=("b0", "b2"), reads=["dat"], creates=["crc_ok"],
            state_reads=["cfg.strip_crc"])
    d.stage("FIFO", "beat", between=("b2", "bf"), reads=["frm.crc_ok"],
            buffer=Buffer(depth=2048, unit="byte", policy="drop", item_max=1518))   # [rtl] FIFO params
    d.stage("HDR", "beat", out="frm", reads=["tdata"], creates=["hdr.*"])
    d.stage("TEST", "frm", reads=["hdr.*"], modes=["test"], condition="P_TEST",
            note="loopback checker, test mode only")

    # Joins: where two paths must meet in step. lat = equal latency; fifo = in order; key = by tag.
    d.join("verdict-meets-data", "lat", ["DLY", "CRC"], evidence="rx.v: data_d1 aligned to crc_valid")

    # Feedback: data (bypass), ctrl (control back upstream), flow (backpressure).
    d.fb("ctrl", "ALIGN", "PHY", note="bitslip until aligned")
    d.fb("flow", "HDR", "FIFO", note="tready")
    return d
