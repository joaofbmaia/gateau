"""Rocket's integer pipeline (chipsalliance/rocket-chip, RocketCore.scala), as in study 02.

FPU, RoCC, vector and PTW omitted. Default parameters: fastLoadWord = true, fastLoadByte = false.
Hazard coverage per producer class is the table study 02 derived from bypass_sources,
ex_cannot_bypass / mem_cannot_bypass and the scoreboard.
"""
from gateau import Design

OUTSIDE = ()


def build() -> Design:
    d = Design("rocket", axes=dict(src=2))
    d.domains += ["clk"]

    d.carrier("inst", "one instruction", "clk")
    d.carrier("dmem", "one data-cache access", "clk")

    d.field("inst", "valid", 1)
    d.field("inst", "pc", 40)
    d.field("inst", "inst", 32)
    d.field("inst", "ctrl", None, group="ctrl")          # IntCtrlSigs: width not modelled
    d.field("inst", "rs", 64, ("src",))
    d.field("inst", "wdata", 64)
    d.field("inst", "xcpt", 1)
    d.field("inst", "cause", 64)
    d.field("inst", "btb", None)                         # BTBResp: width not modelled
    d.field("dmem", "addr", 40)
    d.field("dmem", "data", 64)

    d.state("rf", "in-flow", coverage={
        "ALU op":              {1: "bypass mem_reg_wdata", 2: "bypass wb_reg_wdata", 3: "RF write-through"},
        "load word/double":    {1: "stall (load-use)", 2: "bypass D$ s2 data", 3: "RF write-through"},
        "load byte/half":      {1: "stall", 2: "stall (slow bypass)", 3: "RF write-through"},
        "mul, CSR, jalr":      {1: "stall", 2: "stall", 3: "RF write-through"},
        "div, D$ miss, RoCC":  {"*": "scoreboard until ll_wen"},
    })
    d.state("sboard", "in-flow", coverage={"*": "itself (it is the interlock)"})

    d.boundary("bID", coupling="elastic")                # ibuf
    d.boundary("bEX", after="bID", latency=1, coupling="lockstep")
    d.boundary("bMEM", after="bEX", latency=1, coupling="lockstep")
    d.boundary("bWB", after="bMEM", latency=1, coupling="lockstep")
    d.boundary("bRET", after="bWB", latency=1, coupling="lockstep")

    d.stage("Frontend", "inst", creates=["valid", "pc", "inst", "btb", "xcpt"], note="F1 · F2 · I$ · BTB")
    d.stage("ID", "inst", between=("bID", "bEX"), reads=["inst"], creates=["ctrl", "rs"],
            writes=["xcpt"], state_reads=["rf", "sboard"])
    d.stage("EX", "inst", between=("bEX", "bMEM"), reads=["pc", "ctrl", "rs"], creates=["wdata"])
    d.stage("DC0", "inst", out="dmem", between=("bEX", "bMEM"), reads=["rs"], creates=["addr"])
    d.stage("MEM", "inst", between=("bMEM", "bWB"), reads=["pc", "ctrl"], consumes=["btb"],
            writes=["wdata", "xcpt"])
    d.stage("DC1", "dmem", between=("bMEM", "bWB"), reads=["inst.rs"])
    d.stage("DC2", "dmem", between=("bWB", "bRET"), creates=["data"])
    d.stage("WB", "inst", between=("bWB", "bRET"), consumes=["wdata", "xcpt", "cause", "ctrl"],
            state_writes=["rf", "sboard"])

    d.join("dcache-rejoins-wb", "lat", ["WB", "DC2"], evidence="s2 response used in the WB mux")

    d.fb("data", "MEM", "EX", distance=1, note="mem_reg_wdata")
    d.fb("data", "WB", "EX", distance=2, note="wb_reg_wdata")
    d.fb("data", "DC2", "EX", distance=2, note="dcache_bypass_data")
    d.fb("ctrl", "MEM", "Frontend", note="mispredict → npc (take_pc_mem)")
    d.fb("ctrl", "WB", "Frontend", note="replay · trap · eret (take_pc_wb)")
    return d
