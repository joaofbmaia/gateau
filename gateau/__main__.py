"""Run the checks on a model file:  python -m gateau examples/dprx.py

The file must define build() -> Design, and may define OUTSIDE (names of actors outside the design).
"""
import importlib.util
import sys

from .checks import report, run_all


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    spec = importlib.util.spec_from_file_location("model", argv[1])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    design = mod.build()
    findings = run_all(design, getattr(mod, "OUTSIDE", ()))
    print(f"{design.name}: {len(findings)} findings\n")
    print(report(findings))
    return 1 if any(f.status == "fail" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
