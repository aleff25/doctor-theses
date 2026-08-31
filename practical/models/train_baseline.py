#!/usr/bin/env python3
"""The first interpretable-by-design baseline, evaluated leave-one-system-out.

    ./.venv/bin/python models/train_baseline.py --task oversized-service

Family: L2-regularised logistic regression over standardised metric features.
`models/README.md` names it first among the interpretable families, and it is
the right starting point for a different reason too: its attribution is exact.
The contribution of a feature to a decision is `coef_j * z_j`, not an estimate
of it, so the stage 4 -> 5 contract can be satisfied without SHAP, sampling, or
any approximation whose error would have to be reported separately.

What this script deliberately does *not* do:

- It does not report a single headline accuracy. Every fold is printed, with
  its positive count, because on this dataset most folds have almost none and
  an average across them would be meaningless.
- It does not silently skip a fold it cannot score. A fold whose held-out
  system contains no positive example yields undetermined ROC-AUC, and says so.
- It does not compare against nothing. The majority-class rate is printed
  beside every fold, since on a dataset this imbalanced a model can look
  excellent while learning nothing.

Output: one prediction record per held-out element, in the JSON shape the
pipeline's 4 -> 5 contract specifies (`prediction`, `attributions[]`, each
attribution naming a metric and an `element_id`), plus a run record carrying
every version and the feature exclusions the task was trained under.
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

from aam4j_metrics.catalogue import CATALOGUE_VERSION  # noqa: E402
from aam4j_model.model import METAMODEL_VERSION  # noqa: E402
from aam4j_models.dataset import assemble, leave_one_system_out, materialise, read_labels  # noqa: E402

MODEL_VERSION = "logreg-l2/0.1.0"


def load_profiles(data_root: str) -> dict[tuple[str, str], list[dict]]:
    import csv

    profiles: dict[tuple[str, str], list[dict]] = {}
    with open(os.path.join(ROOT, "subjects", "subjects.lock.json"), encoding="utf-8") as handle:
        lock = json.load(handle)
    for subject in lock["subjects"]:
        system, short = subject["name"], subject["commit"][:8]
        base = os.path.join(data_root, "processed", system, short, "metric_profile.csv")
        if os.path.exists(base):
            with open(base, encoding="utf-8") as handle:
                profiles[(system, "base")] = list(csv.DictReader(handle))
        mutant_root = os.path.join(data_root, "processed", "mutants", system, short)
        if not os.path.isdir(mutant_root):
            continue
        for variant in sorted(os.listdir(mutant_root)):
            path = os.path.join(mutant_root, variant, "metric_profile.csv")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as handle:
                    profiles[(system, variant)] = list(csv.DictReader(handle))
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="oversized-service")
    parser.add_argument("--data-root", default=os.path.join(ROOT, "data"))
    parser.add_argument("--C", type=float, default=1.0, help="inverse L2 strength")
    args = parser.parse_args()

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("install the learn extra:  pip install -e '.[learn]'", file=sys.stderr)
        return 1

    labels = read_labels(os.path.join(args.data_root, "labels", "mutation", "labels.csv"))
    dataset = assemble(load_profiles(args.data_root), labels, args.task)
    if not dataset.rows:
        print(f"no rows for task {args.task!r}: run models/build_dataset.py first", file=sys.stderr)
        return 1

    folds = leave_one_system_out(dataset)
    print(f"task            {args.task}")
    print(f"rows            {len(dataset.rows)}  positives {dataset.positives()}")
    print(f"systems         {', '.join(dataset.systems)}")
    print(f"features        {len(dataset.feature_names)} + undetermined indicators")
    print(f"excluded        {', '.join(dataset.excluded)}  (would make the task circular)")
    if not folds:
        print(
            "\nno leave-one-system-out fold is possible: this task has labels for one system only.\n"
            "That is a finding about the label source, not a reason to switch to a random split.",
            file=sys.stderr,
        )
        return 2

    run = {
        "model_version": MODEL_VERSION,
        "metamodel_version": METAMODEL_VERSION,
        "catalogue_version": CATALOGUE_VERSION,
        "task": args.task,
        "split": "leave-one-system-out",
        "excluded_features": list(dataset.excluded),
        "hyperparameters": {"penalty": "l2", "C": args.C, "class_weight": "balanced"},
        "folds": [],
    }
    out_dir = os.path.join(args.data_root, "processed", "predictions", args.task)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'held-out system':<16}{'n':>5}{'pos':>5}{'majority':>10}{'recall':>9}{'precision':>11}{'roc_auc':>9}")
    for system, train, test in folds:
        data = materialise(dataset, train, test)
        scaler = StandardScaler().fit(data["x_train"])
        model = LogisticRegression(C=args.C, class_weight="balanced", max_iter=2000)
        model.fit(scaler.transform(data["x_train"]), data["y_train"])

        z_test = scaler.transform(data["x_test"])
        probabilities = model.predict_proba(z_test)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)
        truth = data["y_test"]

        positives = sum(truth)
        true_positive = sum(1 for p, t in zip(predictions, truth) if p == 1 and t == 1)
        predicted_positive = int(sum(predictions))
        recall = true_positive / positives if positives else None
        precision = true_positive / predicted_positive if predicted_positive else None
        majority = max(sum(truth), len(truth) - sum(truth)) / len(truth)
        auc = roc_auc_score(truth, probabilities) if 0 < positives < len(truth) else None

        def show(value, fmt="{:.2f}"):
            return "n/d" if value is None else fmt.format(value)

        print(
            f"{system:<16}{len(truth):>5}{positives:>5}{majority:>10.2f}"
            f"{show(recall):>9}{show(precision):>11}{show(auc):>9}"
        )

        records = []
        for index, element in enumerate(data["test_elements"]):
            contributions = [
                {
                    "metric": name.replace("__undetermined", ""),
                    "feature": name,
                    "element_id": element,
                    "contribution": float(coefficient * z_test[index][column]),
                    "kind": "evidence-missing" if name.endswith("__undetermined") else "metric-value",
                }
                for column, (name, coefficient) in enumerate(zip(data["columns"], model.coef_[0]))
            ]
            contributions.sort(key=lambda c: -abs(c["contribution"]))
            records.append(
                {
                    "element_id": element,
                    "task": args.task,
                    "prediction": {
                        "label": int(predictions[index]),
                        "score": float(probabilities[index]),
                        "truth": truth[index],
                    },
                    "attributions": [c for c in contributions if abs(c["contribution"]) > 1e-9][:5],
                    "model_version": MODEL_VERSION,
                    "catalogue_version": CATALOGUE_VERSION,
                    "held_out_system": system,
                }
            )
        path = os.path.join(out_dir, f"loso-{system}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2, sort_keys=True)
            handle.write("\n")

        run["folds"].append(
            {
                "held_out_system": system,
                "n": len(truth),
                "positives": positives,
                "majority_rate": majority,
                "recall": recall,
                "precision": precision,
                "roc_auc": auc,
                "predictions": os.path.relpath(path, ROOT),
            }
        )

    run_path = os.path.join(out_dir, "run.json")
    with open(run_path, "w", encoding="utf-8") as handle:
        json.dump(run, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"\nwrote {os.path.relpath(run_path, ROOT)} and one prediction record file per fold")
    print(
        "\nRead these numbers as a wiring test, not as evidence about real systems: the labels are\n"
        "synthetic by construction (docs/05), so they show whether the metrics respond to an\n"
        "injected architectural change, not whether they predict real-world quality outcomes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
