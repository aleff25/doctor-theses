#!/usr/bin/env python3
"""Walking skeleton of stages (1) -> (2) -> (3) for one subject system.

    ./.venv/bin/python run_pipeline.py --system petclinic

Snapshot identity comes from `subjects/subjects.lock.json`, never from the
working clone's HEAD, so a stray `git pull` under `subjects/` cannot silently
change what a stored profile claims to describe.

Output determinism: emitted artifacts contain no timestamps and no absolute
paths. Re-running on the same pinned commit must produce byte-identical files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for package_dir in ("extractor", "metamodel", "metrics"):
    sys.path.insert(0, os.path.join(HERE, package_dir))

from aam4j_extractor.bundle import extract, write_bundle  # noqa: E402
from aam4j_extractor.static_regex import RegexStaticAnalyser  # noqa: E402
from aam4j_metrics.catalogue import compute_all  # noqa: E402
from aam4j_metrics.graph import build_graph  # noqa: E402
from aam4j_metrics.profile import to_rows, write_profile  # noqa: E402
from aam4j_model.build import build, write_model  # noqa: E402


def pinned_commit(system: str) -> str:
    with open(os.path.join(HERE, "subjects", "subjects.lock.json"), encoding="utf-8") as handle:
        lock = json.load(handle)
    for subject in lock["subjects"]:
        if subject["name"] == system:
            return subject["commit"]
    raise SystemExit(f"{system!r} is not in subjects.lock.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", default="petclinic")
    parser.add_argument("--data-root", default=os.path.join(HERE, "data"))
    args = parser.parse_args()

    system = args.system
    repo_root = os.path.join(HERE, "subjects", system)
    snapshot = pinned_commit(system)

    bundle_dir = os.path.join(args.data_root, "raw", system, snapshot[:8])
    model_path = os.path.join(args.data_root, "interim", system, snapshot[:8], "model.json")
    profile_path = os.path.join(args.data_root, "processed", system, snapshot[:8], "metric_profile.csv")

    bundle = extract(repo_root, system, snapshot, RegexStaticAnalyser())
    written = write_bundle(bundle, bundle_dir)

    model = build(bundle)
    write_model(model, model_path)

    graph = build_graph(model)
    values = compute_all(model, graph)
    rows = to_rows(model, graph, values)
    profiles = write_profile(rows, profile_path)

    print(f"system     {system}")
    print(f"snapshot   {snapshot}")
    print(f"analyser   {bundle['manifest']['static_analyser']}")
    print()
    print("services (DD-002 role, and the rule that assigned it)")
    for service in model.services:
        print(f"  {service.name:<20} {service.role:<15} {service.role_rule}")
    print()
    print(f"G = ({len(graph.nodes)} services, {len(graph.edges)} edges)  "
          f"scope roles={'|'.join(graph.roles_included)} provenance={'|'.join(graph.provenance_included)}")
    for source, target, kind in graph.edges:
        print(f"  {source.split('/')[-1]} -> {target.split('/')[-1]} ({kind})")
    print()
    print("metric profile")
    print(f"  {'metric':<10} {'element':<40} {'value':>7}  note")
    for row in rows:
        value = row["value"] if row["determined"] == "true" else "n/d"
        print(f"  {row['metric']:<10} {row['element_id']:<40} {value:>7}  {row['note']}")
    print()
    if model.evidence_gaps:
        print("evidence gaps recorded in the model")
        for gap in model.evidence_gaps:
            print(f"  [{gap.concern}] {gap.subject}: {gap.reason}")
        print()
    for path in written + [model_path] + profiles:
        print(f"wrote {os.path.relpath(path, HERE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
