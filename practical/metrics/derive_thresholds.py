#!/usr/bin/env python3
"""Derive the group-E smell thresholds from the subject-system distributions.

    ./.venv/bin/python metrics/derive_thresholds.py [--quantile 0.9]

`docs/03-metric-catalogue.md`: "Derive the thresholds empirically from the
distribution across the three subject systems, state the derivation method in
the thesis, and treat the thresholds as a versioned part of the catalogue rather
than as magic numbers in code." This script is that derivation, and its output
(`metrics/catalogue/thresholds.json`) is that versioned part.

Method: nearest-rank quantile over the pooled values of the metric across the
functional services of every pinned subject system. Nearest-rank rather than an
interpolating quantile because the inputs are counts, and a threshold of 2.4
endpoints is not a quantity any service can have.

Refusal rule: if the quantile equals the minimum observed value, the metric does
not separate the population and no threshold is emitted. The reason is stored in
its place, and any predicate needing it reports undetermined. This fires today
on `AIS`, and the reason is a finding about the extractor, not about the systems
(see the note the run prints).

Determinism: the output carries no timestamp and no absolute path, so re-running
on the same profiles produces a byte-identical file.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

THRESHOLD_SET_VERSION = "0.1.0"
SMELLS = {"GOD": ("AIS", "NOE", "NOD")}


def nearest_rank(values: list[float], quantile: float) -> float:
    """The smallest observed value at or above `quantile` of the population."""
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(-(-quantile * len(ordered) // 1))))
    return ordered[rank - 1]


def pooled(profiles: list[tuple[str, str, str]], metric: str) -> list[float]:
    values: list[float] = []
    for _, _, path in profiles:
        with open(path, encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["metric"] == metric and row["element_kind"] == "service" and row["determined"] == "true":
                    values.append(float(row["value"]))
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quantile", type=float, default=0.9)
    parser.add_argument("--data-root", default=os.path.join(ROOT, "data"))
    parser.add_argument("--out", default=os.path.join(HERE, "catalogue", "thresholds.json"))
    args = parser.parse_args()

    with open(os.path.join(ROOT, "subjects", "subjects.lock.json"), encoding="utf-8") as handle:
        lock = json.load(handle)

    profiles: list[tuple[str, str, str]] = []
    for subject in lock["subjects"]:
        path = os.path.join(
            args.data_root, "processed", subject["name"], subject["commit"][:8], "metric_profile.csv"
        )
        if not os.path.exists(path):
            print(f"missing profile for {subject['name']}: run run_pipeline.py first", file=sys.stderr)
            return 1
        profiles.append((subject["name"], subject["commit"], path))

    method = (
        f"nearest-rank q={args.quantile:g} over functional services, "
        "pooled across all pinned subject systems"
    )
    thresholds: dict[str, dict[str, dict]] = {}
    for smell, metrics in SMELLS.items():
        thresholds[smell] = {}
        for metric in metrics:
            values = pooled(profiles, metric)
            if not values:
                thresholds[smell][metric] = {
                    "value": None,
                    "reason": "no determined values in any subject system",
                }
                continue
            cut = nearest_rank(values, args.quantile)
            if cut <= min(values):
                thresholds[smell][metric] = {
                    "value": None,
                    "reason": (
                        f"degenerate distribution: q={args.quantile:g} equals the minimum "
                        f"({cut:g}) over n={len(values)}, so the metric separates nothing"
                    ),
                }
            else:
                thresholds[smell][metric] = {
                    "value": cut,
                    "n": len(values),
                    "min": min(values),
                    "max": max(values),
                }

    document = {
        "version": THRESHOLD_SET_VERSION,
        "method": method,
        "derived_from": [{"system": name, "snapshot": commit} for name, commit, _ in profiles],
        "thresholds": thresholds,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"threshold set {THRESHOLD_SET_VERSION}  {method}")
    for smell, metrics in thresholds.items():
        for metric, entry in sorted(metrics.items()):
            if entry["value"] is None:
                print(f"  {smell}.{metric:<4} REFUSED  {entry['reason']}")
            else:
                print(
                    f"  {smell}.{metric:<4} {entry['value']:g}  "
                    f"(n={entry['n']}, range {entry['min']:g}..{entry['max']:g})"
                )
    print(f"\nwrote {os.path.relpath(args.out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
