"""DD-001 element identity.

    <system>/<kind>/<stable-name>

with no snapshot component. The snapshot is a property of the model instance.
Every ID-producing function in the codebase lives here so that the scheme has
exactly one implementation to change if DD-001 is ever revised.
"""

from __future__ import annotations

SERVICE = "service"
ENDPOINT = "endpoint"
EDGE = "edge"
STORE = "store"
DEPLOYMENT = "deployment"
ENTITY = "entity"
SYSTEM = "system"


def service_id(system: str, name: str) -> str:
    """`petclinic/service/vets-service`"""
    return f"{system}/{SERVICE}/{name}"


def endpoint_id(system: str, service: str, http_method: str, route_template: str) -> str:
    """`petclinic/endpoint/vets-service#GET:/vets/{vetId}`

    The route is the template, never a concrete instantiation.
    """
    return f"{system}/{ENDPOINT}/{service}#{http_method}:{route_template}"


def edge_id(system: str, source: str, target: str, kind: str) -> str:
    """`petclinic/edge/api-gateway->vets-service:sync`

    `kind` is part of the ID, so a sync and an async edge between the same pair
    are distinct elements.
    """
    return f"{system}/{EDGE}/{source}->{target}:{kind}"


def store_id(system: str, name: str) -> str:
    """`petclinic/store/vets-db`"""
    return f"{system}/{STORE}/{name}"


def deployment_id(system: str, name: str) -> str:
    """`petclinic/deployment/vets-service`"""
    return f"{system}/{DEPLOYMENT}/{name}"


def entity_id(system: str, service: str, java_type: str) -> str:
    """`petclinic/entity/customers-service#Owner`

    The Java type, not the table, because the table is the *mapping* and can
    change without the domain concept changing. DD-001's stable-name rule is
    satisfied by the owning service plus the type's simple name.
    """
    return f"{system}/{ENTITY}/{service}#{java_type}"


def system_id(system: str) -> str:
    """`petclinic/system/petclinic` — the element system-level metrics attach to."""
    return f"{system}/{SYSTEM}/{system}"
