"""The studies are the acceptance tests: each model must reproduce exactly the findings its study drew."""
import importlib.util
from pathlib import Path

import pytest

from gateau import run_all

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def load(name):
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def findings(name):
    mod = load(name)
    return run_all(mod.build(), mod.OUTSIDE)


def table(fs):
    return {(f.check, f.subject, f.status) for f in fs}


def test_dprx_reproduces_study_04():
    fs = findings("dprx")
    assert table(fs) == {
        ("state use", "cfg.scrm_en", "fail"),                      # D6: scrambler enable never read
        ("requires", "PARS requires ila", "pass"),                 # D3/D4: lanes aligned before PARS reads lane 0
        ("join", "lat(PARS, SCRM)", "pass"),                       # D1: both b0 → b1
        ("join", "fifo(SDP)", "unchecked"),                        # D1: SDP data ↔ length, in order
        ("rigid edge", "SDP", "unchecked"),
        ("rigid edge", "VID", "unchecked"),                        # D1: 64 words vs vid_clk ratio ?
        ("cost", "TAGB copies along l", "info"),
    }
    by = {(f.check, f.subject): f.message for f in fs}
    assert "structural: every branch spans b0 → b1" in by[("join", "lat(PARS, SCRM)")]
    assert "comments at pars.sv:1394" in by[("join", "lat(PARS, SCRM)")]
    assert by[("cost", "TAGB copies along l")] == "48 b carried, 12 b distinct (36 b are copies)"


def test_mstrx_reproduces_study_05():
    fs = findings("mstrx")
    assert table(fs) == {
        ("rigid edge", "PACK", "pass"),                            # M7: peak 15 slots ≤ 64
        ("cost", "ROUTE → ssym", "info"),                          # M3: 288 b, ≤ 72 valid
        ("route coverage", "ROUTE", "pass"),                       # M9: all 64 slots have a destination
        ("route granularity", "ROUTE", "pass"),                    # M4: must split along s
        ("merge identity", "SDPM", "pass"),
        ("merge atomicity", "SDPM", "pass"),
        ("merge identity", "MSGM", "fail"),                        # M9: same message ID, no sid
        ("merge atomicity", "MSGM", "pass"),
        ("epoch", "vcpt", "pass"),                                 # M6: one reader, one swap point
    }
    by = {(f.check, f.subject): f.message for f in fs}
    assert by[("rigid edge", "PACK")] == "peak 15 slots vs depth 64"
    assert by[("cost", "ROUTE → ssym")] == "288 b per item across 4 copies, at most 72 b valid"
    assert by[("route coverage", "ROUTE")] == "60 of 64 mapped; the other 4 go to discard"


@pytest.mark.parametrize("name", ["dprx", "mstrx"])
def test_cli_exit_code_reports_failures(name, capsys):
    from gateau.__main__ import main
    assert main(["gateau", str(EXAMPLES / f"{name}.py")]) == 1     # both studies contain one failing check
    assert "findings" in capsys.readouterr().out
