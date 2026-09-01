#!/usr/bin/env python3
"""Assemble everything the dashboard shows into one JSON file.

    ./.venv/bin/python dashboard/build_dashboard_data.py

Reads only what the pipeline already wrote (`data/`), the catalogue data
(`metrics/catalogue/`, `metamodel/catalogue/`) and the prose in
`dashboard/content/`, then writes `dashboard/public/dashboard.json`. It computes
no metric of its own: a dashboard that recomputed its numbers could disagree
with the stored profile, and then neither would be the result.

The one thing it adds is **code**. Every fact the extractor emits carries a
repo-relative file and a line, so this script opens the pinned clone and lifts
the lines around each one. That is what lets a card in the dashboard answer
"why does this service have AIS = 1" with the actual Java statement that made
the edge, rather than with a number.

Two invariants are enforced rather than assumed, so the dashboard cannot drift
away from the catalogue:

1. Every metric in `aam4j_metrics.catalogue.METRICS` must have an entry in
   `content/metrics.json`. Adding a metric without documenting it fails here.
2. Every reference key used by a metric or a rule must exist in
   `content/references.json`. A dangling citation fails here.

Determinism: the output carries no timestamp and no absolute path, so a diff
after a second run is a bug rather than noise (P4).
"""

from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for package_dir in ("extractor", "metamodel", "metrics", "models"):
    sys.path.insert(0, os.path.join(ROOT, package_dir))

from aam4j_metrics.catalogue import CATALOGUE_VERSION, METRICS  # noqa: E402
from aam4j_metrics.thresholds import Thresholds  # noqa: E402
from aam4j_model.model import METAMODEL_VERSION  # noqa: E402

SNIPPET_CONTEXT = 4
ENDPOINT_SNIPPET_BUDGET = 12  # per service; the rest keep file and line only

# Annotations that a role rule can fire on. Everything else is noise here:
# Train Ticket alone declares 971 type annotations.
ROLE_ANNOTATIONS = {"EnableConfigServer", "EnableAdminServer", "EnableEurekaServer", "EnableDiscoveryClient"}


def read_json(*parts: str) -> dict:
    with open(os.path.join(*parts), encoding="utf-8") as handle:
        return json.load(handle)


class SnippetReader:
    """Lifts source lines out of a pinned clone, and caches whole files.

    A missing clone is not an error: the dashboard degrades to file and line,
    which is still enough to find the code by hand. Refusing to build without
    `subjects/` would make the dashboard harder to reproduce than the pipeline.
    """

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self.available = os.path.isdir(repo_root)
        self._cache: dict[str, list[str] | None] = {}
        self.misses = 0

    def _lines(self, relative: str) -> list[str] | None:
        if relative not in self._cache:
            path = os.path.join(self.repo_root, relative)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    self._cache[relative] = handle.read().splitlines()
            except OSError:
                self._cache[relative] = None
        return self._cache[relative]

    def at(self, source: dict | None, context: int = SNIPPET_CONTEXT) -> dict | None:
        """`{file, line, start_line, lines[]}`, or file and line alone if unreadable."""
        if not source or not source.get("file"):
            return None
        relative, line = source["file"], int(source.get("line") or 0)
        record = {"file": relative, "line": line, "start_line": None, "lines": None}
        lines = self._lines(relative)
        if lines is None:
            self.misses += 1
            return record
        if line <= 0:
            # File-level evidence (a compose `depends_on`, a DDL file): show the
            # head of the file and say so, rather than pointing at a line that
            # the extractor never claimed.
            start, end = 1, min(len(lines), 14)
        else:
            start, end = max(1, line - context), min(len(lines), line + context)
        record["start_line"] = start
        record["lines"] = lines[start - 1 : end]
        return record


