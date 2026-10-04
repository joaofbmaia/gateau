"""Each check must be able to fail. Small models, one per check, each with a passing and a failing variant."""
import pytest

from gateau import Buffer, Burst, Design, Epoch, MergeInput, ModelError, validate
from gateau.checks import (check_availability, check_epochs, check_hazards, check_joins, check_merges,
                           check_rigid_edges, check_routes, check_state_use)


def statuses(fs, check=None):
    return [f.status for f in fs if check is None or f.check == check]


# ── joins ─────────────────────────────────────────────────────────────────

def fork_join(scrm_out):
    d = Design("j", axes={"l": 4})
    d.domains.append("clk")
    d.carrier("sym", "symbols", "clk")
    d.field("sym", "dat", 8, ("l",))
    d.boundary("b0")
    d.boundary("b1", after="b0", latency=1)
    d.boundary("b2", after="b1", latency=1)
    d.stage("PARS", "sym", between=("b0", "b1"), reads=["dat"])
    d.stage("SCRM", "sym", between=("b0", scrm_out), writes=["dat"])
    d.join("j", "lat", ["PARS", "SCRM"])
    return d


def test_lat_join_structural_pass():
    assert statuses(check_joins(fork_join("b1"))) == ["pass"]


def test_lat_join_fails_when_one_branch_gains_a_register():
    fs = check_joins(fork_join("b2"))
    assert statuses(fs) == ["fail"]
    assert "PARS 1, SCRM 2" in fs[0].message


def test_key_join_needs_enough_keys():
    d = fork_join("b1")
    d.joins[0].kind, d.joins[0].key_bits = "key", 2
    d.joins[0].in_flight = 5
    assert statuses(check_joins(d)) == ["fail"]
    d.joins[0].in_flight = 4
    assert statuses(check_joins(d)) == ["pass"]


# ── hazard windows (a Rocket-like integer pipeline) ──────────────────────

def rocket(bypasses):
    d = Design("rocket")
    d.domains.append("clk")
    d.carrier("inst", "instruction", "clk")
    d.field("inst", "wdata", 64)
    d.state("rf", "in-flow", coverage={3: "RF write-through"})
    d.stage("ID", "inst", state_reads=["rf"])          # RF read
    d.stage("EX", "inst")
    d.stage("MEM", "inst")
    d.stage("WB", "inst", state_writes=["rf"])         # RF write: window of 3
    for dist, src in bypasses:
        d.fb("data", src, "EX", distance=dist)
    return d


def test_hazard_window_covered():
    fs = check_hazards(rocket([(1, "MEM"), (2, "WB")]))
    assert statuses(fs) == ["pass"]
    assert "window 3" in fs[0].message


def test_hazard_window_gap_fails():
    fs = check_hazards(rocket([(1, "MEM")]))
    assert statuses(fs) == ["fail"]
    assert "[2]" in fs[0].message


# ── availability (UDP checksum on transmit) ──────────────────────────────

def udp_tx(prebuffer):
    d = Design("udp")
    d.domains.append("clk")
    d.carrier("pkt", "packet", "clk")
    d.field("pkt", "csum", 16, availability="tail")
    d.stage("CSUM", "pkt", creates=["csum"],
            buffer=Buffer(depth=2048, unit="beat", policy="prebuffer") if prebuffer else None)
    d.stage("UDP_TX", "pkt", reads_at_head=["csum"])
    return d


def test_tail_field_needed_at_head_requires_a_buffer():
    assert statuses(check_availability(udp_tx(False))) == ["fail"]
    assert statuses(check_availability(udp_tx(True))) == ["pass"]


# ── rigid edges ───────────────────────────────────────────────────────────

def edge(buffer):
    d = Design("e")
    d.domains.append("clk")
    d.carrier("c", "item", "clk")
    d.boundary("r", coupling="rigid")
    d.boundary("e", coupling="elastic")
    d.stage("FIFO", "c", between=("r", "e"), buffer=buffer)
    return d


@pytest.mark.parametrize("buffer, status", [
    (None, "fail"),
    (Buffer(depth=8), "unchecked"),
    (Buffer(depth=8, burst=Burst(items=24, in_rate=2, out_rate=0.75)), "fail"),     # peak 15 > 8
    (Buffer(depth=16, burst=Burst(items=24, in_rate=2, out_rate=0.75)), "pass"),
])
def test_rigid_edge(buffer, status):
    assert statuses(check_rigid_edges(edge(buffer))) == [status]


