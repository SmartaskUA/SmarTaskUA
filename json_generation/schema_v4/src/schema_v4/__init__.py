"""Schema v4.0 - validator and tools.

A real package, unlike v3.0's flat-sibling layout: the modules import each other
relatively (``from . import core``), so v3 and v4 can be loaded into one
interpreter. v3's style registers top-level modules named ``core``, ``common``
and ``validator``, which collide.

Everything is driven from the Makefile at the package root::

    make test                       the conformance suite
    make validate                   examples/ and templates/
    make validate DIR=some/folder   anything else
    make result                     regenerate the example result

Under the hood each of those is ``python3 -m schema_v4.<tool>`` with ``src`` on
the path.

Layout:

    core                  domain + CSV I/O, decides no policy
    common                Report + the checks both forms share
    validate_input  the problem form's semantic layer
    validate_result       the result form's cross-checks
    validator             orchestrator + CLI
    build_example_result  builds the worked example under examples/
"""

__version__ = "4.0.0"
