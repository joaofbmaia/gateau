# gateau

A notation for drawing hardware architectures as dataflow, and a checker for the
facts those drawings depend on. The notation is described in
[`docs/notation-v1.html`](docs/notation-v1.html) (v1.2); the studies that shaped it are
`docs/notation-sketchbook*.html`.

This package holds the model, the checks, and a renderer for the bus view.

## Models

Models are plain Python. A model file defines `build() -> Design`:

```python
from gateau import Design

d = Design("example", axes=dict(l=4, s=2))
d.domains += ["lnk_clk"]
d.carrier("sym", "one symbol group per cycle", "lnk_clk")
d.field("sym", "dat", 8, ("l", "s"))
d.boundary("b0")
d.boundary("b1", after="b0", latency=1)
d.stage("PARS", "sym", between=("b0", "b1"), reads=["dat"])
d.stage("SCRM", "sym", between=("b0", "b1"), writes=["dat"])
d.join("tags-meet-data", "lat", ["PARS", "SCRM"])
```

The eight primitives are `carrier`, `field`, `stage`, `boundary`, `join`, `state`,
feedback (`fb`), and `route` / `merge`.

## Checks

```
python -m gateau examples/dprx.py
```

| Check | What it asks |
|---|---|
| state use | is every configuration field read by something? does every `requires` have an upstream writer? |
| join | do the branches of a join meet correctly (equal latency, FIFO depth, key space)? |
| hazard | is every read-after-write distance inside a state's window covered? |
| availability | is a tail field needed at an item's head backed by a whole-item buffer? |
| rigid edge | does a buffer where an unstallable region meets a stallable one cover its peak? |
| cost | how many bits are copies (broadcasts, routes)? |
| route | does every selector value have a destination, at the right granularity? |
| merge | can origins be told apart afterwards, and are coarser items never split? |
| epoch | does every reader of double-buffered state switch at the declared point? |

Each finding is `pass`, `fail`, `unchecked` (the model lacks the information) or `info`.

## Bus view

```
python -m gateau examples/mstrx.py --html mstrx.html
python -m gateau examples/dprx.py --svg dprx.svg --mode training
python -m gateau examples/dprx.py --html dprx-cost.html --overlay cost
```

`gateau/render.py` lays out the bus view from the model using fixed rules. No layout is
placed by hand.

- **Columns:** one per stage, route or merge, in flow order.
- **Bands:** rings first, then a depth-first walk of the flow, so that chains of carriers
  stay adjacent. Children sit under their parent.
- **Rows:** a row is live from the stage that creates it until it is consumed, or until
  its items move to another carrier.
- **Boxes:** a box covers the rows it writes, creates or consumes. Reads are dots on a
  connector. Routes and merges are drawn as demux and mux trapezoids.
- **Rigid shading:** comes from boundary couplings.
- **State:** shown as pills above the bands. Out-of-flow reads from deep bands are drawn
  as stubs.
- **Feedback:** drawn in the gutter, shortest span nearest the bands.
- **Checks:** only in the checks view (below), so the other views stay plain drawings.

Two options change the drawing without moving the layout:

- `--mode` fades whatever is inactive in that mode.
- `--overlay cost` scales line weight by bits × copies.
- `--overlay checks` is the only view with check results. It puts one badge on each subject
  (worst status, a count when there are several, every message in the tooltip) and lists every
  finding under the figure. The drawing keeps full contrast.

## Examples and tests

- `examples/dprx.py`: Parretto's DisplayPort RX (study 04).
- `examples/mstrx.py`: an invented multi-stream DP receiver (study 05).
- `examples/rocket.py`: Rocket's integer pipeline, with hazard coverage per producer class (study 02).
- `examples/ethernet.py`: verilog-ethernet's 10G MAC/IP/UDP RX and TX (study 03).

The tests require each example to reproduce exactly the findings its study drew by
hand, and give every check a passing and a failing case. The renderer tests check
structure, not pixels: every item and carrier is drawn, the band order, where rows end,
which bands are shaded, mode fading, and badges.

```
pip install pytest
python -m pytest
```
