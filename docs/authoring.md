# Writing a gateau model

A gateau model is a short Python file that states the facts a bus-view drawing depends on.
`python -m gateau` checks the facts against each other and draws the views. This guide walks
through writing a model from documentation and RTL. It uses `examples/ethernet.py` as the
worked example and cites the verilog-ethernet file that each fact came from.

Start by copying `examples/template.py`. It runs as is and uses the common primitives.
When something isn't covered here, the four examples are the reference:

| Example | What it shows |
|---|---|
| `examples/ethernet.py` | interface IP: header extract and insert, frame FIFOs, rigid links at both ends |
| `examples/rocket.py` | a CPU pipeline: lockstep boundaries, bypasses, hazard coverage per instruction class |
| `examples/dprx.py` | a link receiver: lanes, broadcast copies, a message ring, modes, clock domains |
| `examples/mstrx.py` | routing and merging streams: indexed carriers, epoch state, burst-sized buffers |

## The loop

```
python -m gateau mymodel.py                                  # checks; exit 1 if any fail
python -m gateau mymodel.py --html bus.html                  # the drawing
python -m gateau mymodel.py --html checks.html --overlay checks
```

Write a little, run it, and look at the drawing. Undeclared names stop the run with a
`ModelError` that names the bad reference. Findings come in four kinds:

| Mark | Meaning | What to do |
|---|---|---|
| `✓` pass | the facts you gave are consistent | nothing |
| `✗` fail | either the design has a problem or the model is wrong | go back to the RTL to see which |
| `?` unchecked | the check needs a fact you haven't given | find it (a depth, latency, rate) or accept it as unknown |
| `·` info | a measurement, such as bits spent on copies | read it |

A wrong guess makes a check lie. When you don't know a fact, leave it out (`None`) and let
the check say `?`.

## The method, step by step

### 1. Name the item

Decide what one unit of flow is at each rate. In the 10G stack, data arrives as 66-bit
blocks, is processed as 64-bit AXI-Stream beats, and has headers that belong to a whole
packet. That gives three carriers on each side. The beat carrier sits inside the packet
carrier because its rate nests within the packet's.

```python
d.carrier("blk_rx", "one 66-bit block per cycle", "clk")
d.carrier("pkt_rx", "one received packet", "clk")
d.carrier("beat_rx", "one 64-bit beat", "clk", parent="pkt_rx")
```

Every carrier names a clock domain, which must be listed in `d.domains`. A design with
two clocks gets two domains, and the drawing colours each carrier by its domain.

### 2. Stages, in flow order

Make one stage for each module or block that does something to the item. The declaration
order of stages, routes and merges sets the drawing's columns, so declare them in flow
order. A stage that moves items to another carrier names that carrier with `out=`. The
MAC turns blocks into beats (`axis_baser_rx_64.v`):

```python
d.stage("MAC_DLY", "blk_rx", out="beat_rx", between=("r1", "r3"), reads=["data"],
        creates=["tdata", "tkeep", "tlast"])
```

### 3. Boundaries

A boundary is a cut across the flow at a register stage. Each one has a coupling:

| Coupling | Meaning |
|---|---|
| `rigid` | the region cannot stall: a link or free-running pipeline |
| `elastic` | ready/valid handshaking |
| `lockstep` | everything stalls together, as in a CPU pipeline |

The latency between two boundaries is declared with `after=` and `latency=`. In the RX MAC,
data is held two blocks (`input_data_d0`, `input_data_d1`) while the CRC verdict is
computed:

```python
d.boundary("r1", coupling="rigid")
d.boundary("r3", after="r1", latency=2, coupling="rigid")
d.boundary("rf", coupling="elastic")          # output of the RX frame FIFO
```

Placing a stage between two boundaries (`between=("r1", "r3")`) is what lets the join,
hazard and rigid-edge checks measure distances.

### 4. Fields

Each field has an element width in bits and optional named axes. `tdata` is 8 bits along
`byte`, and `d.axes` says `byte=8`. Use a group for headers you read or strip as a unit.

```python
d.field("beat_rx", "tdata", 8, ("byte",))
d.field("pkt_rx", "fcs_ok", 1, availability="tail")      # known only after the last beat
for n, w in (("dest_mac", 48), ("src_mac", 48), ("type", 16)):
    d.field("pkt_rx", n, w, group="eth")
```

`availability="tail"` marks a field that only exists once the whole item has passed, such as
a CRC verdict, a length written at the end, or a checksum over the payload. A field whose
width you haven't worked out takes `None`.

Reading a field: a bare name resolves on the stage's own carrier, `car.field` reaches
another carrier, `grp.*` is a whole group, and `grp.field` is one member of a group.

