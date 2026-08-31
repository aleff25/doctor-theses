"""Reference implementations of the four skeleton metrics.

`AIS`, `ADS`, `NOE` (`docs/03-metric-catalogue.md` groups A and C) and the
`SHARED_DB` smell predicate (group E).

Each returns `MetricValue` records rather than bare numbers, because a metric
that could not be computed must be able to say *undetermined* instead of
returning `0`. `SHARED_DB` needs this: on a snapshot with no store identity in
it, `0` would read as "no shared database" when the truth is "no evidence".

Every metric is stamped with `CATALOGUE_VERSION`, per constraint 4 of
`docs/01-pipeline.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

from aam4j_model import ids
from aam4j_model.model import FUNCTIONAL, ArchitectureModel

from . import graph as graph_ops
from .graph import ServiceGraph
from .thresholds import Thresholds

CATALOGUE_VERSION = "0.2.0"


@dataclass(frozen=True)
class MetricValue:
    element_id: str
    element_kind: str
    metric: str
    value: float | None
    determined: bool = True
    note: str = ""


def ais(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Absolute Importance of a Service — in-degree over `G`.

    `AIS(s) = |{t : (t,s) in D}|`
    """
    return [
        MetricValue(node, "service", "AIS", float(graph.in_degree(node)))
        for node in graph.nodes
    ]


