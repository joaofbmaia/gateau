# gateau

A notation for drawing hardware architectures as dataflow, and a checker for the
facts those drawings depend on. The notation is described in
[`docs/notation-v1.html`](docs/notation-v1.html) (v1.2); the studies that shaped it are
`docs/notation-sketchbook*.html`.

This package is step 1: the model and the checks. There is no renderer yet.

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

## Examples and tests

- `examples/dprx.py`: Parretto's DisplayPort RX (study 04).
- `examples/mstrx.py`: an invented multi-stream DP receiver (study 05).

The tests require each example to reproduce exactly the findings its study drew by
hand, and give every check a passing and a failing case:

```
pip install pytest
python -m pytest
```
