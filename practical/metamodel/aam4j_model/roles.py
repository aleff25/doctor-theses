"""DD-002 role classification.

`role in {functional, infrastructure}` is a property of the model, not an
extractor convenience, so it is assigned here at model-build time — after the
extractor has recorded everything without filtering.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import yaml

CATALOGUE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalogue", "roles.yaml")


@dataclass(frozen=True)
class RoleEvidence:
    """Everything a rule may test about one candidate service."""

    name: str
    has_source_module: bool
    maven_dependencies: frozenset[str]
    type_annotations: frozenset[str]
    declares_gateway_routes: bool


@dataclass(frozen=True)
class RoleAssignment:
    role: str
    rule_id: str


class RoleCatalogue:
    def __init__(self, data: dict):
        self.version = str(data.get("version", "0"))
        self.default_role = data.get("default_role", "functional")
        self.rules = data.get("rules") or []
        self.overrides = data.get("overrides") or {}

    @classmethod
    def load(cls, path: str = CATALOGUE_PATH) -> "RoleCatalogue":
        with open(path, encoding="utf-8") as handle:
            return cls(yaml.safe_load(handle))

    def _matches(self, condition: dict, evidence: RoleEvidence) -> bool:
        if "all_of" in condition:
            return all(self._matches(c, evidence) for c in condition["all_of"])
        if "any_of" in condition:
            return any(self._matches(c, evidence) for c in condition["any_of"])
        for key, expected in condition.items():
            if key == "type_annotation":
                if expected not in evidence.type_annotations:
                    return False
            elif key == "maven_dependency":
                if expected not in evidence.maven_dependencies:
                    return False
            elif key == "maven_dependency_prefix":
                if not any(d.startswith(expected) for d in evidence.maven_dependencies):
                    return False
            elif key == "declares_gateway_routes":
                if evidence.declares_gateway_routes is not expected:
                    return False
            elif key == "has_source_module":
                if evidence.has_source_module is not expected:
                    return False
            else:
                raise ValueError(f"unknown role-rule predicate: {key!r}")
        return True

    def classify(self, evidence: RoleEvidence) -> RoleAssignment:
        if evidence.name in self.overrides:
            return RoleAssignment(self.overrides[evidence.name], f"override:{evidence.name}")
        for rule in self.rules:
            if self._matches(rule["when"], evidence):
                return RoleAssignment(rule["role"], rule["id"])
        return RoleAssignment(self.default_role, "default")