def ads(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Absolute Dependence of a Service — out-degree over `G`.

    `ADS(s) = |{t : (s,t) in D}|`
    """
    return [
        MetricValue(node, "service", "ADS", float(graph.out_degree(node)))
        for node in graph.nodes
    ]


def noe(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Number of endpoints — `NOE(s) = |E(s)|`.

    Counted over endpoint *elements*, so two HTTP methods on one route are two
    endpoints (DD-001 puts the method in the endpoint ID). That is the reading
    the identity scheme forces; `docs/03-metric-catalogue.md` does not say
    either way.
    """
    counts = {node: 0 for node in graph.nodes}
    for endpoint in model.endpoints:
        if endpoint.service in counts:
            counts[endpoint.service] += 1
    return [MetricValue(node, "service", "NOE", float(counts[node])) for node in graph.nodes]


def shared_db(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Shared persistence — `exists p in P(s1) ∩ P(s2), s1 != s2`.

    Emitted per service as 1/0: does this service share any store with another
    service in `G`? Store sharing is evaluated within a vendor, since two
    vendors' DDL are alternative deployments of the same service rather than
    two live stores.

    A service whose store identity could not be resolved from the snapshot gets
    `determined = False` and no value, carrying the reason from the model's
    evidence gaps. Reporting `0` there would turn missing evidence into a
    clean bill of health.
    """
    by_vendor: dict[str, dict[str, set[str]]] = {}
    for link in model.persistence_links:
        if link.service not in graph.nodes:
            continue
        by_vendor.setdefault(link.vendor, {}).setdefault(link.store, set()).add(link.service)

    shared_services: dict[str, set[str]] = {}
    for vendor, stores in by_vendor.items():
        for store, services in stores.items():
            if len(services) > 1:
                for service in services:
                    shared_services.setdefault(service, set()).add(f"{store}@{vendor}")

    resolved = {link.service for link in model.persistence_links if link.service in graph.nodes}
    gaps: dict[str, list[str]] = {}
    for gap in model.evidence_gaps:
        if gap.concern.startswith("store-identity:"):
            gaps.setdefault(gap.subject, []).append(gap.concern.split(":", 1)[1])

    values: list[MetricValue] = []
    for node in graph.nodes:
        if node in shared_services:
            values.append(
                MetricValue(
                    node,
                    "service",
                    "SHARED_DB",
                    1.0,
                    note="shares " + ", ".join(sorted(shared_services[node])),
                )
            )
        elif node in resolved:
            values.append(MetricValue(node, "service", "SHARED_DB", 0.0))
        elif node in gaps:
            values.append(
                MetricValue(
                    node,
                    "service",
                    "SHARED_DB",
                    None,
                    determined=False,
                    note="store identity unresolved for vendor(s): " + ", ".join(sorted(gaps[node])),
                )
            )
        else:
            values.append(
                MetricValue(node, "service", "SHARED_DB", 0.0, note="declares no persistent store")
            )
    return values


def acs(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Absolute Criticality of a Service: `ACS(s) = AIS(s) x ADS(s)`.

    Derived, so it inherits every property of its inputs: it is zero for a
    service that is only called and never calls, which is the intended reading
    (criticality here means *on a path*, not *important*).
    """
    return [
        MetricValue(
            node,
            "service",
            "ACS",
            float(graph.in_degree(node) * graph.out_degree(node)),
        )
        for node in graph.nodes
    ]


def scf(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Service Coupling Factor: `|D| / (|S|^2 - |S|)`, one value per system.

    The only system-level metric in the catalogue, so it is the one that forces
    `element_kind` to be a real column rather than a constant. Undefined for a
    single-service graph, where the denominator is zero.
    """
    size = len(graph.nodes)
    element = ids.system_id(model.system)
    if size < 2:
        return [
            MetricValue(
                element,
                "system",
                "SCF",
                None,
                determined=False,
                note=f"|S| = {size}; density is undefined below two services",
            )
        ]
    pairs = len(graph_ops._pairs(graph))
    return [MetricValue(element, "system", "SCF", pairs / float(size * size - size))]


def async_ratio(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """`ASYNC%`: share of a service's incident edge *elements* with `kind = async`.

    Counts edge elements, not service pairs: a sync and an async edge to the
    same neighbour are precisely the case this metric exists to see (DD-001).

    DD-004 governs what may be an async edge at all: telemetry transports are
    not application communication, so a system whose only AMQP traffic is
    Kieker's must read 0 here and not "highly asynchronous". A service with no
    edges has no ratio, and reports undetermined rather than 0, because otherwise an
    isolated service is indistinguishable from a fully synchronous one.
    """
    incident: dict[str, list[str]] = {node: [] for node in graph.nodes}
    for source, target, kind in graph.edges:
        incident[source].append(kind)
        incident[target].append(kind)
    values: list[MetricValue] = []
    for node in graph.nodes:
        kinds = incident[node]
        if not kinds:
            values.append(
                MetricValue(node, "service", "ASYNC%", None, determined=False, note="no edges in G")
            )
        else:
            values.append(
                MetricValue(
                    node,
                    "service",
                    "ASYNC%",
                    sum(1 for kind in kinds if kind == "async") / float(len(kinds)),
                )
            )
    return values


def deg(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Degree centrality: distinct neighbours over `|S| - 1`.

    Undirected neighbourhood, normalised, so it is comparable across the three
    subject systems, which differ in size by a factor of seven.
    """
    size = len(graph.nodes)
    if size < 2:
        return [
            MetricValue(node, "service", "DEG", None, determined=False, note=f"|S| = {size}")
            for node in graph.nodes
        ]
    adjacency = graph_ops.neighbours(graph)
    return [
        MetricValue(node, "service", "DEG", len(adjacency[node]) / float(size - 1))
        for node in graph.nodes
    ]


def btw(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Betweenness centrality over `G` (Brandes, unweighted, normalised).

    The catalogue asks for volume weighting; this evidence configuration has no
    observed call volume, so the value is the unweighted one and says so in the
    note. Adding telemetry changes the weighting, and therefore the catalogue
    version, rather than silently changing what past profiles meant.
    """
    size = len(graph.nodes)
    if size < 3:
        return [
            MetricValue(
                node,
                "service",
                "BTW",
                None,
                determined=False,
                note=f"|S| = {size}; betweenness needs at least three services",
            )
            for node in graph.nodes
        ]
    scores = graph_ops.betweenness(graph)
    return [
        MetricValue(node, "service", "BTW", scores[node], note="unweighted: no observed call volume")
        for node in graph.nodes
    ]


def nod(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Number of domain entities owned, `NOD(s)`.

    Counts `DomainEntity` elements (metamodel 0.2.0-json). The catalogue says
    *aggregate roots*; the extractor sees persisted types, which over-counts
    where an aggregate spans several tables. Recorded as a construct-validity
    limitation in `docs/03-metric-catalogue.md` rather than papered over.
    """
    counts = {node: 0 for node in graph.nodes}
    for entity in model.entities:
        if entity.service in counts:
            counts[entity.service] += 1
    return [MetricValue(node, "service", "NOD", float(counts[node])) for node in graph.nodes]


def cyc(model: ArchitectureModel, graph: ServiceGraph) -> list[MetricValue]:
    """Cyclic dependency: does `s` participate in a cycle in `G`?

    Emitted per service as 1/0, with the cycle's other members in the note, so
    an explanation can name them without recomputing anything. Deterministic
    for the same reason every other metric is: the components are sorted.
    """
    members = graph_ops.cycle_members(graph)
    values: list[MetricValue] = []
    for node in graph.nodes:
        component = members.get(node)
        if component is None:
            values.append(MetricValue(node, "service", "CYC", 0.0))
        else:
            others = [member.split("/")[-1] for member in component if member != node]
            note = "cycle with " + ", ".join(others) if others else "self-dependency"
            values.append(MetricValue(node, "service", "CYC", 1.0, note=note))
    return values


GOD_INPUTS = ("AIS", "NOE", "NOD")


def god(
    model: ArchitectureModel,
    graph: ServiceGraph,
    thresholds: Thresholds | None = None,
) -> list[MetricValue]:
    """God service: `AIS(s) > t1 and NOE(s) > t2 and NOD(s) > t3`.

    The thresholds come from the versioned, derived set in
    `metrics/catalogue/thresholds.json`. If any of the three is undetermined,
    every service reports undetermined with the reason: a conjunctive predicate
    missing a conjunct is a different, looser predicate, and firing it would
    manufacture god services out of a threshold that was never derivable.
    """
    thresholds = thresholds if thresholds is not None else Thresholds.load()
    resolved, reason = thresholds.resolve("GOD", GOD_INPUTS)
    if resolved is None:
        return [
            MetricValue(node, "service", "GOD", None, determined=False, note=reason)
            for node in graph.nodes
        ]
    inputs = {
        "AIS": {v.element_id: v for v in ais(model, graph)},
        "NOE": {v.element_id: v for v in noe(model, graph)},
        "NOD": {v.element_id: v for v in nod(model, graph)},
    }
    values: list[MetricValue] = []
    for node in graph.nodes:
        crossed = []
        undetermined = [name for name in GOD_INPUTS if not inputs[name][node].determined]
        if undetermined:
            values.append(
                MetricValue(
                    node,
                    "service",
                    "GOD",
                    None,
                    determined=False,
                    note="undetermined input(s): " + ", ".join(undetermined),
                )
            )
            continue
        for name in GOD_INPUTS:
            value = inputs[name][node].value
            if value is not None and value > resolved[name]:
                crossed.append(f"{name}={value:g}>{resolved[name]:g}")
        fires = len(crossed) == len(GOD_INPUTS)
        values.append(
            MetricValue(
                node,
                "service",
                "GOD",
                1.0 if fires else 0.0,
                note=("crossed " + ", ".join(crossed)) if fires else f"thresholds {thresholds.version}",
            )
        )
    return values


#: Every catalogued metric, by the ID `docs/03-metric-catalogue.md` gives it.
#: Group B (`CPL`, `CHAT`, `FANOUT_r`) is absent because it is trace-only and
#: this evidence configuration has no telemetry; `LOC_s`, `SGI`, `NANO`,
#: `CHATTY`, `BOTTLE` and `PR` are absent for the reasons recorded in that
#: document's status table. Absent is the honest state: a metric computed from
#: evidence the pipeline does not have would be a fabrication, not a gap.
METRICS = {
    "ACS": acs,
    "ADS": ads,
    "AIS": ais,
    "ASYNC%": async_ratio,
    "BTW": btw,
    "CYC": cyc,
    "DEG": deg,
    "GOD": god,
    "NOD": nod,
    "NOE": noe,
    "SCF": scf,
    "SHARED_DB": shared_db,
}


def compute_all(
    model: ArchitectureModel,
    graph: ServiceGraph,
    thresholds: Thresholds | None = None,
) -> list[MetricValue]:
    thresholds = thresholds if thresholds is not None else Thresholds.load()
    values: list[MetricValue] = []
    for name in sorted(METRICS):
        function = METRICS[name]
        if function is god:
            values.extend(god(model, graph, thresholds))
        else:
            values.extend(function(model, graph))
    return sorted(values, key=lambda v: (v.metric, v.element_id))
