"""Mutation-based supervision, and the guards that keep it from lying.

Synthetic labels are only worth having if two things hold: the operator really
injects the property it claims, and the resulting learning task is not
circular. Both are tested here, on hand-built models whose expected values are
arithmetic rather than a claim about a real system.
"""

from __future__ import annotations

import pytest

from aam4j_metrics.catalogue import cyc, noe, nod, shared_db
from aam4j_metrics.graph import build_graph
from aam4j_model import ids
from aam4j_model.model import (
    DECLARED,
    FUNCTIONAL,
    ArchitectureModel,
    Dependency,
    DomainEntity,
    Endpoint,
    PersistenceLink,
    Service,
    Store,
)
from aam4j_models.dataset import (
    CYCLE,
    EXCLUDED_FEATURES,
    Label,
    assemble,
    leave_one_system_out,
    materialise,
)
from aam4j_models.mutate import introduce_cycle, merge_services, mutate_all, share_database

SYS = "toy"


def service(name: str) -> Service:
    return Service(
        id=ids.service_id(SYS, name),
        name=name,
        role=FUNCTIONAL,
        role_rule="test",
        technology="test",
        source_module=None,
        has_source_module=True,
    )


def edge(source: str, target: str) -> Dependency:
    return Dependency(
        id=ids.edge_id(SYS, source, target, "sync"),
        source=ids.service_id(SYS, source),
        target=ids.service_id(SYS, target),
        kind="sync",
        provenance=DECLARED,
        mechanisms=["test"],
        evidence=[],
    )


@pytest.fixture
def chain() -> ArchitectureModel:
    """a -> b -> c, acyclic; a owns a store; b and c own none."""
    model = ArchitectureModel(system=SYS, snapshot="deadbeef")
    model.services = [service("a"), service("b"), service("c")]
    model.dependencies = [edge("a", "b"), edge("b", "c")]
    model.stores = [Store(id=ids.store_id(SYS, "db"), name="db", vendors=["mysql"], tables=["t"])]
    model.persistence_links = [
        PersistenceLink(ids.service_id(SYS, "a"), ids.store_id(SYS, "db"), "mysql", "owns-tables")
    ]
    model.endpoints = [
        Endpoint(ids.endpoint_id(SYS, "b", "GET", "/b"), ids.service_id(SYS, "b"), "GET", "/b")
    ]
    model.entities = [DomainEntity(ids.entity_id(SYS, "a", "T"), ids.service_id(SYS, "a"), "T", "t")]
    return model


def values(records):
    return {v.element_id.split("/")[-1]: v.value for v in records}


def test_introduce_cycle_actually_creates_a_cycle(chain):
    """The label is only sound if the operator's claim is verified by the
    deterministic detector on the mutant."""
    assert values(cyc(chain, build_graph(chain))) == {"a": 0.0, "b": 0.0, "c": 0.0}
    mutants = introduce_cycle(chain)
    assert mutants
    for mutant in mutants:
        detected = values(cyc(mutant.model, build_graph(mutant.model)))
        for element in mutant.implicated:
            assert detected[element.split("/")[-1]] == 1.0


def test_the_base_model_is_never_mutated_in_place(chain):
    before = len(chain.dependencies)
    mutate_all(chain)
    assert len(chain.dependencies) == before


def test_mutation_is_deterministic(chain):
    first = [(m.variant, m.implicated, m.description) for m in mutate_all(chain)]
    second = [(m.variant, m.implicated, m.description) for m in mutate_all(chain)]
    assert first == second


def test_share_database_makes_the_smell_fire_on_both_services(chain):
    mutants = share_database(chain)
    assert mutants
    mutant = mutants[0]
    detected = values(shared_db(mutant.model, build_graph(mutant.model)))
    assert detected[mutant.implicated[0].split("/")[-1]] == 1.0
    assert detected["a"] == 1.0  # the lender is now sharing too


def test_merge_moves_endpoints_and_entities_to_the_absorber(chain):
    mutants = merge_services(chain, keep_top=1)
    mutant = mutants[0]
    absorber = mutant.implicated[0].split("/")[-1]
    graph = build_graph(mutant.model)
    assert len(mutant.model.services) == len(chain.services) - 1
    assert values(noe(mutant.model, graph))[absorber] >= 1.0
    assert sum(values(nod(mutant.model, graph)).values()) == float(len(chain.entities))


