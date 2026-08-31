"""Unit tests for the metrics added in catalogue 0.2.0.

`docs/03-metric-catalogue.md` item 6: a metric with no test on a model whose
correct value is known by hand is a definition, not a metric. The fixture below
is a three-service cycle plus one isolated service, small enough that every
expected value in this file is arithmetic done on paper and stated in the
docstring that asserts it.

The cycle is deliberate: it is the case PetClinic cannot exercise (its declared
graph is acyclic) and the one `CYC`, `BTW` and `ACS` all turn on.
"""

from __future__ import annotations

import pytest

from aam4j_metrics.catalogue import acs, async_ratio, btw, compute_all, cyc, deg, god, nod, scf
from aam4j_metrics.graph import build_graph, cycle_members, strongly_connected_components
from aam4j_metrics.thresholds import Threshold, Thresholds
from aam4j_model import ids
from aam4j_model.model import (
    DECLARED,
    FUNCTIONAL,
    INFRASTRUCTURE,
    ArchitectureModel,
    Dependency,
    DomainEntity,
    Endpoint,
    Service,
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


def entity(service_name: str, java_type: str, table: str) -> DomainEntity:
    return DomainEntity(
        id=ids.entity_id(SYS, service_name, java_type),
        service=ids.service_id(SYS, service_name),
        java_type=java_type,
        table=table,
    )


def by_name(records):
    return {v.element_id.split("/")[-1]: v.value for v in records}


def records_by_name(records):
    return {v.element_id.split("/")[-1]: v for v in records}


# ---------------------------------------------------------------------------
#   a --> b --> c --> a       d is isolated.      e is infrastructure.
#
# Over G = {a,b,c,d}, |D| = 3 pairs:
#   AIS = ADS = 1 for a,b,c and 0 for d   ->  ACS = 1,1,1,0
#   SCF = 3 / (4^2 - 4) = 0.25
#   DEG = 2/3 for a,b,c and 0 for d
#   BTW: each of a,b,c lies on exactly one shortest path between the other
#        two, so raw = 1 and normalised = 1/((4-1)(4-2)) = 1/6
#   CYC = 1 for a,b,c (one component) and 0 for d
# ---------------------------------------------------------------------------
@pytest.fixture
def ring() -> ArchitectureModel:
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [service("a"), service("b"), service("c"), service("d"), service("e", INFRASTRUCTURE)]
    model.dependencies = [edge("a", "b"), edge("b", "c"), edge("c", "a"), edge("a", "e")]
    return model


def test_acs_is_the_product_of_the_two_degrees(ring):
    graph = build_graph(ring)
    assert by_name(acs(ring, graph)) == {"a": 1.0, "b": 1.0, "c": 1.0, "d": 0.0}


def test_scf_is_system_level_and_uses_distinct_pairs(ring):
    graph = build_graph(ring)
    values = scf(ring, graph)
    assert len(values) == 1
    assert values[0].element_kind == "system"
    assert values[0].element_id == ids.system_id(SYS)
    assert values[0].value == pytest.approx(0.25)


def test_scf_of_a_sync_and_an_async_edge_between_one_pair_counts_the_pair_once(ring):
    """DD-001 makes them two edge elements; density is a property of `S x S`."""
    ring.dependencies.append(edge("a", "b", kind="async"))
    assert scf(ring, build_graph(ring))[0].value == pytest.approx(0.25)


def test_scf_is_undetermined_below_two_services():
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [service("only")]
    value = scf(model, build_graph(model))[0]
    assert value.value is None and value.determined is False


def test_degree_centrality_is_normalised_by_the_graph_size(ring):
    graph = build_graph(ring)
    values = by_name(deg(ring, graph))
    assert values["a"] == pytest.approx(2 / 3)
    assert values["d"] == 0.0


def test_betweenness_on_a_three_cycle_is_one_sixth_each(ring):
    graph = build_graph(ring)
    values = by_name(btw(ring, graph))
    for node in ("a", "b", "c"):
        assert values[node] == pytest.approx(1 / 6)
    assert values["d"] == 0.0


def test_betweenness_records_that_it_is_unweighted(ring):
    """The catalogue asks for volume weighting; without telemetry the value must
    say which one it is rather than let a reader assume the weighted one."""
    assert "unweighted" in btw(ring, build_graph(ring))[0].note


def test_betweenness_is_undetermined_below_three_services():
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [service("a"), service("b")]
    model.dependencies = [edge("a", "b")]
    assert all(v.determined is False for v in btw(model, build_graph(model)))


def test_a_star_topology_puts_all_betweenness_on_the_hub():
    """b is on every shortest path between a, c and d, and nothing else is."""
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [service(n) for n in ("a", "b", "c", "d")]
    model.dependencies = [edge("a", "b"), edge("b", "c"), edge("b", "d")]
    values = by_name(btw(model, build_graph(model)))
    assert values["b"] == pytest.approx(2 / 6)  # (a,c) and (a,d)
    assert values["a"] == values["c"] == values["d"] == 0.0


def test_cyc_fires_for_every_member_and_names_the_others(ring):
    graph = build_graph(ring)
    values = records_by_name(cyc(ring, graph))
    assert {name: v.value for name, v in values.items()} == {"a": 1.0, "b": 1.0, "c": 1.0, "d": 0.0}
    assert "b" in values["a"].note and "c" in values["a"].note


def test_dd002_filtering_can_break_a_cycle_that_runs_through_infrastructure(ring):
    """a -> e -> a is a cycle in the full model and not one in `G`. DD-002 says
    the metric layer decides, and the answer must differ between the two."""
    ring.dependencies.append(edge("e", "a"))
    assert cycle_members(build_graph(ring)).keys() == {
        ids.service_id(SYS, n) for n in ("a", "b", "c")
    }
    wide = build_graph(ring, roles=(FUNCTIONAL, INFRASTRUCTURE))
    assert ids.service_id(SYS, "e") in cycle_members(wide)


def test_scc_of_an_acyclic_graph_is_all_singletons():
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [service(n) for n in ("a", "b", "c")]
    model.dependencies = [edge("a", "b"), edge("b", "c")]
    graph = build_graph(model)
    assert all(len(component) == 1 for component in strongly_connected_components(graph))
    assert cycle_members(graph) == {}


def test_async_ratio_counts_edge_elements_not_pairs(ring):
    """a -> b exists as both sync and async: a has three incident elements
    (a->b sync, a->b async, c->a) of which one is async."""
    ring.dependencies.append(edge("a", "b", kind="async"))
    values = by_name(async_ratio(ring, build_graph(ring)))
    assert values["a"] == pytest.approx(1 / 3)
    assert values["b"] == pytest.approx(1 / 3)
    assert values["c"] == 0.0


def test_async_ratio_is_undetermined_for_a_service_with_no_edges(ring):
    """An isolated service has no ratio. Reporting 0 would make it look fully
    synchronous, which is a claim the evidence does not support."""
    value = records_by_name(async_ratio(ring, build_graph(ring)))["d"]
    assert value.value is None and value.determined is False


def test_nod_counts_entities_of_the_owning_service_only(ring):
    ring.entities = [
        entity("a", "Owner", "owners"),
        entity("a", "Pet", "pets"),
        entity("b", "Visit", "visits"),
        entity("e", "AuditRecord", "audit"),  # infrastructure: filtered out of G
    ]
    values = by_name(nod(ring, build_graph(ring)))
    assert values == {"a": 2.0, "b": 1.0, "c": 0.0, "d": 0.0}
    assert "e" not in values


# ---------------------------------------------------------------------------
# GOD: AIS > t1 and NOE > t2 and NOD > t3, all three or nothing.
# ---------------------------------------------------------------------------
def _thresholds(ais_value, noe_value=1.0, nod_value=0.0, reason="") -> Thresholds:
    return Thresholds(
        version="test",
        method="hand-set",
        derived_from=(),
        by_smell={
            "GOD": {
                "AIS": Threshold(ais_value, reason),
                "NOE": Threshold(noe_value),
                "NOD": Threshold(nod_value),
            }
        },
    )


@pytest.fixture
def with_god_inputs(ring) -> ArchitectureModel:
    for method, route in (("GET", "/x"), ("POST", "/x")):
        ring.endpoints.append(
            Endpoint(
                id=ids.endpoint_id(SYS, "a", method, route),
                service=ids.service_id(SYS, "a"),
                http_method=method,
                route_template=route,
            )
        )
    ring.entities = [entity("a", "Owner", "owners")]
    return ring


def test_god_fires_only_when_every_conjunct_is_crossed(with_god_inputs):
    """a: AIS 1>0, NOE 2>1, NOD 1>0 -> fires. b and c cross AIS only."""
    graph = build_graph(with_god_inputs)
    values = records_by_name(god(with_god_inputs, graph, _thresholds(0.0)))
    assert values["a"].value == 1.0
    assert values["b"].value == 0.0 and values["c"].value == 0.0
    assert "AIS=1>0" in values["a"].note and "NOE=2>1" in values["a"].note


def test_god_is_undetermined_when_a_threshold_could_not_be_derived(with_god_inputs):
    """The rule that keeps the smell honest: a conjunctive predicate missing a
    conjunct is a looser predicate, so it must not be evaluated at all."""
    thresholds = _thresholds(None, reason="degenerate distribution")
    values = records_by_name(god(with_god_inputs, build_graph(with_god_inputs), thresholds))
    assert all(v.value is None and v.determined is False for v in values.values())
    assert "degenerate distribution" in values["a"].note


def test_god_is_undetermined_with_no_threshold_set_at_all(with_god_inputs):
    empty = Thresholds(version="unset", method="", derived_from=(), by_smell={})
    values = god(with_god_inputs, build_graph(with_god_inputs), empty)
    assert all(v.determined is False for v in values)


def test_compute_all_emits_every_catalogued_metric(ring):
    from aam4j_metrics.catalogue import METRICS

    values = compute_all(ring, build_graph(ring))
    assert {v.metric for v in values} == set(METRICS)