# ── routes ────────────────────────────────────────────────────────────────

def router(granularity="axis s", mapped=60, default="discard"):
    d = Design("r", axes={"s": 2, "sid": 4})
    d.domains.append("clk")
    d.carrier("sym", "group", "clk")
    d.carrier("ssym", "group", "clk", index="sid")
    d.field("sym", "slot", 6, ("s",))
    d.route("R", "sym", "ssym", selector="t[slot]", selector_field="sym.slot",
            domain=64, mapped=mapped, default=default, granularity=granularity)
    return d


def test_route_granularity_must_follow_the_selector():
    assert statuses(check_routes(router()), "route granularity") == ["pass"]
    assert statuses(check_routes(router(granularity="item")), "route granularity") == ["fail"]


def test_route_coverage_needs_a_default_for_unmapped_values():
    assert statuses(check_routes(router()), "route coverage") == ["pass"]
    assert statuses(check_routes(router(default=None)), "route coverage") == ["fail"]
    assert statuses(check_routes(router(mapped=64, default=None)), "route coverage") == ["pass"]


def test_route_destination_must_be_indexed():
    d = router()
    d.carriers["ssym"].index = None
    with pytest.raises(ModelError):
        validate(d)


# ── merges ────────────────────────────────────────────────────────────────

def merger(creates=(), msg_id=None, granularity="pkt"):
    d = Design("m", axes={"sid": 4})
    d.domains.append("clk")
    d.carrier("pkt", "packet", "clk")
    d.carrier("beat", "beat", "clk", parent="pkt")
    d.merge("M", [MergeInput("SRC", replicate="sid", msg_id=msg_id)], "pkt", "round-robin", granularity,
            creates=creates)
    return d


def test_merge_identity():
    assert statuses(check_merges(merger(msg_id="MSA")), "merge identity") == ["fail"]
    assert statuses(check_merges(merger(creates=["pkt.sid"])), "merge identity") == ["pass"]


def test_merge_at_beat_granularity_can_interleave_packets():
    assert statuses(check_merges(merger(granularity="pkt")), "merge atomicity") == ["pass"]
    assert statuses(check_merges(merger(granularity="beat")), "merge atomicity") == ["fail"]


# ── epochs ────────────────────────────────────────────────────────────────

def epoch(second_reader_switch=None, second=False):
    d = Design("ep")
    d.domains.append("clk")
    d.carrier("c", "item", "clk")
    d.state("vcpt", "out-of-flow", epoch=Epoch("mtp boundary"))
    d.stage("ROUTE", "c", state_reads=["vcpt"])
    d.stages["ROUTE"].state_reads[0].switch = "mtp boundary"
    if second:
        d.stage("PACK", "c", state_reads=["vcpt"])
        d.stages["PACK"].state_reads[0].switch = second_reader_switch
    return d


def test_epoch_one_reader_passes():
    assert statuses(check_epochs(epoch())) == ["pass"]


def test_epoch_reader_switching_on_detect_fails():
    fs = check_epochs(epoch("on ACT detect", second=True))
    assert statuses(fs) == ["fail"]
    assert "PACK switches at on ACT detect" in fs[0].message


def test_epoch_reader_without_declared_switch_is_unchecked():
    assert statuses(check_epochs(epoch(None, second=True))) == ["unchecked"]


# ── state use and validation ─────────────────────────────────────────────

def test_unread_config_field_is_flagged():
    d = Design("s")
    d.domains.append("clk")
    d.carrier("c", "item", "clk")
    d.state("cfg", "out-of-flow", fields=["a", "b"])
    d.stage("X", "c", state_reads=["cfg.a"])
    assert [(f.subject, f.status) for f in check_state_use(d)] == [("cfg.b", "fail")]


@pytest.mark.parametrize("mutate", [
    lambda d: d.stage("Y", "c", reads=["nope"]),
    lambda d: d.stage("Y", "c", state_reads=["cfg.nope"]),
    lambda d: d.stage("Y", "nowhere"),
    lambda d: d.stage("Y", "c", between=("b0", "b9")),
])
def test_validate_rejects_undeclared_references(mutate):
    d = Design("v")
    d.domains.append("clk")
    d.carrier("c", "item", "clk")
    d.state("cfg", "out-of-flow", fields=["a"])
    d.boundary("b0")
    mutate(d)
    with pytest.raises(ModelError):
        validate(d)