### 5. Forks and joins

Where two paths split and meet again, say how they stay matched:

| Kind | Meaning | Facts the check needs |
|---|---|---|
| `lat` | equal latency | branches between the same boundaries, or boundaries with known latency |
| `fifo` | in-order pairing through a queue | `depth` and `in_flight` |
| `key` | matching by tag | `key_bits` and `in_flight` |

Put where the RTL guarantees the join in `evidence`. It is often only a comment:

```python
d.join("crc-verdict-meets-data", "lat", ["MAC_DLY", "MAC_CRC"],
       evidence="input_data_d0 / input_data_d1 in axis_baser_rx_64.v")
```

### 6. Routes and merges

A route sends each item, or each slice of an item along an axis, to one copy of an
indexed carrier, chosen by a selector. A merge serialises several sources into one
carrier, and must either create a field that says where each item came from or rely on
ids the sources already carry. The Ethernet stack has neither; see `examples/mstrx.py`.

### 7. State

State is anything the flow reads or writes that does not travel with the item. Its
writer type is one of three:

| Writer | Meaning | Example |
|---|---|---|
| `out-of-flow` | written by something outside the flow | configuration registers, written by software |
| `in-flow` | written by the flow itself | a register file |
| `shared` | written by one path and read by another | the ARP cache, filled by RX and read by TX |

```python
d.state("arp", "shared")                                    # arp.v, arp_cache.v
d.stage("ARP_RX", "pkt_rx", reads=["type"], state_writes=["arp"])
d.stage("ARP_TX", "pkt_tx", reads=["dst_ip"], state_reads=["arp"], writes=["dest_mac"])
```

List the fields of configuration state, because the state-use check reports fields that
nothing reads. For in-flow state with read-after-write hazards, give `coverage`, the way
each distance is handled. `examples/rocket.py` gives it per instruction class.

### 8. Feedback

Feedback is drawn in the gutter below the bands:

| Kind | Meaning |
|---|---|
| `data` | a bypass; with `distance=` it counts toward hazard coverage |
| `ctrl` | control sent back upstream |
| `flow` | backpressure |

Feedback may end at an actor outside the design; list those actors in `OUTSIDE`.

```python
d.fb("ctrl", "PHY_RX", "SERDES", note="bitslip until block lock")
d.fb("flow", "ETH_RX", "FIFO_RX", note="tready")
```

### 9. Buffers, and the checks that use them

Buffers carry the facts behind the rigid-edge and availability checks. The RX frame FIFO
(`RX_FIFO_DEPTH = 4096` in `eth_mac_10g_fifo.v`) sits where the rigid link meets the
stallable stack, and it drops frames on overflow. To pass, it has to hold one whole
maximum-size frame:

```python
d.stage("FIFO_RX", "beat_rx", between=("r3", "rf"), reads=["pkt_rx.fcs_ok"],
        buffer=Buffer(depth=4096, unit="byte", policy="drop", item_max=1518))
```

The UDP checksum is a tail field. It needs the whole payload, but it is written into the
header, which goes first, so `UDP_TX` reads it with `reads_at_head`. That passes only
because the checksum stage prebuffers a whole datagram (`PAYLOAD_FIFO_DEPTH = 2048` beats in
`udp_checksum_gen_64.v`):

```python
d.stage("CSUM", "pkt_tx", creates=["checksum"],
        buffer=Buffer(depth=2048 * 8, unit="byte", policy="prebuffer", item_max=1480))
d.stage("UDP_TX", "pkt_tx", out="beat_tx", reads_at_head=["udp.*"], consumes=["udp.*"])
```

Set `CSUM`'s depth to 1024 and the availability check fails, which is the point of
modelling it.

### 10. Review the drawing

The drawing is laid out by rule, so it shows what the model says, not what you meant.
Signs of a modelling slip:

- a row that runs to the right edge when something should consume it (a missing `consumes`);
- a row that starts at the left edge when some stage makes it (a missing `creates`);
- a stage with no connections (missing `reads` or `writes`);
- a box spanning bands you didn't expect (check `out=` and the carrier's parent);
- a `✗` whose subject you don't recognise: read the message, then the RTL.

Once the model is right, keep it honest with a test that pins its findings. Each example
has one in `tests/test_examples.py`.

## What the model cannot say yet

- that a field is simplified (the `≈` mark in the hand-drawn figures);
- exceptions for one replica of a replicated stage;
- out-of-order completion, and carriers whose rates are a clock ratio;
- semantic facts such as "this checksum is never verified". Put those in `note=`, which is
  kept in the model but not drawn.
