"""Hand-derived ground truth for PetClinic at 305a1f13.

Every expected value in this file was worked out by reading the eight modules,
*before* comparing against the implementation. The derivation is written out in
the comments so a reviewer can check the number rather than trust it. If the
code and the comment disagree, one of the two is wrong and the disagreement is
the finding.

Re-derive this file whenever the pinned commit moves.
"""

from __future__ import annotations

import os

import pytest

from aam4j_extractor.bundle import extract
from aam4j_extractor.static_regex import RegexStaticAnalyser
from aam4j_metrics.catalogue import compute_all
from aam4j_metrics.graph import build_graph
from aam4j_metrics.profile import to_rows
from aam4j_model.build import build
from aam4j_model.model import FUNCTIONAL, INFRASTRUCTURE

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(HERE, "subjects", "petclinic")
SNAPSHOT = "305a1f13e4f961001d4e6cb50a9db51dc3fc5967"

pytestmark = pytest.mark.skipif(
    not os.path.isdir(REPO), reason="run subjects/fetch_subjects.sh first"
)


@pytest.fixture(scope="module")
def model():
    bundle = extract(REPO, "petclinic", SNAPSHOT, RegexStaticAnalyser())
    return build(bundle)


@pytest.fixture(scope="module")
def graph(model):
    return build_graph(model)


@pytest.fixture(scope="module")
def values(model, graph):
    return {(v.metric, v.element_id.split("/")[-1]): v for v in compute_all(model, graph)}


# ---------------------------------------------------------------------------
# DD-002 role classification
# ---------------------------------------------------------------------------
#
# Read of the eight reactor modules named in the root pom.xml:
#
#   config-server      @EnableConfigServer                       -> infrastructure
#   discovery-server   @EnableEurekaServer                       -> infrastructure
#   admin-server       @EnableAdminServer (Spring Boot Admin)    -> infrastructure
#   api-gateway        gateway starter AND 4 declared routes     -> infrastructure
#   customers-service  owners/pets domain, JPA, own DDL          -> functional
#   vets-service       vets/specialties domain, JPA, own DDL     -> functional
#   visits-service     visits domain, JPA, own DDL               -> functional
#   genai-service      chat over the pet-clinic domain           -> functional
#
# The first four are exactly the DD-002 infrastructure list for petclinic.
#
# genai-service is the interesting one. Its pom carries
# `spring-cloud-starter-gateway-server-webflux`, so a rule matching the gateway
# starter alone would classify it infrastructure. It declares no routes and its
# only endpoint is a domain chat endpoint, so it is functional. Rule R4 requires
# both conditions for exactly this reason.
#
# Three further containers exist in docker-compose.yml with no reactor module:
# tracing-server (Zipkin), prometheus-server, grafana-server. DD-002 says model
# everything and filter at metric time, so they are in the model, classified
# infrastructure by R5.

EXPECTED_ROLES = {
    "admin-server": (INFRASTRUCTURE, "R3-admin-console"),
    "api-gateway": (INFRASTRUCTURE, "R4-edge-gateway"),
    "config-server": (INFRASTRUCTURE, "R1-config-server"),
    "customers-service": (FUNCTIONAL, "default"),
    "discovery-server": (INFRASTRUCTURE, "R2-service-registry"),
    "genai-service": (FUNCTIONAL, "default"),
    "grafana-server": (INFRASTRUCTURE, "R5-no-source-module"),
    "prometheus-server": (INFRASTRUCTURE, "R5-no-source-module"),
    "tracing-server": (INFRASTRUCTURE, "R5-no-source-module"),
    "vets-service": (FUNCTIONAL, "default"),
    "visits-service": (FUNCTIONAL, "default"),
}


def test_roles_match_dd002(model):
    assert {s.name: (s.role, s.role_rule) for s in model.services} == EXPECTED_ROLES


def test_role_catalogue_needs_no_overrides(model):
    """DD-002 asks for an auditable rule, not a name list. No service in
    PetClinic needs a per-name override to reach the DD-002 classification."""
    assert not any(s.role_rule.startswith("override:") for s in model.services)


