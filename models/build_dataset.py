#!/usr/bin/env python3
"""Generate the mutation-based supervision and the model-ready tables.

    ./.venv/bin/python models/build_dataset.py

For every pinned subject system this:

1. loads the stored architecture model (stage 2 output, never re-extracted),
2. applies every mutation operator in `aam4j_models.mutate`,
3. runs the metric catalogue over the base model and each mutant,
4. writes the labels the operators guarantee, and the joined dataset per task.

Nothing here is random, so the whole dataset is reproducible from the pinned
snapshots plus a catalogue version.

The negative class is where synthetic supervision usually goes wrong, so it is
built explicitly rather than by default:

- a service the operator damaged is a positive;
- a service that already exhibited the injected property in the *base* model is
  not emitted at all, because its label is genuinely unknown;
- everything else is a negative, and when the task has no deterministic
  detector to check the base against, the row says so in its `note` rather than
  passing as a verified negative.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for package_dir in ("metamodel", "metrics", "models"):
    sys.path.insert(0, os.path.join(ROOT, package_dir))

from aam4j_metrics.catalogue import compute_all  # noqa: E402
from aam4j_metrics.graph import build_graph  # noqa: E402
from aam4j_metrics.profile import to_rows, write_profile  # noqa: E402
from aam4j_model.model import FUNCTIONAL, ArchitectureModel  # noqa: E402
from aam4j_models.dataset import Label, assemble, write_dataset, write_labels  # noqa: E402
from aam4j_models.mutate import OVERSIZED_SERVICE, mutate_all  # noqa: E402

UNVERIFIED = "unverified negative: no deterministic detector exists for this task at this catalogue version"


def profile_for(model: ArchitectureModel) -> list[dict]:
    graph = build_graph(model)
    return to_rows(model, graph, compute_all(model, graph))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.path.join(ROOT, "data"))
    args = parser.parse_args()

    with open(os.path.join(ROOT, "subjects", "subjects.lock.json"), encoding="utf-8") as handle:
        lock = json.load(handle)

    profiles: dict[tuple[str, str], list[dict]] = {}
    labels: list[Label] = []
    generated = 0

    for subject in lock["subjects"]:
        system, commit = subject["name"], subject["commit"]
        model_path = os.path.join(args.data_root, "interim", system, commit[:8], "model.json")
        if not os.path.exists(model_path):
            print(f"missing model for {system}: run run_pipeline.py --system {system}", file=sys.stderr)
            return 1
        with open(model_path, encoding="utf-8") as handle:
            base = ArchitectureModel.from_dict(json.load(handle))

        profiles[(system, "base")] = profile_for(base)
        mutants = mutate_all(base)
        generated += len(mutants)
        tasks = sorted({mutant.task for mutant in mutants})
        functional = sorted(s.id for s in base.services if s.role == FUNCTIONAL)

        # Base rows: negatives for every task, minus whatever the base already has.
        for task in tasks:
            already = {
                element
                for mutant in mutants
                if mutant.task == task
                for element in mutant.already_positive_in_base
            }
            for element in functional:
                if element in already:
                    continue
                labels.append(
                    Label(
                        system=system,
                        snapshot=commit,
                        variant="base",
                        element_id=element,
                        task=task,
                        label=0,
                        label_provenance="by-construction",
                        operator="none",
                        note=UNVERIFIED if task == OVERSIZED_SERVICE else "",
                    )
                )

        for mutant in mutants:
            variant_dir = os.path.join(args.data_root, "processed", "mutants", system, commit[:8], mutant.variant)
            rows = profile_for(mutant.model)
            write_profile(rows, os.path.join(variant_dir, "metric_profile.csv"))
            profiles[(system, mutant.variant)] = rows

            implicated = set(mutant.implicated)
            already = set(mutant.already_positive_in_base)
            present = sorted(s.id for s in mutant.model.services if s.role == FUNCTIONAL)
            for element in present:
                if element in implicated:
                    label, note = 1, mutant.description
                elif element in already:
                    continue
                else:
                    label = 0
                    note = UNVERIFIED if mutant.task == OVERSIZED_SERVICE else ""
                labels.append(
                    Label(
                        system=system,
                        snapshot=commit,
                        variant=mutant.variant,
                        element_id=element,
                        task=mutant.task,
                        label=label,
                        label_provenance="by-construction",
                        operator=mutant.operator,
                        note=note,
                    )
                )

    label_path = write_labels(labels, os.path.join(args.data_root, "labels", "mutation", "labels.csv"))
    print(f"{generated} mutants over {len(lock['subjects'])} systems, {len(labels)} labelled rows")
    print(f"wrote {os.path.relpath(label_path, ROOT)}\n")

    for task in sorted({label.task for label in labels}):
        dataset = assemble(profiles, labels, task)
        path = write_dataset(dataset, os.path.join(args.data_root, "processed", "datasets", f"{task}.csv"))
        positives = dataset.positives()
        print(
            f"  {task:<20} n={len(dataset.rows):<5} positives={positives:<4} "
            f"features={len(dataset.feature_names)}  excluded={','.join(dataset.excluded)}"
        )
        print(f"  {'':<20} systems={','.join(dataset.systems)}  -> {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
