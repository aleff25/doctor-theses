"""Metric unit tests over hand-built model instances.

`docs/03-metric-catalogue.md` item 6: "a metric with no test on a model whose
correct value is known by hand is a definition, not a metric". These models are
written by hand precisely so the expected values are arithmetic on four nodes
rather than a claim about a real system.

They also cover the cases PetClinic does not exercise: async edges, an
undetermined `SHARED_DB`, and infrastructure nodes opted *into* `G`.
"""

from __future__ import annotations

import pytest

from aam4j_metrics.catalogue import ads, ais, noe, shared_db
from aam4j_metrics.graph import build_graph
from aam4j_model import ids
from aam4j_model.model import (
    DECLARED,
    FUNCTIONAL,
    INFRASTRUCTURE,
    OBSERVED,
    ArchitectureModel,
    Dependency,
    Endpoint,
    EvidenceGap,
    PersistenceLink,
    Service,
    Store,
)

SYS = "toy"


def service(name: str, role: str = FUNCTIONAL) -> Service:
    return Service(
        id=ids.service_id(SYS, name),
        name=name,
        role=role,
        role_rule="test",
        technology="test",
        source_module=None,
        has_source_module=True,
    )


def edge(source: str, target: str, kind: str = "sync", provenance: str = DECLARED) -> Dependency:
    return Dependency(
        id=ids.edge_id(SYS, source, target, kind),
        source=ids.service_id(SYS, source),
        target=ids.service_id(SYS, target),
        kind=kind,
        provenance=provenance,
        mechanisms=["test"],
        evidence=[],
    )


def values_by_name(records):
    return {v.element_id.split("/")[-1]: v.value for v in records}


# ---------------------------------------------------------------------------
#   a --> b --> c        d is isolated.       e is infrastructure and is
#   |           ^                             called by a and calls b.
#   +-----------+
#
# Hand values over G = {a,b,c,d} (functional only):
#   AIS: a=0  b=1  c=2  d=0
#   ADS: a=2  b=1  c=0  d=0
# ---------------------------------------------------------------------------
@pytest.fixture
def diamond() -> ArchitectureModel:
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [
        service("a"),
        service("b"),
        service("c"),
        service("d"),
        service("e", INFRASTRUCTURE),
    ]
    model.dependencies = [
        edge("a", "b"),
        edge("b", "c"),
        edge("a", "c"),
        edge("a", "e"),
        edge("e", "b"),
    ]
    return model


def test_ais_and_ads_on_a_hand_built_graph(diamond):
    graph = build_graph(diamond)
    assert values_by_name(ais(diamond, graph)) == {"a": 0.0, "b": 1.0, "c": 2.0, "d": 0.0}
    assert values_by_name(ads(diamond, graph)) == {"a": 2.0, "b": 1.0, "c": 0.0, "d": 0.0}


def test_dd002_filter_removes_edges_incident_to_filtered_nodes(diamond):
    """`e` is infrastructure, so a->e and e->b are not in D. Without this, `b`
    would read AIS 2 and `a` ADS 3 — the corruption DD-002 exists to prevent."""
    graph = build_graph(diamond)
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 3


def test_infrastructure_can_be_opted_into_the_graph_explicitly(diamond):
    """DD-002 allows metrics to opt in to infrastructure nodes; the graph then
    records that it did, so a figure using it can say so."""
    graph = build_graph(diamond, roles=(FUNCTIONAL, INFRASTRUCTURE))
    assert values_by_name(ais(diamond, graph))["b"] == 2.0
    assert values_by_name(ads(diamond, graph))["a"] == 3.0
    assert graph.roles_included == (FUNCTIONAL, INFRASTRUCTURE)


def test_observed_edges_are_excluded_from_the_declared_graph(diamond):
    """An edge observed at runtime but never declared must not silently join
    the declared graph — their disagreement is the finding."""
    diamond.dependencies.append(edge("d", "a", provenance=OBSERVED))
    assert values_by_name(ads(diamond, build_graph(diamond)))["d"] == 0.0
    observed_graph = build_graph(diamond, provenance=(OBSERVED,))
    assert values_by_name(ads(diamond, observed_graph))["d"] == 1.0