# ---------------------------------------------------------------------------
# Dependency edges
# ---------------------------------------------------------------------------
#
# Declared edges found by reading the sources and configuration:
#
# from Java (static)
#   api-gateway   -> customers-service   CustomersServiceClient, WebClient
#                                        "http://customers-service/owners/{ownerId}"
#   api-gateway   -> visits-service      VisitsServiceClient, "http://visits-service/"
#   genai-service -> customers-service   AIDataProvider,
#                                        discoveryClient.getInstances("customers-service")
#   genai-service -> vets-service        VectorStoreController, "http://vets-service/"
#
# from configuration
#   api-gateway   -> {vets,visits,customers,genai}-service    4 lb:// gateway routes
#   <7 modules>   -> config-server       spring.config.import: configserver:
#                                        (all but config-server itself)
#   <6 modules>   -> discovery-server    eureka client starter; admin-server,
#                                        api-gateway, customers, genai, vets, visits
#   compose depends_on, duplicating the two above
#
# Distinct (source, target, sync) elements: 4 gateway->domain, 7 ->config-server,
# 6 ->discovery-server, 2 genai->domain = 19.

def test_full_model_edge_count(model):
    assert len(model.dependencies) == 19
    assert all(d.provenance == "declared" for d in model.dependencies)


def test_no_observed_dependencies_in_this_evidence_configuration(model):
    """Static + configuration only. The distinction must exist in the model
    even when there is nothing observed to put on the other side of it."""
    assert [d for d in model.dependencies if d.provenance == "observed"] == []
    assert model.provenance["evidence_classes_absent"] == ["metrics", "traces"]


# G after the DD-002 filter. Removing a node removes its edges, so all four
# api-gateway->domain edges leave with the gateway, and every edge to
# config-server or discovery-server leaves with them.
#
#   S = {customers-service, genai-service, vets-service, visits-service}
#   D = {genai->customers, genai->vets}

def test_filtered_graph(graph):
    assert [n.split("/")[-1] for n in graph.nodes] == [
        "customers-service",
        "genai-service",
        "vets-service",
        "visits-service",
    ]
    assert [(s.split("/")[-1], t.split("/")[-1], k) for s, t, k in graph.edges] == [
        ("genai-service", "customers-service", "sync"),
        ("genai-service", "vets-service", "sync"),
    ]


# ---------------------------------------------------------------------------
# AIS — in-degree over G
# ---------------------------------------------------------------------------
#   customers-service   <- genai-service                      = 1
#   vets-service        <- genai-service                      = 1
#   visits-service      <- nothing in G (only api-gateway,    = 0
#                          which is filtered out)
#   genai-service       <- nothing                            = 0

HAND_AIS = {
    "customers-service": 1.0,
    "genai-service": 0.0,
    "vets-service": 1.0,
    "visits-service": 0.0,
}

# ---------------------------------------------------------------------------
# ADS — out-degree over G
# ---------------------------------------------------------------------------
#   genai-service  -> customers-service, vets-service         = 2
#   the three domain services make no calls to other services = 0
# (their outbound edges are all to config-server /
#  discovery-server, which are not in G)

HAND_ADS = {
    "customers-service": 0.0,
    "genai-service": 2.0,
    "vets-service": 0.0,
    "visits-service": 0.0,
}

# ---------------------------------------------------------------------------
# NOE — endpoints per service
# ---------------------------------------------------------------------------
# customers-service = 8
#   OwnerResource, class @RequestMapping("/owners"):
#     POST /owners                          createOwner
#     GET  /owners/{ownerId}                findOwner
#     GET  /owners                          findAll
#     PUT  /owners/{ownerId}                updateOwner
#   PetResource, no class-level mapping:
#     GET  /petTypes                        getPetTypes
#     POST /owners/{ownerId}/pets           processCreationForm
#     PUT  /owners/*/pets/{petId}           processUpdateForm
#     GET  /owners/*/pets/{petId}           findPet
#
# vets-service = 1
#   VetResource, class @RequestMapping("/vets"): GET /vets
#
# visits-service = 3
#   VisitResource, no class-level mapping:
#     POST /owners/*/pets/{petId}/visits
#     GET  /owners/*/pets/{petId}/visits
#     GET  /pets/visits
#
# genai-service = 1
#   PetclinicChatClient, class @RequestMapping("/"): POST /chatclient
#   VectorStoreController is @Component and AIDataProvider is @Service; neither
#   is a controller, so neither contributes endpoints. PetclinicTools exposes
#   @Tool methods to the LLM, which are not HTTP endpoints.
#
# api-gateway would be 2 (GET /api/gateway/owners/{ownerId}, POST /fallback) and
# the three platform servers 0, but none of them is in G.

HAND_NOE = {
    "customers-service": 8.0,
    "genai-service": 1.0,
    "vets-service": 1.0,
    "visits-service": 3.0,
}

