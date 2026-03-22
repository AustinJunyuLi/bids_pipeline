"""Backward-compatible alias for the materialize stage during migration."""

from __future__ import annotations

from skill_pipeline.materialize import run_materialize


def run_canonicalize(*args, **kwargs):
    return run_materialize(*args, **kwargs)
