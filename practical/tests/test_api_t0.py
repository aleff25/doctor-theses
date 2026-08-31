"""Stage 6 at trust level T0.

These tests are about the *contract*, not about the numbers: the numbers are
already tested where they are computed, and the API's job is to hand them over
without losing the two things that make them honest: the version stamp and the
distinction between an undetermined metric and a zero.

The suite is skipped when the `api` extra is not installed, because the pipeline
itself must stay runnable with no third-party packages at all.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("fastapi", reason="install the api extra: pip install -e '.[api,dev]'")

from fastapi.testclient import TestClient  # noqa: E402

from aam4j_api.app import app  # noqa: E402
from aam4j_api.store import NotFound, ProfileStore  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.path.join(ROOT, "data", "processed", "petclinic", "305a1f13", "metric_profile.csv")

pytestmark = pytest.mark.skipif(
    not os.path.exists(PROFILE),
    reason="run `python run_pipeline.py --system petclinic` first",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_reports_which_systems_have_artifacts(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert {entry["system"] for entry in body["systems"]} == {"petclinic", "teastore", "trainticket"}


def test_every_response_carries_the_version_stamp(client):
    """Constraint 4 of `docs/01-pipeline.md`: everything is versioned. A served
    number whose catalogue version is unknown is not reproducible."""
    for url in ("/health", "/catalogue", "/systems", "/systems/petclinic/profile"):
        block = client.get(url).json()["provenance"]
        assert block["metamodel_version"] and block["catalogue_version"]
        assert block["trust_level"] == "T0"
        assert block["llm"]["enabled"] is False


def test_the_api_never_offers_an_assessment_at_t0(client):
    """The LLM-off fallback has to be a working system, and a working system
    that has no quality model must say so instead of scoring anything."""
    body = client.get("/systems/petclinic/services/customers-service").json()
    assert body["assessment"]["available"] is False
    assert "stage 4" in body["assessment"]["reason"]


def test_undetermined_metrics_are_served_as_null_and_not_as_zero(client):
    """The single most important property of this API. `GOD` cannot be
    evaluated without a derivable threshold; serving 0 would publish 'no god
    services here' on the strength of no evidence at all."""
    body = client.get("/systems/petclinic/profile", params={"metric": "GOD"}).json()
    assert body["rows"], "GOD should be present in the profile"
    for row in body["rows"]:
        assert row["determined"] is False
        assert row["value"] is None
        assert row["note"]


def test_service_view_lists_its_undetermined_metrics_explicitly(client):
    body = client.get("/systems/petclinic/services/visits-service").json()
    assert "GOD" in body["undetermined_metrics"]
    assert "ASYNC%" in body["undetermined_metrics"]  # no edges in G


def test_profile_filters_compose(client):
    body = client.get(
        "/systems/petclinic/profile",
        params={"metric": ["AIS", "ADS"], "element": "vets-service"},
    ).json()
    assert {row["metric"] for row in body["rows"]} == {"AIS", "ADS"}
    assert {row["element_id"] for row in body["rows"]} == {"petclinic/service/vets-service"}


def test_an_unknown_metric_is_a_client_error_not_an_empty_result(client):
    """An empty list would read as 'this system has no such smell'."""
    response = client.get("/systems/petclinic/profile", params={"metric": "NOT_A_METRIC"})
    assert response.status_code == 400
    assert "NOT_A_METRIC" in response.json()["detail"]


def test_unknown_system_is_404_and_names_the_known_ones(client):
    response = client.get("/systems/spring-petclinic/graph")
    assert response.status_code == 404
    assert "petclinic" in response.json()["error"]


def test_graph_serves_roles_so_a_figure_can_declare_its_scope(client):
    """DD-002: any figure that includes infrastructure nodes must say so, which
    it can only do if the role travels with the node."""
    body = client.get("/systems/petclinic/graph").json()
    roles = {service["role"] for service in body["services"]}
    assert roles == {"functional", "infrastructure"}
    assert all(service["role_rule"] for service in body["services"])


def test_gaps_are_a_first_class_endpoint(client):
    body = client.get("/systems/petclinic/gaps").json()
    concerns = {gap["concern"] for gap in body["gaps"]}
    assert any(concern.startswith("store-identity") for concern in concerns)


def test_store_refuses_a_snapshot_that_is_not_pinned():
    """Serving whatever happens to sit in `data/` would let an unpinned run be
    presented as the subject system."""
    store = ProfileStore(ROOT)
    with pytest.raises(NotFound):
        store.resolve("petclinic", "0000000")
    assert store.resolve("petclinic", "305a1f13").commit.startswith("305a1f13")
