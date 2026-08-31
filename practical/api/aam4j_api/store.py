"""Read access to what the pipeline wrote under `data/`.

The API reads artifacts; it never recomputes them. Two reasons, both from
`docs/01-pipeline.md`:

- A served number and a stored number that can disagree is a reproducibility
  hole. Serving straight from `data/processed/` means what a developer sees is
  exactly the row that was written, versions and all.
- Recomputation would put the metric catalogue behind an HTTP boundary, and
  the pipeline stages have to stay usable without a server running.

Snapshots are addressed by their full commit SHA and resolved through
`subjects/subjects.lock.json`, so an unpinned directory that appeared under
`data/` by accident cannot be served as if it were the subject system.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass

TRUST_LEVEL = "T0"


class NotFound(LookupError):
    """Requested system, snapshot or element is not in the store."""


@dataclass(frozen=True)
class SnapshotRef:
    system: str
    commit: str
    branch: str
    url: str

    @property
    def short(self) -> str:
        return self.commit[:8]


class ProfileStore:
    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        self.data_root = os.path.join(self.root, "data")
        self.lock_path = os.path.join(self.root, "subjects", "subjects.lock.json")

    # -- pinned subjects ---------------------------------------------------
    def pinned(self) -> list[SnapshotRef]:
        with open(self.lock_path, encoding="utf-8") as handle:
            lock = json.load(handle)
        return [
            SnapshotRef(s["name"], s["commit"], s.get("branch", ""), s.get("url", ""))
            for s in lock["subjects"]
        ]

    def resolve(self, system: str, snapshot: str | None = None) -> SnapshotRef:
        """The pinned snapshot of `system`, or the one whose SHA `snapshot` prefixes."""
        candidates = [ref for ref in self.pinned() if ref.system == system]
        if not candidates:
            known = ", ".join(sorted({ref.system for ref in self.pinned()}))
            raise NotFound(f"unknown system {system!r}; pinned systems are: {known}")
        if snapshot is None:
            return candidates[0]
        for ref in candidates:
            if ref.commit.startswith(snapshot):
                return ref
        raise NotFound(f"{system!r} has no pinned snapshot matching {snapshot!r}")

    # -- artifacts ---------------------------------------------------------
    def _profile_path(self, ref: SnapshotRef) -> str:
        return os.path.join(self.data_root, "processed", ref.system, ref.short, "metric_profile.csv")

    def _model_path(self, ref: SnapshotRef) -> str:
        return os.path.join(self.data_root, "interim", ref.system, ref.short, "model.json")

    def has_artifacts(self, ref: SnapshotRef) -> bool:
        return os.path.exists(self._profile_path(ref)) and os.path.exists(self._model_path(ref))

    def _require(self, ref: SnapshotRef, path: str) -> str:
        if not os.path.exists(path):
            raise NotFound(
                f"no artifact for {ref.system}@{ref.short}: run "
                f"`python run_pipeline.py --system {ref.system}` first"
            )
        return path

    def profile(self, ref: SnapshotRef) -> list[dict]:
        path = self._require(ref, self._profile_path(ref))
        with open(path, encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return [self._typed(row) for row in rows]

    def model(self, ref: SnapshotRef) -> dict:
        path = self._require(ref, self._model_path(ref))
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _typed(row: dict) -> dict:
        """CSV is all strings; the wire format is not.

        `determined` and `value` travel together: an undetermined row carries
        `value: null` and its `note`, never a zero. Every consumer of this API
        is therefore forced to handle "no evidence" as a distinct case.
        """
        determined = row["determined"] == "true"
        return {
            "system": row["system"],
            "snapshot": row["snapshot"],
            "element_id": row["element_id"],
            "element_kind": row["element_kind"],
            "metric": row["metric"],
            "value": float(row["value"]) if determined and row["value"] != "" else None,
            "determined": determined,
            "note": row["note"],
            "metamodel_version": row["metamodel_version"],
            "catalogue_version": row["catalogue_version"],
            "graph_scope": row["graph_scope"],
        }
