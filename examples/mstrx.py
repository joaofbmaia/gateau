"""MSTRX: an INVENTED multi-stream DisplayPort receiver, as in docs/models/mstrx.gateau and study 05.

Not a real design. Written to exercise route, merge, indexed carriers and epoch state.
"""
from gateau import Buffer, Burst, Design, Epoch, MergeInput

OUTSIDE = ("PHY", "PM")
SWAP = "first MTP boundary after ACT"


def build() -> Design:
    d = Design("mstrx", params=dict(P_LANES=4, P_SPL=2, N_STR=4), axes=dict(l=4, s=2, sid=4, ppc=2, rgb=3))
    d.domains += ["lnk_clk", "sdp_clk", "vid_clk", "sys_clk"]
    d.modes += ["training", "normal"]

    # carriers
    d.carrier("msg", "16-bit message", "lnk_clk", ring=True)
    d.carrier("sym", "one symbol group per lnk_clk", "lnk_clk")
    d.carrier("ssym", "one symbol group, this stream's slots (sparse)", "lnk_clk", index="sid")
    d.carrier("str", "one stream symbol group (dense, elastic)", "lnk_clk", index="sid")
    d.carrier("sdpk", "SDP packet of one stream", "sdp_clk", index="sid")
    d.carrier("sdpb", "32-bit SDP beat", "sdp_clk", parent="sdpk", index="sid")
    d.carrier("sdpo", "SDP packet, all streams", "sdp_clk")
    d.carrier("sdpob", "32-bit SDP beat", "sdp_clk", parent="sdpo")
    d.carrier("pix", "P_PPC pixels", "vid_clk[sid]", index="sid")

    # fields
    d.group("sym", "lnk", ["k"], 1, ("l", "s"))
    d.group("sym", "lnk", ["dat"], 8, ("l", "s"))
    d.group("sym", "lnk", ["lock"], 1)
    d.field("sym", "slot", 6, ("s",))
    d.group("ssym", "lnk", ["k"], 1, ("l", "s"))
    d.group("ssym", "lnk", ["dat"], 8, ("l", "s"))
    d.field("ssym", "v", 1, ("s",))
    d.field("str", "k", 1, ("l", "s"))
    d.field("str", "dat", 8, ("l", "s"))
    d.field("sdpk", "len", 6, availability="tail")
    d.field("sdpb", "dat", 32)
    d.field("sdpo", "sid", 2)
    d.field("sdpo", "len", 6, availability="tail")
    d.field("sdpob", "dat", 32)
    d.field("pix", "data", 8, ("ppc", "rgb"))

    # state
    d.state("cfg", "out-of-flow", fields=["lanes", "bpc"])
    d.state("vcpt", "out-of-flow", epoch=Epoch(SWAP))
    d.state("mtp", "in-flow", cyclic=64)

    # boundaries
    d.boundary("b0", coupling="rigid")
    d.boundary("b1", after="b0", latency=1, coupling="rigid")
    d.boundary("b2", after="b1", latency=1, coupling="rigid")
    d.boundary("b3", coupling="elastic")

    # stages and routes, in flow order
    d.stage("LINK", "sym", writes=["k", "dat", "lock"], state_reads=["cfg"], note="= study 04, collapsed")
    d.stage("FRAME", "sym", between=("b0", "b1"), reads=["k", "dat"], creates=["slot"],
            state_writes=["mtp", "vcpt"], note="detects ACT; swaps the vcpt epoch")
    d.route("ROUTE", "sym", "ssym", selector="vcpt.active[slot]", selector_field="sym.slot",
            domain=64, mapped=60, default="discard", granularity="axis s", between=("b1", "b2"),
            creates=["ssym.v"], consumes=["sym.slot"], state_reads=["vcpt"])
    d.routes["ROUTE"].state_reads[0].switch = SWAP
    d.stage("PACK", "ssym", out="str", between=("b2", "b3"), replicate="sid",
            reads=["v", "k", "dat"], creates=["k", "dat"],
            buffer=Buffer(depth=64, unit="slot", burst=Burst(items=24, in_rate=2, out_rate=0.75)),
            note="burst: stream A's 24 slots, two per cycle, drained at 24 per 32 cycles")
    d.stage("STRM", "str", out="sdpk", replicate="sid", reads=["k", "dat"],
            creates=["len", "sdpb.dat", "pix.data"], state_reads=["cfg"],
            emits=[("msg")], note="= study 04 PARS · MSA · SDP · VID")

    # merges
    d.merge("SDPM", [MergeInput("STRM", replicate="sid")], "sdpo", "round-robin", "sdpk", creates=["sdpo.sid"])
    d.merge("MSGM", [MergeInput("STRM", replicate="sid", msg_id="MSA")], "msg", "ring order", "msg")

    # feedback
    d.fb("flow", "SDPM", "STRM", note="grant: one stream at a time")
    d.fb("ctrl", "STRM", "PM", note="per-stream vblank irq")
    d.fb("ctrl", "PM", "FRAME", note="vcpt shadow via msg (ALLOCATE_PAYLOAD)")
    return d
