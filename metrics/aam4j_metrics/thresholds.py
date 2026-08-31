"""Thresholds for the smell predicates of `docs/03-metric-catalogue.md` group E.

The catalogue says, in as many words, that thresholds are the weak point of the
smell group and that reviewers will go straight at them. Three consequences are
enforced here rather than left to discipline:

1. **Thresholds are catalogue data, not literals in code.** They live in
   `metrics/catalogue/thresholds.json`, are versioned, and every profile row
   already carries `catalogue_version`.
2. **They are derived, and the derivation travels with them.** The file records
   the method and the exact (system, snapshot) pairs the distribution came from,
   so the number can be recomputed by `metrics/derive_thresholds.py`.
3. **A degenerate distribution yields no threshold.** If the chosen quantile of
   a metric equals its minimum, thresholding on it separates nothing, and the
   file stores `null` plus the reason. A predicate that needs that threshold
   reports *undetermined*, never a verdict. This is the same rule `SHARED_DB`
   already follows: missing evidence must not read as a clean bill of health.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue", "thresholds.json")

UNSET = "unset"


@dataclass(frozen=True)
class Threshold:
    value: float | None
    reason: str = ""

    @property
    def determined(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class Thresholds:
    version: str
    method: str
    derived_from: tuple[tuple[str, str], ...]
    by_smell: dict[str, dict[str, Threshold]]

    @classmethod
    def load(cls, path: str | None = None) -> "Thresholds":
        path = path or DEFAULT_PATH
        if not os.path.exists(path):
            return cls(version=UNSET, method="", derived_from=(), by_smell={})
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        by_smell = {
            smell: {
                metric: Threshold(entry.get("value"), entry.get("reason", ""))
                for metric, entry in metrics.items()
            }
            for smell, metrics in data.get("thresholds", {}).items()
        }
        return cls(
            version=data.get("version", UNSET),
            method=data.get("method", ""),
            derived_from=tuple((d["system"], d["snapshot"]) for d in data.get("derived_from", [])),
            by_smell=by_smell,
        )

    def resolve(self, smell: str, required: tuple[str, ...]) -> tuple[dict[str, float] | None, str]:
        """`(thresholds, reason)`. `None` with a reason if the smell cannot fire.

        All-or-nothing on purpose: a conjunctive predicate evaluated with two of
        its three thresholds is a different predicate, and would quietly fire
        more often than the one in the catalogue.
        """
        if self.version == UNSET:
            return None, "no threshold set configured (run metrics/derive_thresholds.py)"
        entries = self.by_smell.get(smell)
        if not entries:
            return None, f"threshold set {self.version} defines no thresholds for {smell}"
        missing = []
        resolved: dict[str, float] = {}
        for metric in required:
            entry = entries.get(metric)
            if entry is None or not entry.determined:
                missing.append(f"{metric} ({entry.reason if entry else 'absent from the threshold set'})")
            else:
                resolved[metric] = float(entry.value)
        if missing:
            return None, "undetermined threshold(s): " + "; ".join(missing)
        return resolved, ""