def load_profile(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    out = []
    for row in rows:
        determined = row["determined"] == "true"
        out.append(
            {
                "element_id": row["element_id"],
                "element_kind": row["element_kind"],
                "metric": row["metric"],
                "value": float(row["value"]) if determined and row["value"] != "" else None,
                "determined": determined,
                "note": row["note"],
            }
        )
    return out


def build_system(subject: dict, data_root: str) -> dict:
    system, commit = subject["name"], subject["commit"]
    short = commit[:8]
    raw = os.path.join(data_root, "raw", system, short)
    model = read_json(data_root, "interim", system, short, "model.json")
    profile = load_profile(os.path.join(data_root, "processed", system, short, "metric_profile.csv"))
    static = read_json(raw, "static.json")
    config = read_json(raw, "configuration.json")
    manifest = read_json(raw, "manifest.json")
    snippets = SnippetReader(os.path.join(ROOT, "subjects", system))

    metrics_by_element: dict[str, list[dict]] = {}
    for row in profile:
        metrics_by_element.setdefault(row["element_id"], []).append(
            {k: row[k] for k in ("metric", "value", "determined", "note")}
        )

    service_id_by_name = {s["name"]: s["id"] for s in model["services"]}
    gaps_by_subject: dict[str, list[dict]] = {}
    for gap in model.get("evidence_gaps", []):
        gaps_by_subject.setdefault(gap["subject"], []).append(gap)

    # --- evidence, grouped by the service it belongs to --------------------
    endpoints: dict[str, list[dict]] = {}
    for fact in static["endpoints"]:
        endpoints.setdefault(fact["module"], []).append(fact)
    entities: dict[str, list[dict]] = {}
    for fact in static["entities"]:
        entities.setdefault(fact["module"], []).append(fact)
    annotations: dict[str, list[dict]] = {}
    for fact in static["type_annotations"]:
        if fact["annotation"] in ROLE_ANNOTATIONS:
            annotations.setdefault(fact["module"], []).append(fact)
    schemas: dict[str, list[dict]] = {}
    for fact in static["schema_declarations"]:
        schemas.setdefault(fact["module"], []).append(fact)

    dependency_facts: dict[tuple[str, str], list[dict]] = {}
    for document in (static, config):
        for fact in document["declared_dependencies"]:
            key = (fact["source"], fact["target_hint"])
            dependency_facts.setdefault(key, []).append(
                {
                    "evidence_class": document["evidence_class"],
                    "mechanism": fact["mechanism"],
                    "detail": fact.get("detail"),
                    "snippet": snippets.at(fact["evidence"]),
                }
            )

    modules_by_name = {m["service_name"]: m for m in manifest["modules"]}

    services = []
    for record in model["services"]:
        name = record["name"]
        outbound, inbound = [], []
        for dependency in model["dependencies"]:
            if dependency["source"] == record["id"]:
                target = dependency["target"].split("/")[-1]
                outbound.append(
                    {
                        "other": dependency["target"],
                        "other_name": target,
                        "kind": dependency["kind"],
                        "provenance": dependency["provenance"],
                        "mechanisms": dependency["mechanisms"],
                        "facts": dependency_facts.get((name, target), []),
                    }
                )
            elif dependency["target"] == record["id"]:
                source = dependency["source"].split("/")[-1]
                inbound.append(
                    {
                        "other": dependency["source"],
                        "other_name": source,
                        "kind": dependency["kind"],
                        "provenance": dependency["provenance"],
                        "mechanisms": dependency["mechanisms"],
                        "facts": dependency_facts.get((source, name), []),
                    }
                )

        endpoint_records = []
        for index, fact in enumerate(sorted(endpoints.get(name, []), key=lambda f: (f["route_template"], f["http_method"]))):
            endpoint_records.append(
                {
                    "http_method": fact["http_method"],
                    "route_template": fact["route_template"],
                    "declaring_type": fact["declaring_type"],
                    "snippet": snippets.at(fact["source"]) if index < ENDPOINT_SNIPPET_BUDGET else {
                        "file": fact["source"]["file"], "line": fact["source"]["line"],
                        "start_line": None, "lines": None,
                    },
                }
            )

        entity_records = [
            {"java_type": f["java_type"], "table": f["table"], "snippet": snippets.at(f["source"])}
            for f in sorted(entities.get(name, []), key=lambda f: f["java_type"])
        ]
        schema_records = [
            {
                "store_name": f["store_name"], "vendor": f["vendor"], "tables": f["tables"],
                "foreign_tables": f["foreign_tables"], "snippet": snippets.at(f["source"]),
            }
            for f in sorted(schemas.get(name, []), key=lambda f: (f["vendor"], f["store_name"]))
        ]
        annotation_records = [
            {"annotation": f["annotation"], "java_type": f["java_type"], "snippet": snippets.at(f["source"])}
            for f in sorted(annotations.get(name, []), key=lambda f: f["annotation"])
        ]

        module = modules_by_name.get(name)
        services.append(
            {
                "id": record["id"],
                "name": name,
                "role": record["role"],
                "role_rule": record["role_rule"],
                "technology": record["technology"],
                "source_module": record["source_module"],
                "has_source_module": record["has_source_module"],
                "in_graph": record["role"] == "functional",
                "metrics": sorted(metrics_by_element.get(record["id"], []), key=lambda m: m["metric"]),
                "maven_dependencies": sorted(d["artifact_id"] for d in module["dependencies"]) if module else [],
                "evidence": {
                    "role_annotations": annotation_records,
                    "endpoints": endpoint_records,
                    "entities": entity_records,
                    "schemas": schema_records,
                    "outbound": outbound,
                    "inbound": inbound,
                },
                "gaps": gaps_by_subject.get(record["id"], []) + gaps_by_subject.get(name, []),
            }
        )

    system_metrics = [
        {k: row[k] for k in ("metric", "value", "determined", "note", "element_id")}
        for row in profile
        if row["element_kind"] == "system"
    ]

    functional = [s for s in services if s["in_graph"]]
    functional_ids = {s["id"] for s in functional}
    graph_edges = [
        {"source": d["source"], "target": d["target"], "kind": d["kind"]}
        for d in model["dependencies"]
        if d["source"] in functional_ids and d["target"] in functional_ids
    ]
    return {
        "name": system,
        "snapshot": commit,
        "short": short,
        "url": subject.get("url", ""),
        "branch": subject.get("branch", ""),
        "provenance": model.get("provenance", {}),
        "counts": {
            "services_total": len(services),
            "services_functional": len(functional),
            "services_infrastructure": len(services) - len(functional),
            "endpoints": len(model["endpoints"]),
            "entities": len(model.get("entities", [])),
            # Three different counts that a careless summary collapses into one.
            # `static` is what the analyser recovered from source: call sites in
            # Java. `configuration` is what docker-compose and the YAML declare,
            # which in PetClinic is mostly start ordering rather than calls.
            # `model` is every dependency element, infrastructure included.
            # `graph_edges` is the only one the metrics are computed over, and
            # it is the one that matters when reading AIS, ADS, DEG or BTW.
            "static_dependencies": len(static["declared_dependencies"]),
            "configuration_dependencies": len(config["declared_dependencies"]),
            "model_dependencies": len(model["dependencies"]),
            "graph_edges": len(graph_edges),
            "stores": len(model["stores"]),
            "evidence_gaps": len(model.get("evidence_gaps", [])),
            "snippets_unreadable": snippets.misses,
            "clone_available": snippets.available,
        },
        "graph": {"nodes": [s["id"] for s in functional], "edges": graph_edges},
        "system_metrics": system_metrics,
        "services": services,
        "gaps": model.get("evidence_gaps", []),
    }


def build_learning(data_root: str) -> dict:
    """Whatever models/build_dataset.py and train_baseline.py have produced."""
    tasks = []
    datasets_dir = os.path.join(data_root, "processed", "datasets")
    labels_path = os.path.join(data_root, "labels", "mutation", "labels.csv")
    if not os.path.isdir(datasets_dir):
        return {"available": False, "reason": "run models/build_dataset.py"}

    labels: list[dict] = []
    if os.path.exists(labels_path):
        with open(labels_path, encoding="utf-8") as handle:
            labels = list(csv.DictReader(handle))

    for filename in sorted(os.listdir(datasets_dir)):
        if not filename.endswith(".csv"):
            continue
        task = filename[:-4]
        with open(os.path.join(datasets_dir, filename), encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        features = [c for c in (rows[0] if rows else {}) if c not in
                    ("system", "variant", "element_id", "operator", "label")]
        task_labels = [row for row in labels if row["task"] == task]
        run_path = os.path.join(data_root, "processed", "predictions", task, "run.json")
        run = read_json(run_path) if os.path.exists(run_path) else None
        predictions = []
        if run:
            for fold in run["folds"]:
                path = os.path.join(ROOT, fold["predictions"])
                if os.path.exists(path):
                    records = read_json(path)
                    positives = [r for r in records if r["prediction"]["truth"] == 1]
                    predictions.append({"held_out_system": fold["held_out_system"],
                                        "examples": (positives or records)[:3]})
        tasks.append(
            {
                "task": task,
                "rows": len(rows),
                "positives": sum(1 for r in rows if r["label"] == "1"),
                "systems": sorted({r["system"] for r in rows}),
                "features": sorted(features),
                "variants": sorted({r["variant"] for r in rows}),
                "unverified_negatives": sum(1 for r in task_labels if r["note"].startswith("unverified")),
                "run": run,
                "prediction_examples": predictions,
            }
        )
    return {"available": True, "tasks": tasks}


def main() -> int:
    data_root = os.path.join(ROOT, "data")
    lock = read_json(ROOT, "subjects", "subjects.lock.json")

    metrics_content = read_json(HERE, "content", "metrics.json")
    rules_content = read_json(HERE, "content", "rules.json")
    references = read_json(HERE, "content", "references.json")["references"]

    documented = {m["id"] for m in metrics_content["metrics"]}
    missing = set(METRICS) - documented
    if missing:
        raise SystemExit(
            f"metrics without an entry in dashboard/content/metrics.json: {', '.join(sorted(missing))}"
        )
    stale = documented - set(METRICS)
    if stale:
        raise SystemExit(f"documented metrics that the catalogue no longer computes: {', '.join(sorted(stale))}")

    cited = {key for item in metrics_content["metrics"] + rules_content["rules"] for key in item["refs"]}
    dangling = cited - set(references)
    if dangling:
        raise SystemExit(f"citations with no reference entry: {', '.join(sorted(dangling))}")

    systems = []
    for subject in lock["subjects"]:
        profile = os.path.join(data_root, "processed", subject["name"], subject["commit"][:8], "metric_profile.csv")
        if not os.path.exists(profile):
            raise SystemExit(
                f"no profile for {subject['name']}: run `python run_pipeline.py --system {subject['name']}` first"
            )
        systems.append(build_system(subject, data_root))

    thresholds = Thresholds.load()
    document = {
        "meta": {
            "metamodel_version": METAMODEL_VERSION,
            "catalogue_version": CATALOGUE_VERSION,
            "threshold_set_version": thresholds.version,
            "trust_level": "T0",
            "generated_by": "dashboard/build_dashboard_data.py",
            "totals": {
                "systems": len(systems),
                "graph_edges": sum(s["counts"]["graph_edges"] for s in systems),
                "static_dependencies": sum(s["counts"]["static_dependencies"] for s in systems),
                "services": sum(s["counts"]["services_total"] for s in systems),
                "functional_services": sum(s["counts"]["services_functional"] for s in systems),
                "metrics_implemented": len(METRICS),
                "metrics_absent": len(metrics_content["absent"]),
                "evidence_gaps": sum(s["counts"]["evidence_gaps"] for s in systems),
            },
        },
        "catalogue": metrics_content,
        "rules": rules_content["rules"],
        "role_rules": read_role_rules(),
        "references": references,
        "thresholds": {
            "version": thresholds.version,
            "method": thresholds.method,
            "derived_from": [{"system": s, "snapshot": c} for s, c in thresholds.derived_from],
            "by_smell": {
                smell: {
                    metric: {"value": entry.value, "determined": entry.determined, "reason": entry.reason}
                    for metric, entry in entries.items()
                }
                for smell, entries in thresholds.by_smell.items()
            },
        },
        "systems": systems,
        "learning": build_learning(data_root),
    }

    out = os.path.join(HERE, "public", "dashboard.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    size = os.path.getsize(out) / 1024
    print(f"systems     {', '.join(s['name'] for s in systems)}")
    for system in systems:
        counts = system["counts"]
        clone = "" if counts["clone_available"] else "  (clone missing: snippets omitted)"
        print(
            f"  {system['name']:<12} {counts['services_functional']:>3} functional / "
            f"{counts['services_total']:<3} services  {counts['endpoints']:>3} endpoints  "
            f"{counts['entities']:>2} entities  {counts['graph_edges']:>2} graph edges  "
            f"{counts['evidence_gaps']:>2} gaps{clone}"
        )
    print(f"\nmetrics     {len(METRICS)} implemented, {len(metrics_content['absent'])} documented as absent")
    print(f"rules       {len(rules_content['rules'])} cards, {len(references)} references, 0 dangling citations")
    print(f"wrote       {os.path.relpath(out, ROOT)}  ({size:.0f} KB)")
    return 0


def read_role_rules() -> list[dict]:
    """The DD-002 classification rules, straight from the catalogue file."""
    import yaml

    with open(os.path.join(ROOT, "metamodel", "catalogue", "roles.yaml"), encoding="utf-8") as handle:
        catalogue = yaml.safe_load(handle)
    return [
        {
            "id": rule["id"],
            "role": rule["role"],
            "rationale": " ".join(rule["rationale"].split()),
            "condition": rule["when"],
        }
        for rule in catalogue["rules"]
    ] + [
        {
            "id": "default",
            "role": catalogue["default_role"],
            "rationale": "No rule matched. The default is functional, so a service is only "
                         "excluded from the graph when a rule says why.",
            "condition": None,
        }
    ]


if __name__ == "__main__":
    raise SystemExit(main())
