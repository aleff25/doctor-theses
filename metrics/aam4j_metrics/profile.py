"""Metric-profile emission in the long format of `docs/01-pipeline.md`.

Contract columns, in order:

    system, snapshot, element_id, element_kind, metric, value

Four columns are appended. The first three are required by constraint 4 of
`docs/01-pipeline.md` ("everything is versioned"); the last two are what lets a
metric report *undetermined* instead of a misleading zero:

    metamodel_version, catalogue_version, graph_scope, determined, note

`graph_scope` records which roles and which provenance were in `G`, so a figure
that includes infrastructure nodes is self-describing — DD-002 requires any such
figure to say so.

Parquet is deferred: it needs a third-party writer, and CSV is the half of the
contract that can be diffed and hand-checked. The row shape is identical, so
adding a Parquet writer is a serialisation change only.
"""

from __future__ import annotations

import csv
import json
import os

from aam4j_model.model import ArchitectureModel

from .catalogue import CATALOGUE_VERSION, MetricValue
from .graph import ServiceGraph

COLUMNS = [
    "system",
    "snapshot",
    "element_id",
    "element_kind",
    "metric",
    "value",
    "metamodel_version",
    "catalogue_version",
    "graph_scope",
    "determined",
    "note",
]


def to_rows(model: ArchitectureModel, graph: ServiceGraph, values: list[MetricValue]) -> list[dict]:
    scope = "roles=" + "|".join(graph.roles_included) + ";provenance=" + "|".join(graph.provenance_included)
    rows = [
        {
            "system": model.system,
            "snapshot": model.snapshot,
            "element_id": value.element_id,
            "element_kind": value.element_kind,
            "metric": value.metric,
            "value": "" if value.value is None else repr(value.value),
            "metamodel_version": model.metamodel_version,
            "catalogue_version": CATALOGUE_VERSION,
            "graph_scope": scope,
            "determined": "true" if value.determined else "false",
            "note": value.note,
        }
        for value in values
    ]
    return sorted(rows, key=lambda r: (r["metric"], r["element_id"]))


def write_profile(rows: list[dict], csv_path: str) -> list[str]:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    json_path = os.path.splitext(csv_path)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return [csv_path, json_path]
