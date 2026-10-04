"""Run the checks on a model file, and optionally draw its bus view.

  python -m gateau examples/dprx.py
  python -m gateau examples/dprx.py --html dprx.html [--mode training] [--overlay cost|checks]
  python -m gateau examples/dprx.py --svg dprx.svg

The file must define build() -> Design, and may define OUTSIDE (names of actors outside the design).
The exit code is 1 if any check fails, whether or not a drawing was asked for.
"""
import argparse
import importlib.util
import sys

from .checks import report, run_all


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m gateau", description=__doc__.strip().splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("--svg", metavar="FILE", help="write the bus view as a bare SVG")
    ap.add_argument("--html", metavar="FILE", help="write the bus view as an HTML page")
    ap.add_argument("--mode", help="fade the parts of the design inactive in this mode")
    ap.add_argument("--overlay", choices=["cost", "checks"])
    args = ap.parse_args(argv[1:])

    spec = importlib.util.spec_from_file_location("model", args.model)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    design = mod.build()
    findings = run_all(design, getattr(mod, "OUTSIDE", ()))
    print(f"{design.name}: {len(findings)} findings\n")
    print(report(findings))

    if args.mode and args.mode not in design.modes:
        ap.error(f"mode {args.mode!r} not in {design.modes}")
    if args.svg or args.html:
        from .render import render_html, render_svg
        if args.svg:
            with open(args.svg, "w", encoding="utf-8") as f:
                f.write(render_svg(design, findings, args.mode, args.overlay))
        if args.html:
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(render_html(design, findings, args.mode, args.overlay))
    return 1 if any(f.status == "fail" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
