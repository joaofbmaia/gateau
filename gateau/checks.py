"""Validation and the derived checks of gateau notation v1.2.

`validate` raises ModelError for references that don't resolve. Everything else is a
`Finding`: each check looks at the model and says pass, fail, unchecked (the model
doesn't hold enough information to decide) or info (cost figures).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .model import Design, ModelError, Stage

Status = Literal["pass", "fail", "unchecked", "info"]


@dataclass(frozen=True)
class Finding:
    check: str
    subject: str
    status: Status
    message: str


# ── validation ────────────────────────────────────────────────────────────

def validate(d: Design, outside: tuple[str, ...] = ()) -> None:
    """Raise ModelError if anything in the model refers to something undeclared."""
    def need(cond, what):
        if not cond:
            raise ModelError(what)

    for c in d.carriers.values():
        need(c.domain in d.domains or c.domain.split("[")[0] in d.domains, f"carrier {c.name}: unknown domain {c.domain}")
        need(c.parent is None or c.parent in d.carriers, f"carrier {c.name}: unknown parent {c.parent}")
        need(c.index is None or c.index in d.axes, f"carrier {c.name}: unknown index axis {c.index}")
    for f in d.fields.values():
        need(f.carrier in d.carriers, f"field {f.path}: unknown carrier")
        for a in f.axes:
            need(a in d.axes, f"field {f.path}: unknown axis {a}")
    for b in d.boundaries.values():
        need(b.after is None or b.after in d.boundaries, f"boundary {b.name}: unknown base {b.after}")
    for s in d.stages.values():
        need(s.on in d.carriers, f"stage {s.name}: unknown carrier {s.on}")
        need(s.out is None or s.out in d.carriers, f"stage {s.name}: unknown output carrier {s.out}")
        if s.between:
            for b in s.between:
                need(b in d.boundaries, f"stage {s.name}: unknown boundary {b}")
        for ref in s.reads + s.reads_at_head + s.writes + s.consumes:
            d.resolve(ref, s.on)
        for ref in s.creates:
            d.resolve(ref, s.out or s.on)
        for t in s.state_reads + s.state_writes + s.requires:
            need(t.state in d.states, f"stage {s.name}: unknown state {t.state}")
            st = d.states[t.state]
            need(t.sub is None or t.sub in st.fields, f"stage {s.name}: unknown field {t.state}.{t.sub}")
        for e in s.emits:
            need(e.carrier in d.carriers, f"stage {s.name}: emits to unknown carrier {e.carrier}")
        need(s.replicate is None or s.replicate in d.axes, f"stage {s.name}: unknown axis {s.replicate}")
        need(s.modes is None or s.modes <= set(d.modes), f"stage {s.name}: unknown mode in {s.modes}")
    for j in d.joins:
        for b in j.branches:
            need(b in d.stages, f"join {j.name}: unknown stage {b}")
    known = set(d.stages) | set(d.routes) | set(d.merges) | set(outside)
    for f in d.feedback:
        for end in (f.src, f.dst):
            need(end.split(".")[0] in known, f"feedback {f.src} → {f.dst}: unknown end {end}")
    for r in d.routes.values():
        need(r.src in d.carriers and r.dst in d.carriers, f"route {r.name}: unknown carrier")
        need(d.carriers[r.dst].index is not None, f"route {r.name}: destination {r.dst} is not an indexed carrier")
        for t in r.state_reads:
            need(t.state in d.states, f"route {r.name}: unknown state {t.state}")
    for m in d.merges.values():
        need(m.dst in d.carriers, f"merge {m.name}: unknown carrier {m.dst}")
        need(m.granularity in d.carriers, f"merge {m.name}: granularity must name a carrier")


# ── helpers ───────────────────────────────────────────────────────────────

def _latency(d: Design, start: str, end: str) -> Optional[int]:
    """Cycles from boundary `start` to boundary `end`, following `after` links back from `end`."""
    total, cur = 0, end
    while cur != start:
        b = d.boundaries[cur]
        if b.after is None or not isinstance(b.latency, int):
            return None
        total += b.latency
        cur = b.after
    return total


def _state_readers(d: Design, state: str):
    for s in d.stages.values():
        for t in s.state_reads + s.requires:
            if t.state == state:
                yield s.name, t
    for r in d.routes.values():
        for t in r.state_reads:
            if t.state == state:
                yield r.name, t


def _stage_index(d: Design, name: str) -> int:
    return d.order.index(name)


def _distance(d: Design, reader: Stage, writer: Stage) -> int:
    """Pipeline distance from a reading stage to a writing stage: by boundary latency when both
    are placed between boundaries, otherwise by flow order."""
    if reader.between and writer.between:
        lat = _latency(d, reader.between[0], writer.between[0])
        if lat is not None:
            return lat
    return _stage_index(d, writer.name) - _stage_index(d, reader.name)


# ── lint: state that is written but never read; requirements met ─────────

def check_state_use(d: Design) -> list[Finding]:
    out = []
    for st in d.states.values():
        if not st.fields:
            continue
        read_all = any(t.sub is None for _, t in _state_readers(d, st.name))
        read = {t.sub for _, t in _state_readers(d, st.name) if t.sub}
        for sub in st.fields:
            if not read_all and sub not in read:
                out.append(Finding("state use", f"{st.name}.{sub}", "fail", "written, never read"))
    for s in d.stages.values():
        for t in s.requires:
            writers = [w.name for w in d.stages.values() for wt in w.state_writes if wt.state == t.state]
            earlier = [w for w in writers if _stage_index(d, w) < _stage_index(d, s.name)]
            if earlier:
                out.append(Finding("requires", f"{s.name} requires {t.state}", "pass",
                                   f"written by {', '.join(earlier)} before {s.name}"))
            else:
                out.append(Finding("requires", f"{s.name} requires {t.state}", "fail",
                                   "nothing upstream establishes it"))
    return out


# ── 1. joins ──────────────────────────────────────────────────────────────

def check_joins(d: Design) -> list[Finding]:
    out = []
    for j in d.joins:
        subj = f"{j.kind}({', '.join(j.branches)})"
        ev = f"; RTL evidence: {j.evidence}" if j.evidence else ""
        if j.kind == "lat":
            spans = [d.stages[b].between for b in j.branches]
            if all(spans) and len(set(spans)) == 1:
                a, b = spans[0]
                out.append(Finding("join", subj, "pass", f"structural: every branch spans {a} → {b}{ev}"))
                continue
            lats = [_latency(d, *sp) if sp else None for sp in spans]
            if None in lats:
                out.append(Finding("join", subj, "unchecked", "a branch has no declared latency"))
            elif len(set(lats)) == 1:
                out.append(Finding("join", subj, "pass", f"every branch takes {lats[0]} cycles{ev}"))
            else:
                detail = ", ".join(f"{b} {l}" for b, l in zip(j.branches, lats))
                out.append(Finding("join", subj, "fail", f"branch latencies differ: {detail}"))
        elif j.kind == "fifo":
            if j.depth is not None and j.in_flight is not None:
                ok = j.depth >= j.in_flight + 1
                out.append(Finding("join", subj, "pass" if ok else "fail",
                                   f"depth {j.depth} vs other path latency {j.in_flight} + 1"))
            else:
                out.append(Finding("join", subj, "unchecked", "in-order pairing declared; depth vs latency not in the model"))
        else:  # key
            if j.key_bits is not None and j.in_flight is not None:
                ok = 2 ** j.key_bits >= j.in_flight
                out.append(Finding("join", subj, "pass" if ok else "fail",
                                   f"{2 ** j.key_bits} keys for {j.in_flight} items in flight"))
            else:
                out.append(Finding("join", subj, "unchecked", f"key {j.key}: in-flight count not in the model"))
    return out


# ── 2. hazard windows ─────────────────────────────────────────────────────

def check_hazards(d: Design) -> list[Finding]:
    out = []
    for st in d.states.values():
        if st.writer != "in-flow":
            continue
        readers = [d.stages[n] for n, _ in _state_readers(d, st.name) if n in d.stages]
        writers = [s for s in d.stages.values() if any(t.state == st.name for t in s.state_writes)]
        pairs = [(r, w) for r in readers for w in writers if _stage_index(d, w.name) > _stage_index(d, r.name)]
        if not pairs:
            continue
        window = max(_distance(d, r, w) for r, w in pairs)
        by_class = st.coverage if st.coverage and all(isinstance(v, dict) for v in st.coverage.values()) \
            else {None: dict(st.coverage)}
        for cls, cov in by_class.items():
            covered = dict(cov)
            if cls is None:      # unclassified: bypass feedback edges count directly
                for fbk in d.feedback:
                    if fbk.kind == "data" and fbk.distance is not None:
                        covered.setdefault(fbk.distance, f"bypass from {fbk.src}")
            subject = st.name if cls is None else f"{st.name} ← {cls}"
            if "*" in covered:
                out.append(Finding("hazard", subject, "pass", f"window {window}: every distance by {covered['*']}"))
                continue
            missing = [k for k in range(1, window + 1) if k not in covered]
            if missing:
                out.append(Finding("hazard", subject, "fail",
                                   f"window {window}; distances {missing} have no bypass, stall or scoreboard"))
            else:
                how = "; ".join(f"d={k}: {covered[k]}" for k in range(1, window + 1))
                out.append(Finding("hazard", subject, "pass", f"window {window} covered ({how})"))
    return out


# ── 3. availability ───────────────────────────────────────────────────────

def check_availability(d: Design) -> list[Finding]:
    out = []
    for s in d.stages.values():
        for ref in s.reads_at_head:
            for f in d.resolve(ref, s.on):
                if f.availability != "tail":
                    continue
                item = f"{f.carrier} item"
                upstream = [u for u in d.stages.values()
                            if _stage_index(d, u.name) <= _stage_index(d, s.name)
                            and u.buffer and u.buffer.policy == "prebuffer"]
                buf = upstream[-1].buffer if upstream else None
                if buf and buf.item_max is not None and buf.depth is not None and buf.item_max > buf.depth:
                    out.append(Finding("availability", f.path, "fail",
                                       f"tail field needed at head by {s.name}; {upstream[-1].name} holds "
                                       f"{buf.depth} {buf.unit}s but a {item} can be {buf.item_max}"))
                elif upstream:
                    size = f" ({buf.depth} {buf.unit}s ≥ {buf.item_max})" if buf.item_max is not None else ""
                    out.append(Finding("availability", f.path, "pass",
                                       f"tail field needed at head by {s.name}; {upstream[-1].name} holds a whole {item}{size}"))
                else:
                    out.append(Finding("availability", f.path, "fail",
                                       f"tail field needed at head by {s.name}; needs a buffer of one whole {item}"))
    return out


# ── 4. rigid edges ────────────────────────────────────────────────────────

def check_rigid_edges(d: Design) -> list[Finding]:
    out = []
    for s in d.stages.values():
        if not s.between:
            continue
        a, b = (d.boundaries[x] for x in s.between)
        into_rigid = a.coupling != "rigid" and b.coupling == "rigid"
        if not (a.coupling == "rigid" and b.coupling != "rigid") and not into_rigid:
            continue
        buf = s.buffer
        if into_rigid:
            if buf is None or buf.policy != "prebuffer":
                out.append(Finding("rigid edge", s.name, "fail",
                                   "stallable input feeds a region that cannot pause, with no whole-item prebuffer"))
            elif buf.item_max is not None and buf.depth is not None:
                ok = buf.depth >= buf.item_max
                out.append(Finding("rigid edge", s.name, "pass" if ok else "fail",
                                   f"prebuffers a whole item: depth {buf.depth} vs largest item {buf.item_max} {buf.unit}s"))
            else:
                out.append(Finding("rigid edge", s.name, "unchecked", "prebuffer declared; item size not in the model"))
            continue
        if buf is not None and buf.policy == "drop" and buf.item_max is not None and buf.depth is not None:
            ok = buf.depth >= buf.item_max
            out.append(Finding("rigid edge", s.name, "pass" if ok else "fail",
                               f"drops on overflow; holds a whole item: depth {buf.depth} vs largest item {buf.item_max} {buf.unit}s"))
        elif buf is None or buf.depth is None:
            out.append(Finding("rigid edge", s.name, "fail", "rigid input meets a stallable output with no buffer"))
        elif buf.burst is None:
            out.append(Finding("rigid edge", s.name, "unchecked",
                               f"buffer {buf.depth} {buf.unit}s; arrival pattern not in the model"))
        else:
            peak = buf.burst.peak
            ok = peak <= buf.depth
            out.append(Finding("rigid edge", s.name, "pass" if ok else "fail",
                               f"peak {peak:g} {buf.unit}s vs depth {buf.depth}"))
    return out


# ── 5. cost ───────────────────────────────────────────────────────────────

def check_cost(d: Design) -> list[Finding]:
    out = []
    for s in d.stages.values():
        if not s.broadcast:
            continue
        refs, axis = s.broadcast
        fs = [f for r in refs for f in d.resolve(r, s.on)]
        if any(d.bits(f) is None for f in fs):
            out.append(Finding("cost", f"{s.name} copies along {axis}", "unchecked", "a field width is not modelled"))
            continue
        carried = sum(d.bits(f) for f in fs) * d.copies(s.on)
        distinct = carried // d.axes[axis]
        out.append(Finding("cost", f"{s.name} copies along {axis}", "info",
                           f"{carried} b carried, {distinct} b distinct ({carried - distinct} b are copies)"))
    for r in d.routes.values():
        src_names = {f.name: f for f in d.carrier_fields(r.src)}
        data = [f for f in d.carrier_fields(r.dst) if f.name in src_names]
        per_copy = sum(d.bits(f) or 0 for f in data)
        k = d.copies(r.dst)
        out.append(Finding("cost", f"{r.name} → {r.dst}", "info",
                           f"{per_copy * k} b per item across {k} copies, at most {per_copy} b valid"))
    return out


# ── 6. route coverage and granularity ─────────────────────────────────────

def check_routes(d: Design) -> list[Finding]:
    out = []
    for r in d.routes.values():
        if r.domain is None or r.mapped is None:
            out.append(Finding("route coverage", r.name, "unchecked", "selector domain not in the model"))
        elif r.mapped >= r.domain:
            out.append(Finding("route coverage", r.name, "pass", f"all {r.domain} selector values mapped"))
        elif r.default:
            out.append(Finding("route coverage", r.name, "pass",
                               f"{r.mapped} of {r.domain} mapped; the other {r.domain - r.mapped} go to {r.default}"))
        else:
            out.append(Finding("route coverage", r.name, "fail",
                               f"{r.domain - r.mapped} of {r.domain} selector values have no destination"))
        if r.selector_field:
            f = d.resolve(r.selector_field)[0]
            if f.axes and r.granularity == "item":
                out.append(Finding("route granularity", r.name, "fail",
                                   f"selector varies along {', '.join(f.axes)} inside one item; routing whole items is wrong"))
            elif r.granularity.startswith("axis ") and r.granularity.split()[1] not in f.axes:
                out.append(Finding("route granularity", r.name, "fail",
                                   f"routes along {r.granularity.split()[1]} but the selector has axes {f.axes}"))
            else:
                out.append(Finding("route granularity", r.name, "pass", f"granularity {r.granularity} matches the selector"))
    return out


# ── 7. merge identity and atomicity ───────────────────────────────────────

def check_merges(d: Design) -> list[Finding]:
    out = []
    for m in d.merges.values():
        n_sources = sum(d.axes[i.replicate] if i.replicate else 1 for i in m.inputs)
        ids = [i.msg_id for i in m.inputs for _ in range(d.axes[i.replicate] if i.replicate else 1)]
        if m.creates:
            out.append(Finding("merge identity", m.name, "pass", f"creates {', '.join(m.creates)}"))
        elif None not in ids and len(set(ids)) == n_sources:
            out.append(Finding("merge identity", m.name, "pass", "every source carries a distinct id"))
        else:
            same = f"same id {ids[0]!r} from" if ids and len(set(ids)) == 1 and ids[0] else "no distinguishing field on"
            out.append(Finding("merge identity", m.name, "fail",
                               f"{same} {n_sources} sources and nothing created; origins are lost"))
        children = [c.name for c in d.carriers.values() if c.parent == m.granularity]
        parent = d.carriers[m.granularity].parent
        if parent:
            out.append(Finding("merge atomicity", m.name, "fail",
                               f"merges at {m.granularity}, inside {parent}: items of {parent} can interleave"))
        else:
            inner = f" (never splits {', '.join(children)})" if children else ""
            out.append(Finding("merge atomicity", m.name, "pass", f"merges whole {m.granularity} items{inner}"))
    return out


# ── 8. epochs ─────────────────────────────────────────────────────────────

def check_epochs(d: Design) -> list[Finding]:
    out = []
    for st in d.states.values():
        if not st.epoch:
            continue
        readers = list(_state_readers(d, st.name))
        bad = [(n, t.switch) for n, t in readers if t.switch and t.switch != st.epoch.swap_point]
        unknown = [n for n, t in readers if not t.switch]
        if bad:
            detail = ", ".join(f"{n} switches at {sw}" for n, sw in bad)
            out.append(Finding("epoch", st.name, "fail", f"declared swap point {st.epoch.swap_point}; {detail}"))
        elif unknown:
            out.append(Finding("epoch", st.name, "unchecked", f"switch point not declared for {', '.join(unknown)}"))
        else:
            out.append(Finding("epoch", st.name, "pass",
                               f"{len(readers)} reader(s), all switch at {st.epoch.swap_point}"))
    return out


ALL_CHECKS = (check_state_use, check_joins, check_hazards, check_availability, check_rigid_edges,
              check_cost, check_routes, check_merges, check_epochs)


def run_all(d: Design, outside: tuple[str, ...] = ()) -> list[Finding]:
    validate(d, outside)
    return [f for check in ALL_CHECKS for f in check(d)]


MARK = {"pass": "✓", "fail": "✗", "unchecked": "?", "info": "·"}


def report(findings: list[Finding]) -> str:
    w = max((len(f.check) for f in findings), default=5)
    s = max((len(f.subject) for f in findings), default=7)
    return "\n".join(f"{MARK[f.status]} {f.check:<{w}}  {f.subject:<{s}}  {f.message}" for f in findings)