def test_sync_and_async_between_the_same_pair_are_one_neighbour(diamond):
    """DD-001 makes them two edge elements; AIS/ADS count services, so the pair
    contributes 1 to each degree, not 2."""
    diamond.dependencies.append(edge("a", "b", kind="async"))
    graph = build_graph(diamond)
    assert len(graph.edges) == 4
    assert values_by_name(ais(diamond, graph))["b"] == 1.0
    assert values_by_name(ads(diamond, graph))["a"] == 2.0


# ---------------------------------------------------------------------------
# NOE: two methods on one route are two endpoint elements under DD-001.
#   a: GET /x, POST /x, GET /y/{id}  = 3
#   b: none                          = 0
# ---------------------------------------------------------------------------
def test_noe_counts_endpoint_elements(diamond):
    for method, route in (("GET", "/x"), ("POST", "/x"), ("GET", "/y/{id}")):
        diamond.endpoints.append(
            Endpoint(
                id=ids.endpoint_id(SYS, "a", method, route),
                service=ids.service_id(SYS, "a"),
                http_method=method,
                route_template=route,
            )
        )
    counts = values_by_name(noe(diamond, build_graph(diamond)))
    assert counts["a"] == 3.0
    assert counts["b"] == 0.0


def test_noe_ignores_endpoints_of_filtered_services(diamond):
    diamond.endpoints.append(
        Endpoint(
            id=ids.endpoint_id(SYS, "e", "GET", "/admin"),
            service=ids.service_id(SYS, "e"),
            http_method="GET",
            route_template="/admin",
        )
    )
    assert "e" not in values_by_name(noe(diamond, build_graph(diamond)))


# ---------------------------------------------------------------------------
# SHARED_DB
#   a and b both own tables in store `shared`   -> 1, 1
#   c owns store `own` alone                    -> 0
#   d declares no store at all                  -> 0
# ---------------------------------------------------------------------------
def test_shared_db_fires_only_for_the_services_that_share(diamond):
    diamond.stores = [
        Store(id=ids.store_id(SYS, "shared"), name="shared", vendors=["mysql"], tables=["t1", "t2"]),
        Store(id=ids.store_id(SYS, "own"), name="own", vendors=["mysql"], tables=["t3"]),
    ]
    diamond.persistence_links = [
        PersistenceLink(ids.service_id(SYS, "a"), ids.store_id(SYS, "shared"), "mysql", "owns-tables"),
        PersistenceLink(ids.service_id(SYS, "b"), ids.store_id(SYS, "shared"), "mysql", "owns-tables"),
        PersistenceLink(ids.service_id(SYS, "c"), ids.store_id(SYS, "own"), "mysql", "owns-tables"),
    ]
    assert values_by_name(shared_db(diamond, build_graph(diamond))) == {
        "a": 1.0,
        "b": 1.0,
        "c": 0.0,
        "d": 0.0,
    }


def test_shared_db_is_evaluated_within_a_vendor(diamond):
    """Two vendors' DDL are alternative deployments of one service, not two
    live stores, so a name collision across vendors is not sharing."""
    diamond.persistence_links = [
        PersistenceLink(ids.service_id(SYS, "a"), ids.store_id(SYS, "db"), "mysql", "owns-tables"),
        PersistenceLink(ids.service_id(SYS, "b"), ids.store_id(SYS, "db"), "postgres", "owns-tables"),
    ]
    result = values_by_name(shared_db(diamond, build_graph(diamond)))
    assert result["a"] == 0.0 and result["b"] == 0.0


def test_shared_db_reports_undetermined_rather_than_zero(diamond):
    """The case that matters for honesty: a service with a database whose
    identity the snapshot does not carry must not be reported as `0`."""
    diamond.evidence_gaps = [
        EvidenceGap(
            subject=ids.service_id(SYS, "a"),
            concern="store-identity:hsqldb",
            reason="no JDBC URL in this checkout",
        )
    ]
    result = {v.element_id.split("/")[-1]: v for v in shared_db(diamond, build_graph(diamond))}
    assert result["a"].value is None
    assert result["a"].determined is False
    assert "hsqldb" in result["a"].note
    assert result["b"].determined is True
