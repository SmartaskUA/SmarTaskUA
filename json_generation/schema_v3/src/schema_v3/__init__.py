"""Tooling for the v3.0 scheduling-problem schema.

Three modules, run as CLIs and imported by the tests:

- ``core``      -- the shared domain (time maths, cell semantics, candidate
                   generation, the feasibility scan). Imports neither sibling.
- ``transform`` -- compiles a declarative problem into the expanded form.
- ``validator`` -- validates a problem (either form) or a solution.

The modules import each other as flat siblings (``import core``), which works
because each is run as a script or imported with this directory on ``sys.path``.
"""
