"""Import paths for running scripts from the repository root.

`pyproject.toml` sets the same list under `tool.pytest.ini_options.pythonpath`,
which covers the test run. This file covers everything else (`python
run_pipeline.py`, `python metrics/derive_thresholds.py`, a REPL), so the two
entry points never disagree about where the packages are.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIRS = ("extractor", "metamodel", "metrics", "api", "models")

for package_dir in PACKAGE_DIRS:
    path = os.path.join(HERE, package_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
