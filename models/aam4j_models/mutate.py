"""Architectural mutation: labelled data by construction.

`docs/05-labels-and-datasets.md` lists four possible label sources and is blunt
about the first three: the subject systems' git histories are not defect
histories, Train Ticket's fault-injection labels have to be re-verified against
`refactor/v2`, and TeaStore's performance labels cost experiment time to
produce. The fourth source is the one that can start today:

    "deliberately mutate a subject system's architecture (merge two services,
    add a shared database, introduce a cycle) and label the mutants by
    construction ... which is, arguably, a cleaner test of RQ2 than any
    prediction task."

That is what this module does. A mutation operator takes an architecture model
and returns a new one plus the elements it damaged, so the label is not
inferred, measured or mined: it is a record of what was done.

## The threat this design has to keep visible

Mutants are not drawn from the same distribution as real architectural decay.
Results transfer to "does the metric detect this property", not to "does this
predict real-world failure". `docs/05` requires that sentence in threats to
validity, and `dataset.py` refuses to let the stronger claim be made
accidentally by excluding, per task, the deterministic detector of the very
property that was injected (see `EXCLUDED_FEATURES` there). Without that guard,
a classifier predicting `cycle` from a feature set containing `CYC` would score
perfectly and mean nothing.

## Determinism

Operators pick their targets by sorted element ID, never at random. The same
base model always yields the same mutants, so the dataset is reproducible from
the pinned snapshot alone.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from aam4j_model import ids
from aam4j_model.model import FUNCTIONAL, ArchitectureModel, Dependency, PersistenceLink

#: Task name -> the architectural property the operator injects.
CYCLE = "cycle"
SHARED_PERSISTENCE = "shared-persistence"
OVERSIZED_SERVICE = "oversized-service"


@dataclass(frozen=True)
class Mutant:
    """One mutated model, and the labels its construction guarantees.

    `implicated` are the services the operator damaged directly: label 1.
    Every other functional service is a candidate negative, but only if the
    *base* model did not already exhibit the property, because otherwise the label
    would be wrong and the row is dropped by `dataset.py` rather than guessed.
    """

    variant: str
    operator: str
    task: str
    model: ArchitectureModel
    implicated: tuple[str, ...]
    description: str
    already_positive_in_base: tuple[str, ...] = field(default=())


def _functional(model: ArchitectureModel) -> list[str]:
    return sorted(s.id for s in model.services if s.role == FUNCTIONAL)


def _name(element_id: str) -> str:
    return element_id.split("/")[-1]


def introduce_cycle(model: ArchitectureModel) -> list[Mutant]:
    """Reverse an existing declared edge, creating a two-service cycle.

    Reversal rather than a fresh edge between arbitrary services: the pair
    already communicates, so the mutant stays a system someone could plausibly
    have written, which is the weakest point of synthetic supervision.
    """
    functional = set(_functional(model))
    existing = {
        (d.source, d.target)
        for d in model.dependencies
        if d.source in functional and d.target in functional
    }
    mutants: list[Mutant] = []
    for index, (source, target) in enumerate(sorted(existing)):
        if (target, source) in existing:
            continue  # already cyclic in the base
        mutated = copy.deepcopy(model)
        mutated.dependencies.append(
            Dependency(
                id=ids.edge_id(model.system, _name(target), _name(source), "sync"),
                source=target,
                target=source,
                kind="sync",
                provenance="declared",
                mechanisms=["mutation"],
                evidence=[{"evidence_class": "mutation", "operator": "introduce_cycle"}],
            )
        )
        mutated.dependencies.sort(key=lambda d: d.id)
        base_cyclic = tuple(sorted(node for node in functional if (node, node) in existing))
        mutants.append(
            Mutant(
                variant=f"cycle-{index:02d}",
                operator="introduce_cycle",
                task=CYCLE,
                model=mutated,
                implicated=(source, target),
                description=f"added {_name(target)} -> {_name(source)}, closing a cycle",
                already_positive_in_base=base_cyclic,
            )
        )
    return mutants


def share_database(model: ArchitectureModel) -> list[Mutant]:
    """Point a service with no store at another service's store.

    The mutant is the textbook shared-persistence coupling: two services now
    read and write the same tables, and neither one's code changed.
    """
    functional = set(_functional(model))
    links = [link for link in model.persistence_links if link.service in functional]
    if not links:
        return []
    owners = {link.service for link in links}
    by_store: dict[tuple[str, str], set[str]] = {}
    for link in links:
        by_store.setdefault((link.store, link.vendor), set()).add(link.service)
    already = tuple(sorted({s for services in by_store.values() if len(services) > 1 for s in services}))

    candidates = sorted(functional - owners)
    mutants: list[Mutant] = []
    for index, borrower in enumerate(candidates):
        store, vendor = sorted(by_store)[0]
        lender = sorted(by_store[(store, vendor)])[0]
        mutated = copy.deepcopy(model)
        mutated.persistence_links.append(
            PersistenceLink(service=borrower, store=store, vendor=vendor, access="reads-tables")
        )
        mutated.persistence_links.sort(key=lambda p: (p.vendor, p.service, p.store))
        mutants.append(
            Mutant(
                variant=f"shared-db-{index:02d}",
                operator="share_database",
                task=SHARED_PERSISTENCE,
                model=mutated,
                implicated=(borrower, lender),
                description=f"{_name(borrower)} now reads {_name(store)}, owned by {_name(lender)}",
                already_positive_in_base=already,
            )
        )
    return mutants


def merge_services(model: ArchitectureModel, keep_top: int = 3) -> list[Mutant]:
    """Absorb one service into another: endpoints, entities, stores and edges.

    The absorbing service gains the merged service's responsibilities without
    gaining any of its own structure, which is precisely the granularity defect
    `NOE`, `NOD` and the god-service predicate are supposed to see.

    `keep_top` bounds the number of mutants to the largest absorbers by
    endpoint count, so a 30-service system does not generate 900 variants that
    all say the same thing.
    """
    functional = _functional(model)
    if len(functional) < 2:
        return []
    endpoints_by_service: dict[str, int] = {service: 0 for service in functional}
    for endpoint in model.endpoints:
        if endpoint.service in endpoints_by_service:
            endpoints_by_service[endpoint.service] += 1
    ranked = sorted(functional, key=lambda s: (-endpoints_by_service[s], s))

    mutants: list[Mutant] = []
    for index, absorber in enumerate(ranked[:keep_top]):
        victim = next(s for s in ranked if s != absorber)
        mutated = copy.deepcopy(model)
        mutated.services = [s for s in mutated.services if s.id != victim]
        mutated.endpoints = [
            type(e)(id=e.id, service=absorber if e.service == victim else e.service,
                    http_method=e.http_method, route_template=e.route_template)
            for e in mutated.endpoints
        ]
        mutated.entities = [
            type(e)(id=e.id, service=absorber if e.service == victim else e.service,
                    java_type=e.java_type, table=e.table)
            for e in mutated.entities
        ]
        mutated.persistence_links = [
            PersistenceLink(absorber if p.service == victim else p.service, p.store, p.vendor, p.access)
            for p in mutated.persistence_links
        ]
        rewired = []
        for dependency in mutated.dependencies:
            source = absorber if dependency.source == victim else dependency.source
            target = absorber if dependency.target == victim else dependency.target
            if source == target:
                continue  # an edge internal to the merged service is no longer a dependency
            rewired.append(
                type(dependency)(
                    id=ids.edge_id(model.system, _name(source), _name(target), dependency.kind),
                    source=source,
                    target=target,
                    kind=dependency.kind,
                    provenance=dependency.provenance,
                    mechanisms=dependency.mechanisms,
                    evidence=dependency.evidence,
                )
            )
        mutated.dependencies = sorted({d.id: d for d in rewired}.values(), key=lambda d: d.id)
        mutants.append(
            Mutant(
                variant=f"merge-{index:02d}",
                operator="merge_services",
                task=OVERSIZED_SERVICE,
                model=mutated,
                implicated=(absorber,),
                description=f"{_name(victim)} absorbed into {_name(absorber)}",
            )
        )
    return mutants


OPERATORS = (introduce_cycle, share_database, merge_services)


def mutate_all(model: ArchitectureModel) -> list[Mutant]:
    mutants: list[Mutant] = []
    for operator in OPERATORS:
        mutants.extend(operator(model))
    return mutants