# ---------------------------------------------------------------------------
# SHARED_DB — exists p in P(s1) ∩ P(s2), s1 != s2
# ---------------------------------------------------------------------------
# The snapshot's only source of store *identity* is the DDL each module ships.
#
#   customers-service/src/main/resources/db/mysql/schema.sql
#   vets-service/src/main/resources/db/mysql/schema.sql
#   visits-service/src/main/resources/db/mysql/schema.sql
#
# All three open with `CREATE DATABASE IF NOT EXISTS petclinic; USE petclinic;`
# and create their tables inside it. Under the mysql profile the three services
# share one schema, so SHARED_DB fires for all three.
#
# Corroboration: visits' DDL declares
#   FOREIGN KEY (pet_id) REFERENCES pets(id)
# and never creates `pets` — it is customers-service's table. A foreign key
# across a service boundary is only possible inside one schema.
#
# genai-service has spring-boot-starter-data-jpa, hsqldb and mysql-connector-j
# on its classpath but declares no @Entity, no repository and no DDL, so it owns
# no store: 0, not 1. Driver presence is not persistence.
#
# The hsqldb DDL names no database, and the JDBC URL that would identify it
# lives in the external configuration repository, which is not part of this
# checkout. That is recorded as an evidence gap rather than assumed distinct.

HAND_SHARED_DB = {
    "customers-service": 1.0,
    "genai-service": 0.0,
    "vets-service": 1.0,
    "visits-service": 1.0,
}


@pytest.mark.parametrize(
    "metric,expected",
    [("AIS", HAND_AIS), ("ADS", HAND_ADS), ("NOE", HAND_NOE), ("SHARED_DB", HAND_SHARED_DB)],
)
def test_metric_matches_hand_derivation(values, metric, expected):
    computed = {
        name: value.value for (m, name), value in values.items() if m == metric
    }
    assert computed == expected


def test_shared_db_names_the_store_it_found(values):
    for service in ("customers-service", "vets-service", "visits-service"):
        assert values[("SHARED_DB", service)].note == "shares petclinic/store/petclinic@mysql"


def test_hsqldb_store_identity_recorded_as_a_gap(model):
    gaps = {g.subject.split("/")[-1] for g in model.evidence_gaps if g.concern == "store-identity:hsqldb"}
    assert gaps == {"customers-service", "vets-service", "visits-service"}


def test_cross_schema_foreign_key_recorded(model):
    gaps = [g for g in model.evidence_gaps if g.concern == "cross-schema-foreign-key"]
    assert len(gaps) == 1
    assert gaps[0].subject == "petclinic/service/visits-service"
    assert "pets" in gaps[0].reason


# ---------------------------------------------------------------------------
# DD-001 identity and output determinism
# ---------------------------------------------------------------------------

def test_ids_follow_dd001(model):
    assert model.service_by_name("vets-service").id == "petclinic/service/vets-service"
    ids = {e.id for e in model.endpoints}
    assert "petclinic/endpoint/customers-service#GET:/owners/{ownerId}" in ids
    assert "petclinic/edge/api-gateway->vets-service:sync" in {d.id for d in model.dependencies}
    assert model.stores[0].id == "petclinic/store/petclinic"


def test_no_snapshot_component_in_any_id(model):
    for element in list(model.services) + list(model.endpoints) + list(model.dependencies):
        assert SNAPSHOT not in element.id
        assert SNAPSHOT[:8] not in element.id


def test_no_absolute_paths_in_emitted_artifacts(model):
    """Determinism: nothing in the model may embed the machine it ran on."""
    assert HERE not in str(model.to_dict())


def test_profile_is_in_the_documented_long_format(model, graph):
    rows = to_rows(model, graph, compute_all(model, graph))
    for column in ("system", "snapshot", "element_id", "element_kind", "metric", "value"):
        assert column in rows[0]
    assert {r["system"] for r in rows} == {"petclinic"}
    assert {r["snapshot"] for r in rows} == {SNAPSHOT}
    # Catalogue 0.2.0 added SCF, which attaches to the system rather than to a
    # service. `element_kind` stops being a constant here, which is the point of
    # having the column at all.
    assert {r["element_kind"] for r in rows} == {"service", "system"}
    assert rows == sorted(rows, key=lambda r: (r["metric"], r["element_id"]))
    service_metrics = {r["metric"] for r in rows if r["element_kind"] == "service"}
    system_metrics = {r["metric"] for r in rows if r["element_kind"] == "system"}
    assert system_metrics == {"SCF"}
    # every service-level metric on each of the 4 functional services, plus SCF
    assert len(rows) == len(service_metrics) * 4 + 1


def test_extraction_is_deterministic():
    first = extract(REPO, "petclinic", SNAPSHOT, RegexStaticAnalyser())
    second = extract(REPO, "petclinic", SNAPSHOT, RegexStaticAnalyser())
    assert first == second
