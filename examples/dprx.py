"""Parretto DisplayPort RX (prt_dprx_top), as in docs/models/dprx.gateau and study 04.

Modelled by hand from Parretto's source-available RTL. Structure only; no code reproduced.
"""
from gateau import Buffer, Design

OUTSIDE = ("PHY", "PM")


def build() -> Design:
    d = Design("dprx",
               params=dict(P_LANES=4, P_SPL=2, P_PPC=2, P_BPC=8, P_SDP=True, P_MST=True),
               axes=dict(l=4, s=2, ppc=2, rgb=3))
    d.domains += ["lnk_clk", "vid_clk", "sdp_clk", "sys_clk"]
    d.modes += ["training", "normal"]

    # carriers
    d.carrier("msg", "16-bit message, routed by ID", "lnk_clk", ring=True)
    d.carrier("sym", "one symbol group per lnk_clk", "lnk_clk")
    d.carrier("pix", "P_PPC pixels per vid_clk", "vid_clk")
    d.carrier("sdpk", "secondary data packet", "sdp_clk")
    d.carrier("sdpb", "32-bit SDP beat", "sdp_clk", parent="sdpk")

    # fields
    d.field("sym", "k", 1, ("l", "s"))
    d.field("sym", "dat", 8, ("l", "s"))
    d.field("sym", "lock", 1)
    d.group("sym", "tag", ["sol", "eol", "vid", "sdp", "msa", "vbid"], 1, ("l", "s"))
    d.field("pix", "data", 8, ("ppc", "rgb"))
    d.field("pix", "sof", 1)
    d.field("pix", "eol", 1)
    d.field("sdpk", "len", 6, availability="tail")
    d.field("sdpb", "dat", 32)

    # state
    d.state("cfg", "out-of-flow", fields=["lnk_en", "lanes", "scrm_en", "mst_en", "bpc"])
    d.state("cfg_tps", "out-of-flow")
    d.state("ila", "in-flow")
    d.state("msa_ram", "in-flow")
    d.state("vcfg", "out-of-flow", fields=["hwidth"])

    # boundaries
    d.boundary("b0", coupling="rigid")                       # TRN output, lanes aligned
    d.boundary("b1", after="b0", latency=1, coupling="rigid")
    d.boundary("bsdp", coupling="elastic")                    # SDP FIFO output, sdp_clk
    d.boundary("bvid", coupling="elastic")                    # VID FIFO output, vid_clk

    # stages, in flow order
    d.stage("CTL", "msg", state_writes=["cfg"])
    d.stage("TRN", "sym", replicate="l", writes=["k", "dat"],
            state_reads=["cfg_tps"], state_writes=["ila", "cfg_tps"])
    d.stage("PARS", "sym", between=("b0", "b1"), reads=["k", "dat"], creates=["tag.*"],
            requires=["ila"], state_reads=["cfg.lnk_en"],
            note="reads lane 0 only; lanes are aligned by TRN")
    d.stage("SCRM", "sym", between=("b0", "b1"), replicate="l", writes=["k", "dat", "lock"],
            state_reads=["cfg.lanes", "cfg.mst_en"], note="enable tied to 1 in the RTL")
    d.stage("TAGB", "sym", broadcast=(("tag.*",), "l"), note="lane-0 tags copied to every lane")
    d.stage("MSA", "sym", reads=["k", "dat", "tag.msa"], consumes=["tag.msa"],
            state_reads=["cfg.lanes"], state_writes=["msa_ram"], emits=["msg"], modes=["normal"])
    d.stage("SDP", "sym", out="sdpk", between=("b1", "bsdp"), condition="P_SDP",
            reads=["k", "dat", "tag.sdp"], consumes=["tag.sdp"], creates=["len", "sdpb.dat"],
            emits=["msg"], buffer=Buffer(depth=32, unit="word"), modes=["normal"])
    d.stage("VID", "sym", out="pix", between=("b1", "bvid"),
            consumes=["sol", "eol", "vid", "vbid", "k", "dat", "lock"], creates=["data", "sof", "eol"],
            state_reads=["cfg.bpc", "vcfg"], state_writes=["vcfg"],
            buffer=Buffer(depth=64, unit="word"), modes=["normal"])

    # joins
    d.join("tags-meet-data", "lat", ["PARS", "SCRM"], evidence="comments at pars.sv:1394, scrm.sv:128")
    d.join("sdp-length", "fifo", ["SDP"])

    # feedback
    d.fb("data", "SCRM", "TRN", modes=["training"], note="TPS4 is checked descrambled")
    d.fb("ctrl", "TRN", "PM", note="training status via msg")
    d.fb("ctrl", "PM", "CTL", note="cfg and cfg_tps via msg")
    d.fb("ctrl", "VID", "PM", note="end-of-vblank irq")
    return d
