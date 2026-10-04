"""gateau: a notation and checker for hardware architecture dataflow (notation v1.2)."""
from .model import (Boundary, Buffer, Burst, Carrier, Design, Emit, Epoch, Feedback, Field, Join,
                    Merge, MergeInput, ModelError, Route, Stage, State, StateTap)
from .checks import Finding, report, run_all, validate

__all__ = ["Boundary", "Buffer", "Burst", "Carrier", "Design", "Emit", "Epoch", "Feedback", "Field",
           "Finding", "Join", "Merge", "MergeInput", "ModelError", "Route", "Stage", "State", "StateTap",
           "report", "run_all", "validate"]
