"""The architecture model — stage ② of the pipeline.

## What is deferred, and why the shape survives it

`docs/01-pipeline.md` specifies the ②→③ artifact as an Ecore instance in XMI.
This skeleton serialises to JSON instead. The data is shaped so that introducing
Ecore is a serialisation change, not a remodelling:

- Every element is a flat record with a single-valued `id` — the future
  `EAttribute id`, `ID = true`.
- The root `ArchitectureModel` owns each element type in one list. Those lists
  become containment `EReference`s with `containment = true`.
- Elements never nest one another. Every relationship between elements is an
  `id` string, which becomes a non-containment `EReference` and serialises to an
  XMI `href`/`#//@...` in exactly the same place.
- Collections are typed homogeneously and never polymorphic, because a
  heterogeneous list has no clean `EClass` to hang off.
- No element carries the snapshot. DD-001 forbids it in IDs, and the snapshot
  lives once, on the model instance.

What is genuinely deferred, and must be built before this is a thesis artifact:

1. The `.ecore` metamodel file and generated EMF classes.
2. OCL bodies for the metrics. `metrics/` currently holds Python reference
   implementations; `docs/03-metric-catalogue.md` requires an OCL definition
   before a metric counts as catalogued, and the Python is the reference
   implementation that the OCL is validated against, not a substitute for it.
3. XMI serialisation and metamodel-version validation of stored instances.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

METAMODEL_VERSION = "0.2.0-json"

FUNCTIONAL = "functional"
INFRASTRUCTURE = "infrastructure"

DECLARED = "declared"
OBSERVED = "observed"


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    role: str
    role_rule: str
    technology: str
    source_module: str | None
    has_source_module: bool


@dataclass(frozen=True)
class Endpoint:
    id: str
    service: str
    http_method: str
    route_template: str


@dataclass(frozen=True)
class Dependency:
    """A directed dependency edge.

    `provenance` is `declared` or `observed` and is never collapsed: an edge
    that exists in code but never fires at runtime, and an edge that fires but
    is not declared, are both findings. Two edges between the same pair with
    different provenance are two elements.
    """

    id: str
    source: str
    target: str
    kind: str
    provenance: str
    mechanisms: list[str]
    evidence: list[dict]


@dataclass(frozen=True)
class DomainEntity:
    """One persisted domain entity, and the table it maps to.

    Added in metamodel 0.2.0-json because `NOD` (`docs/03-metric-catalogue.md`
    group C) counts entities owned by a service, and the extractor was already
    producing the facts that stage (2) was dropping. An entity is attributed to
    exactly one service: the module that declares the type.
    """

    id: str
    service: str
    java_type: str
    table: str


@dataclass(frozen=True)
class Store:
    id: str
    name: str
    vendors: list[str]
    tables: list[str]


@dataclass(frozen=True)
class PersistenceLink:
    """Which service reaches which store, under which deployment vendor."""

    service: str
    store: str
    vendor: str
    access: str


@dataclass(frozen=True)
class DeploymentUnit:
    id: str
    service: str | None
    container: str
    image: str | None
    ports: list[str]


@dataclass(frozen=True)
class EvidenceGap:
    """Something the model could not determine, and why.

    Kept in the model rather than in a log, because a metric that cannot be
    computed for want of evidence must be able to say so instead of returning a
    number that looks like a finding.
    """

    subject: str
    concern: str
    reason: str


@dataclass
class ArchitectureModel:
    system: str
    snapshot: str
    metamodel_version: str = METAMODEL_VERSION
    provenance: dict = field(default_factory=dict)
    services: list[Service] = field(default_factory=list)
    endpoints: list[Endpoint] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    entities: list[DomainEntity] = field(default_factory=list)
    stores: list[Store] = field(default_factory=list)
    persistence_links: list[PersistenceLink] = field(default_factory=list)
    deployment_units: list[DeploymentUnit] = field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = field(default_factory=list)

    def service_by_name(self, name: str) -> Service | None:
        for service in self.services:
            if service.name == name:
                return service
        return None

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "snapshot": self.snapshot,
            "metamodel_version": self.metamodel_version,
            "provenance": self.provenance,
            "services": [asdict(s) for s in self.services],
            "endpoints": [asdict(e) for e in self.endpoints],
            "dependencies": [asdict(d) for d in self.dependencies],
            "entities": [asdict(e) for e in self.entities],
            "stores": [asdict(s) for s in self.stores],
            "persistence_links": [asdict(p) for p in self.persistence_links],
            "deployment_units": [asdict(d) for d in self.deployment_units],
            "evidence_gaps": [asdict(g) for g in self.evidence_gaps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchitectureModel":
        return cls(
            system=data["system"],
            snapshot=data["snapshot"],
            metamodel_version=data["metamodel_version"],
            provenance=data.get("provenance", {}),
            services=[Service(**s) for s in data["services"]],
            endpoints=[Endpoint(**e) for e in data["endpoints"]],
            dependencies=[Dependency(**d) for d in data["dependencies"]],
            entities=[DomainEntity(**e) for e in data.get("entities", [])],
            stores=[Store(**s) for s in data["stores"]],
            persistence_links=[PersistenceLink(**p) for p in data["persistence_links"]],
            deployment_units=[DeploymentUnit(**d) for d in data["deployment_units"]],
            evidence_gaps=[EvidenceGap(**g) for g in data.get("evidence_gaps", [])],
        )
