"""Deterministic quantitative engine.

Every public function is pure: array inputs in, numbers out, no I/O.
Claude never calls these directly; it receives the results as tool outputs.
"""