def test_merge_drops_edges_that_became_internal(chain):
    """An edge between two merged services is no longer a dependency; leaving it
    would show up as a self-loop and inflate every degree metric."""
    for mutant in merge_services(chain, keep_top=3):
        assert all(d.source != d.target for d in mutant.model.dependencies)


# ---------------------------------------------------------------------------
# dataset guards
# ---------------------------------------------------------------------------
def _profiles():
    def row(system, element, metric, value, determined=True):
        return {
            "system": system,
            "snapshot": "deadbeef",
            "element_id": element,
            "element_kind": "service",
            "metric": metric,
            "value": "" if not determined else repr(float(value)),
            "determined": "true" if determined else "false",
            "note": "",
        }

    return {
        ("s1", "base"): [
            row("s1", "s1/service/x", "CYC", 0),
            row("s1", "s1/service/x", "AIS", 1),
            row("s1", "s1/service/x", "BTW", 0, determined=False),
            row("s1", "s1/service/y", "CYC", 0),
            row("s1", "s1/service/y", "AIS", 3),
            row("s1", "s1/service/y", "BTW", 2),
        ],
        ("s2", "base"): [
            row("s2", "s2/service/z", "CYC", 1),
            row("s2", "s2/service/z", "AIS", 9),
            row("s2", "s2/service/z", "BTW", 4),
        ],
    }


def _labels():
    return [
        Label("s1", "deadbeef", "base", "s1/service/x", CYCLE, 0, "by-construction", "none", ""),
        Label("s1", "deadbeef", "base", "s1/service/y", CYCLE, 0, "by-construction", "none", ""),
        Label("s2", "deadbeef", "base", "s2/service/z", CYCLE, 1, "by-construction", "introduce_cycle", ""),
    ]


def test_the_detector_of_the_injected_property_is_never_a_feature():
    """`CYC` predicts the `cycle` task perfectly by construction. Leaving it in
    would produce a flawless classifier that has learned nothing at all."""
    dataset = assemble(_profiles(), _labels(), CYCLE)
    assert "CYC" in EXCLUDED_FEATURES[CYCLE]
    assert "CYC" not in dataset.feature_names
    assert "AIS" in dataset.feature_names


def test_system_level_metrics_are_not_service_features():
    """`SCF` is one number per system, so it would act as a system label."""
    dataset = assemble(_profiles(), _labels(), CYCLE)
    assert "SCF" not in dataset.feature_names


def test_leave_one_system_out_never_shares_a_system_across_the_split():
    dataset = assemble(_profiles(), _labels(), CYCLE)
    for held_out, train, test in leave_one_system_out(dataset):
        train_systems = {dataset.rows[i]["system"] for i in train}
        test_systems = {dataset.rows[i]["system"] for i in test}
        assert test_systems == {held_out}
        assert held_out not in train_systems


def test_undetermined_becomes_an_indicator_and_not_a_silent_zero():
    dataset = assemble(_profiles(), _labels(), CYCLE)
    held_out, train, test = leave_one_system_out(dataset)[0]
    data = materialise(dataset, train, test)
    assert "BTW__undetermined" in data["columns"]
    flag = data["columns"].index("BTW__undetermined")
    btw = data["columns"].index("BTW")
    rows = data["x_train"] + data["x_test"]
    flagged = [row for row in rows if row[flag] == 1.0]
    assert flagged, "the fixture has one undetermined BTW"
    for row in flagged:
        assert row[btw] == data["medians"]["BTW"]


def test_imputation_statistics_are_fitted_on_the_training_fold_only():
    """Median over the whole dataset would leak the held-out system's
    distribution into training."""
    dataset = assemble(_profiles(), _labels(), CYCLE)
    medians = {}
    for held_out, train, test in leave_one_system_out(dataset):
        medians[held_out] = materialise(dataset, train, test)["medians"]["AIS"]
    assert medians["s1"] != medians["s2"]
