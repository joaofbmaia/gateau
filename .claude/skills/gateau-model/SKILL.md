---
name: gateau-model
description: Write or update a gateau model (a Python file describing a hardware architecture's dataflow) from RTL, documentation or what the user knows, then check and render it as a bus-view diagram. Use when asked to model, diagram or draw an RTL design, IP block or datapath with gateau, or to fix or extend a model in examples/.
---

# Writing a gateau model

You know how to read RTL and documentation. What you don't know is gateau itself: its eight
primitives, their exact API, and what the checks and the renderer read. That is all this file covers.
Human-facing guide: `docs/authoring.md`. Runnable starting point: `examples/template.py`. Reference
models: `examples/ethernet.py` (interface IP), `rocket.py` (CPU pipeline, hazards), `dprx.py` (lanes,
broadcast, ring, modes), `mstrx.py` (route, merge, indexed carriers, epoch).

## Deliverable and loop

A file defining `build() -> Design` and optionally `OUTSIDE = ("PHY", ...)`, the actors you don't
model, which feedback may end at.

```
python -m gateau model.py                         # validate and check; exit 1 on any ✗
python -m gateau model.py --html bus.html         # plain bus view
python -m gateau model.py --html chk.html --overlay checks      # also --overlay cost, --mode <mode>
```

Iterate until it validates and every `✗` is understood. Look at the render: a row reaching the right
edge means nothing consumes it, a row starting at the left edge means nothing creates it, and an
unconnected box means missing reads or writes. When you finish, report:
- the findings, with each `✗` classified as a design issue or a model gap;
- the facts you left unknown (`?`);
- anything the model can't express (below).

## Rules

- **Never guess a number.** A fact you can't source stays `None` or is left out, and its check reports
  `?`. A wrong depth or latency makes a check lie.
- **Cite sources.** Put the RTL location in `Join(evidence=...)`. For everything else use `note=`
  (kept in the model, not drawn).
- **Declaration order is flow order.** Stages, routes and merges become the drawing's columns in the
  order you declare them. `requires` and the availability check's "upstream" use this order, and so
  do hazard distances when the stages have no `between` boundaries.
- **Granularity:** one stage per transformation of the item, not per module. Aim for 6 to 16 stages;
  more becomes hard to read. A whole subsystem may be one stage with a `note`.

## API: `d = Design(name, params={}, axes={"lane": 4})`

`d.domains += [...]` and `d.modes += [...]` are plain lists. Every name you use must be declared,
otherwise `ModelError`.

| Call | Meaning |
|---|---|
| `d.carrier(name, item, domain, parent=None, index=None, ring=False)` | A flow of items at one rate. `parent`: nested rate (a beat inside a packet). `index=axis`: one copy per axis value, drawn as a deck and required as a route destination. `ring`: a field-less message ring. `domain` must be in `d.domains`; `"vid_clk[sid]"` means one clock per index. |
| `d.field(carrier, name, elem_bits, axes=(), availability="whole", group=None)` | Width is `elem_bits × prod(axes)`. `elem_bits=None` if unknown. `availability="tail"` means the field exists only once the whole item has passed. |
| `d.group(carrier, group, names, elem_bits, axes=())` | Several fields sharing a group, referred to as `grp.*`. |
| `d.state(name, writer, fields=(), cyclic=None, epoch=None, coverage={})` | Storage outside the item. `writer`: `"out-of-flow"` (config), `"in-flow"` (written by the flow: register files, scoreboards) or `"shared"` (written on one path, read on another). |
| `d.boundary(name, after=None, latency=None, coupling="rigid")` | A cut at a register stage. `after`+`latency` give the latency relative to another boundary. `coupling`: `rigid` (cannot stall), `elastic` (ready/valid), `lockstep` (stalls as one). |
| `d.stage(name, on, **kw)` | See stage keywords below. |
| `d.join(name, kind, branches, depth=, key=, key_bits=, in_flight=, evidence=)` | `kind`: `lat` (equal latency), `fifo` (in order), `key` (by tag). `branches` are stage names. |
| `d.fb(kind, src, dst, distance=None, modes=None, note="")` | `kind`: `data` (bypass), `ctrl` (control), `flow` (backpressure). Ends are stage, route or merge names, or `OUTSIDE` names. |
| `d.route(name, src, dst, selector, selector_field=, domain=, mapped=, default=, granularity="item", between=, creates=, consumes=, state_reads=)` | Demux into the indexed carrier `dst`. `domain`/`mapped`: selector values that exist and that map. `default`: where the rest go. `granularity`: `"item"` or `"axis s"`. |
| `d.merge(name, [MergeInput(source_stage, replicate=axis, msg_id=)], dst, policy, granularity, creates=())` | Mux. `source` must be a stage. `granularity` must name a carrier, the unit never split. `creates` is the field that records origin. |

Import `Buffer`, `Burst`, `Epoch`, `MergeInput` and `StateTap` from `gateau`.

### Stage keywords

`d.stage(name, on, ...)`:

- **`out=`**: a transfer to another carrier. Its `creates` resolve on `out`; everything else resolves
  on `on`.
  - When `out` is in another carrier family, the input carrier's rows end at this stage, provided
    nothing later touches the input carrier.
  - When `out` is a parent or child of `on`, it lifts fields (headers onto the packet) and the input
    carrier continues.
- **`between=("b0", "b1")`**: places the stage between two boundaries. Stages sharing the same pair
  make a `lat` join structural.
- **`reads`, `writes`, `creates`, `consumes`**: field references.
  - `creates` starts a row and `consumes` ends one.
  - `reads_at_head`: needed when the item starts. On a tail field this requires an upstream
    whole-item prebuffer.
- **`state_reads`, `state_writes`, `requires`**: `"cfg"`, `"cfg.field"`, or
  `StateTap(state, sub, switch=...)` when the switch point matters for epoch state.
  - `requires`: an upstream stage must have written the state first.
  - On routes, set the switch after building: `d.routes["R"].state_reads[0].switch = ...`.
- **`broadcast=(("tag.*",), "lane")`**: copies fields along an axis. The cost check measures the copies.
- **`replicate="lane"`**: ×N identical instances.
- **`condition="P_X"`**: the stage exists only under a parameter (dashed box).
- **`modes=["training"]`**: the stage is active only in those modes (faded otherwise).
- **`emits=["msg"]`**, or `Emit(carrier, msg_id)`: sends items onto another carrier, usually a ring.
- **`buffer=Buffer(depth, unit, policy, burst, item_max)`**:
  - `policy` is `drop`, `prebuffer` or `stall`.
  - `item_max`: the largest item, in `unit`s, that must fit whole.
  - `burst=Burst(items, in_rate, out_rate)` gives peak occupancy for a rigid-to-stallable edge.
- **`note=`**: free text, not drawn.

### Field references

- `"dat"`: on the stage's own carrier.
- `"car.dat"`: another carrier.
- `"grp.*"`: a whole group.
- `"grp.dat"`: a group member when names repeat.
- `"*"`: every field of the carrier.

## What each check needs, or it reports `?`

| Check | Inputs | Fails when |
|---|---|---|
| state use | `state(fields=...)` plus stage taps on `"cfg.field"` | a listed field is never read. A bare `"cfg"` tap counts as reading all fields. |
| requires | `requires=` | no earlier stage `state_writes` it |
| join `lat` | branches with the same `between`, or boundaries with `latency` | latencies differ |
| join `fifo` / `key` | `depth`+`in_flight` / `key_bits`+`in_flight` | too shallow, or too few keys |
| hazard | `in-flow` state read by an earlier stage and written by a later one, plus `coverage` | a distance in 1..window is uncovered |
| availability | `reads_at_head` on a `tail` field, plus an upstream `prebuffer` with `depth` and `item_max` | no prebuffer, or `item_max > depth` |
| rigid edge | a stage whose `between` crosses rigid to non-rigid, or non-rigid to rigid, with its `buffer` | see below |
| route | `domain`, `mapped`, `default`; `selector_field`'s axes vs `granularity` | values with no destination; the selector varies inside the routed unit |
| merge | `creates`, or a distinct `msg_id` per source; `granularity` | origins indistinguishable; granularity carrier has a parent (interleaving) |
| epoch | `Epoch(swap_point)` plus a `switch` on every reader | a reader switches elsewhere |
| cost (info) | `broadcast`, routes, and known widths | never fails |

Rigid-edge details:
- **Rigid into stallable:** a `drop` buffer must hold `item_max`; any other buffer needs a `burst`,
  and its peak must fit the depth.
- **Stallable into rigid:** the buffer must be a `prebuffer` with `depth ≥ item_max`.

Hazard `coverage`:
- Use `{distance: "how"}`, or per producer class `{"ALU op": {1: "bypass x", 2: "...", 3: "RF"}}`.
- `"*"` covers every distance, as a scoreboard does.
- Unclassified coverage also counts `fb("data", ..., distance=k)` bypasses.

## What the model can't express (say so; don't force it)

- simplification marks (≈);
- per-replica exceptions;
- out-of-order completion;
- clock-ratio carriers;
- merge fairness;
- semantic gaps such as "this checksum is never verified". Put these in `note=` and in your report.
