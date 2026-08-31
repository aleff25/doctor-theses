"""The static-analysis seam, and the route parsing the Python side does.

The point of `StaticAnalyser` is that a JVM analyser can replace the Python one
without any other module noticing. The stub below is what a Spoon/JavaParser
process would look like from this side of the boundary: a name and a dict of
facts. If this test needs anything from `static_regex`, the seam has leaked.
"""

from __future__ import annotations

import os

import pytest

from aam4j_extractor.bundle import extract
from aam4j_extractor.static_regex import RegexStaticAnalyser, join_route
from aam4j_extractor.spi import StaticFacts
from aam4j_model.build import build

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(HERE, "subjects", "petclinic")
SNAPSHOT = "305a1f13e4f961001d4e6cb50a9db51dc3fc5967"


class StubAnalyser:
    """Stands in for a JVM analyser: emits one endpoint per module and nothing else."""

    name = "stub/1.0.0"

    def analyse(self, module_name: str, module_root: str, repo_root: str) -> StaticFacts:
        return {
            "endpoints": [
                {
                    "module": module_name,
                    "http_method": "GET",
                    "route_template": "/stub",
                    "declaring_type": "Stub",
                    "source": {"file": "stub.java", "line": 1},
                }
            ],
            "calls": [],
            "entities": [],
            "type_annotations": [],
        }


@pytest.mark.skipif(not os.path.isdir(REPO), reason="run subjects/fetch_subjects.sh first")
def test_analyser_is_swappable_without_touching_downstream_stages():
    bundle = extract(REPO, "petclinic", SNAPSHOT, StubAnalyser())
    model = build(bundle)
    assert model.provenance["static_analyser"] == "stub/1.0.0"
    # One stub endpoint per reactor module, and role classification still works
    # off configuration and POM evidence even with no Java facts at all.
    assert len(model.endpoints) == 8
    assert model.service_by_name("api-gateway").role_rule == "R4-edge-gateway"
    # R3 needs @EnableAdminServer, which the stub does not emit: the rule set
    # degrades to the default rather than guessing.
    assert model.service_by_name("admin-server").role_rule == "default"


@pytest.mark.parametrize(
    "prefix,suffix,expected",
    [
        ("/owners", "/{ownerId}", "/owners/{ownerId}"),
        ("/owners", "", "/owners"),
        ("", "owners/*/pets/{petId}", "/owners/*/pets/{petId}"),
        ("/", "/chatclient", "/chatclient"),
        ("/api/gateway", "owners/{ownerId}", "/api/gateway/owners/{ownerId}"),
        ("", "", "/"),
    ],
)
def test_route_templates_are_normalised(prefix, suffix, expected):
    assert join_route(prefix, suffix) == expected


@pytest.mark.skipif(not os.path.isdir(REPO), reason="run subjects/fetch_subjects.sh first")
def test_licence_header_urls_are_not_mistaken_for_service_calls():
    """Every PetClinic source file opens with an Apache licence URL. A dotted
    host is an external address, never an in-system service name."""
    bundle = extract(REPO, "petclinic", SNAPSHOT, RegexStaticAnalyser())
    targets = {d["target_hint"] for d in bundle["static"]["declared_dependencies"]}
    assert targets == {"customers-service", "vets-service", "visits-service"}
