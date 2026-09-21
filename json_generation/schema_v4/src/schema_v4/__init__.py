"""Schema v4.0 - validator and SISQUAL adapter.

A real package, unlike v3.0's flat-sibling layout: the modules import each other
relatively (``from . import core``), so v3 and v4 can be loaded into one
interpreter. v3's style registers top-level modules named ``core``, ``common``
and ``validator``, which collide.

Run the tools as modules, with ``src`` on the path::

    PYTHONPATH=src python3 -m schema_v4.validator     <file-or-folder>
    PYTHONPATH=src python3 -m schema_v4.sisqual_adapt <raw-bundle-dir> -o <out>

Layout:

    core                  domain + CSV I/O, decides no policy
    common                Report + the checks both forms share
    validate_declarative  the problem form's semantic layer
    validate_result       the result form's cross-checks
    validator             orchestrator + CLI
    sisqual_adapt         SISQUAL's dialect -> canonical v4
"""

__version__ = "4.0.0"
