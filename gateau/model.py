"""The gateau model: eight primitives and their attributes (notation v1.2).

A design is built with the methods on `Design`; every method returns the object it
creates, so models read top to bottom like the .gateau sketches in docs/models/.
Nothing here draws or checks anything; see checks.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import prod
from typing import Literal, Optional, Union

Coupling = Literal["rigid", "elastic", "lockstep"]
Availability = Literal["whole", "head", "tail"]
FeedbackKind = Literal["data", "ctrl", "flow"]
StateWriter = Literal["in-flow", "out-of-flow", "shared"]
JoinKind = Literal["lat", "fifo", "key"]
Latency = Union[int, Literal["variable"], None]      # None = unknown ("?")


class ModelError(ValueError):
    """Raised when a model refers to something it never declared."""


# ── 1. carriers and 2. fields ─────────────────────────────────────────────

@dataclass
class Carrier:
    name: str
    item: str
    domain: str
    parent: Optional[str] = None          # rates nest: a beat carrier inside a packet carrier
    index: Optional[str] = None           # indexed carrier: one copy per value of this axis
    ring: bool = False


@dataclass
class Field:
    carrier: str
    name: str
    elem_bits: Optional[int]              # None: width not modelled
    axes: tuple[str, ...] = ()
    availability: Availability = "whole"
    group: Optional[str] = None

    @property
    def path(self) -> str:
        return f"{self.carrier}.{self.name}"


# ── 4. boundaries ─────────────────────────────────────────────────────────

@dataclass
class Boundary:
    name: str
    after: Optional[str] = None           # b1 = b0 + 1  →  Boundary("b1", after="b0", latency=1)
    latency: Latency = None
    coupling: Coupling = "rigid"


# ── 6. state ──────────────────────────────────────────────────────────────

@dataclass
class Epoch:
    swap_point: str                       # e.g. "mtp-boundary-after-act"


@dataclass
class State:
    name: str
    writer: StateWriter
    fields: tuple[str, ...] = ()          # named sub-fields, for configuration registers
    cyclic: Optional[int] = None
    epoch: Optional[Epoch] = None
    # hazard coverage for in-flow state. Either distance → how it is covered, or, per producer
    # class, {class: {distance: how}}; the distance "*" covers every distance (a scoreboard).
    coverage: dict = field(default_factory=dict)


@dataclass
class StateTap:
    state: str
    sub: Optional[str] = None             # cfg.scrm_en → state="cfg", sub="scrm_en"
    switch: Optional[str] = None          # for epoch state: where this reader switches


def _tap(spec: str, switch: Optional[str] = None) -> StateTap:
    name, _, sub = spec.partition(".")
    return StateTap(name, sub or None, switch)


# ── buffers, used by the rigid-edge and availability checks ──────────────

@dataclass
class Burst:
    """Arrival pattern into a buffer: `items` arrive at `in_rate` per cycle, drained at `out_rate`."""
    items: float
    in_rate: float
    out_rate: float

    @property
    def peak(self) -> float:
        return self.items - self.out_rate * (self.items / self.in_rate)


@dataclass
class Buffer:
    depth: Optional[int] = None
    unit: str = "item"
    policy: Optional[Literal["drop", "prebuffer", "stall"]] = None
    burst: Optional[Burst] = None
    item_max: Optional[int] = None        # largest item the buffer must hold whole, in `unit`s


# ── 3. stages ─────────────────────────────────────────────────────────────

@dataclass
class Emit:
    carrier: str
    msg_id: Optional[str] = None          # identity the emitted items carry, if any


@dataclass
class Stage:
    name: str
    on: str                               # input carrier
    out: Optional[str] = None             # output carrier for a transfer stage (defaults to `on`)
    between: Optional[tuple[str, str]] = None
    reads: tuple[str, ...] = ()
    reads_at_head: tuple[str, ...] = ()   # fields needed when the item starts (availability check)
    writes: tuple[str, ...] = ()
    creates: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    broadcast: Optional[tuple[tuple[str, ...], str]] = None   # (fields, axis): copies along an axis
    state_reads: tuple[StateTap, ...] = ()
    state_writes: tuple[StateTap, ...] = ()
    requires: tuple[StateTap, ...] = ()
    replicate: Optional[str] = None       # ×ℓ, ×sid
    condition: Optional[str] = None       # exists only if this parameter is set
    modes: Optional[frozenset[str]] = None
    emits: tuple[Emit, ...] = ()
    buffer: Optional[Buffer] = None
    note: str = ""


# ── 5. forks and joins ────────────────────────────────────────────────────

@dataclass
class Join:
    name: str
    kind: JoinKind
    branches: tuple[str, ...]             # stage names, one per path
    depth: Optional[int] = None           # fifo
    key: Optional[str] = None             # key: field path
    key_bits: Optional[int] = None
    in_flight: Optional[int] = None
    evidence: str = ""                    # where the RTL states it (comment, assertion, …)


# ── 7. feedback ───────────────────────────────────────────────────────────

@dataclass
class Feedback:
    kind: FeedbackKind
    src: str
    dst: str
    modes: Optional[frozenset[str]] = None
    distance: Optional[int] = None        # for bypasses: the read-after-write distance covered
    note: str = ""


# ── 8. route and merge ────────────────────────────────────────────────────

@dataclass
class Route:
    name: str
    src: str                              # carrier
    dst: str                              # indexed carrier
    selector: str                         # field or state lookup that picks the destination
    selector_field: Optional[str] = None  # field the selector is a function of (granularity check)
    domain: Optional[int] = None          # how many selector values exist (e.g. 64 slots)
    mapped: Optional[int] = None          # how many of them map to a destination
    default: Optional[str] = None         # what happens to the rest ("discard", a carrier, …)
    granularity: str = "item"             # "item" or "axis <name>"
    between: Optional[tuple[str, str]] = None
    creates: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    state_reads: tuple[StateTap, ...] = ()


@dataclass
class MergeInput:
    source: str                           # stage or carrier feeding the merge
    replicate: Optional[str] = None       # one input per value of this axis
    msg_id: Optional[str] = None


@dataclass
class Merge:
    name: str
    inputs: tuple[MergeInput, ...]
    dst: str
    policy: str                           # "round-robin", "priority", "ring order", …
    granularity: str                      # carrier whose items are never split
    creates: tuple[str, ...] = ()


# ── the design ────────────────────────────────────────────────────────────

@dataclass
class Design:
    name: str
    params: dict[str, Union[int, bool]] = field(default_factory=dict)
    axes: dict[str, int] = field(default_factory=dict)
    domains: list[str] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    carriers: dict[str, Carrier] = field(default_factory=dict)
    fields: dict[str, Field] = field(default_factory=dict)
    states: dict[str, State] = field(default_factory=dict)
    boundaries: dict[str, Boundary] = field(default_factory=dict)
    stages: dict[str, Stage] = field(default_factory=dict)
    joins: list[Join] = field(default_factory=list)
    feedback: list[Feedback] = field(default_factory=list)
    routes: dict[str, Route] = field(default_factory=dict)
    merges: dict[str, Merge] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)    # stages, routes and merges in flow order

    # builders ------------------------------------------------------------
    def carrier(self, name, item, domain, **kw) -> Carrier:
        c = self.carriers[name] = Carrier(name, item, domain, **kw)
        return c

    def field(self, carrier, name, elem_bits, axes=(), **kw) -> Field:
        f = Field(carrier, name, elem_bits, tuple(axes), **kw)
        self.fields[f.path] = f
        return f

    def group(self, carrier, group, names, elem_bits, axes=()) -> list[Field]:
        return [self.field(carrier, n, elem_bits, axes, group=group) for n in names]

    def state(self, name, writer, **kw) -> State:
        if "fields" in kw:
            kw["fields"] = tuple(kw["fields"])
        s = self.states[name] = State(name, writer, **kw)
        return s

    def boundary(self, name, after=None, latency=None, coupling="rigid") -> Boundary:
        b = self.boundaries[name] = Boundary(name, after, latency, coupling)
        return b

    def stage(self, name, on, **kw) -> Stage:
        for k in ("state_reads", "state_writes", "requires"):
            if k in kw:
                kw[k] = tuple(t if isinstance(t, StateTap) else _tap(t) for t in kw[k])
        for k in ("reads", "reads_at_head", "writes", "creates", "consumes"):
            if k in kw:
                kw[k] = tuple(kw[k])
        if "modes" in kw and kw["modes"] is not None:
            kw["modes"] = frozenset(kw["modes"])
        if "emits" in kw:
            kw["emits"] = tuple(e if isinstance(e, Emit) else Emit(e) for e in kw["emits"])
        s = self.stages[name] = Stage(name, on, **kw)
        if name not in self.order:
            self.order.append(name)
        return s

    def join(self, name, kind, branches, **kw) -> Join:
        j = Join(name, kind, tuple(branches), **kw)
        self.joins.append(j)
        return j

    def fb(self, kind, src, dst, **kw) -> Feedback:
        if "modes" in kw and kw["modes"] is not None:
            kw["modes"] = frozenset(kw["modes"])
        f = Feedback(kind, src, dst, **kw)
        self.feedback.append(f)
        return f

    def route(self, name, src, dst, selector, **kw) -> Route:
        if "state_reads" in kw:
            kw["state_reads"] = tuple(t if isinstance(t, StateTap) else _tap(t) for t in kw["state_reads"])
        for k in ("creates", "consumes"):
            if k in kw:
                kw[k] = tuple(kw[k])
        r = self.routes[name] = Route(name, src, dst, selector, **kw)
        if name not in self.order:
            self.order.append(name)
        return r

    def merge(self, name, inputs, dst, policy, granularity, creates=()) -> Merge:
        m = self.merges[name] = Merge(name, tuple(inputs), dst, policy, granularity, tuple(creates))
        if name not in self.order:
            self.order.append(name)
        return m

    # queries -------------------------------------------------------------
    def bits(self, f: Field) -> Optional[int]:
        """Bits of one field per item, including its own axes (None if the width isn't modelled)."""
        if f.elem_bits is None:
            return None
        return f.elem_bits * prod(self.axes[a] for a in f.axes)

    def copies(self, carrier: str) -> int:
        """How many physical copies of a carrier exist (indexed carriers are replicated)."""
        c = self.carriers[carrier]
        return self.axes[c.index] if c.index else 1

    def carrier_fields(self, carrier: str) -> list[Field]:
        return [f for f in self.fields.values() if f.carrier == carrier]

    def resolve(self, ref: str, carrier: Optional[str] = None) -> list[Field]:
        """Resolve a field reference: "sym.dat", "dat" (on `carrier`), or a group "tag.*"."""
        if "." in ref and ref.split(".", 1)[0] in self.carriers:
            car, name = ref.split(".", 1)
        elif carrier is not None:
            car, name = carrier, ref
        else:
            raise ModelError(f"field reference {ref!r} needs a carrier")
        if name.endswith(".*"):
            grp = name[:-2]
            out = [f for f in self.carrier_fields(car) if f.group == grp]
        elif name == "*":
            out = self.carrier_fields(car)
        elif "." in name:                                  # group-qualified: "tag.msa"
            grp, member = name.split(".", 1)
            out = [f for f in self.carrier_fields(car) if f.group == grp and f.name == member]
        else:
            out = [f for f in self.carrier_fields(car) if f.name == name]
        if not out:
            raise ModelError(f"unknown field {ref!r} on carrier {car!r}")
        return out
