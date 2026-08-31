"""Configuration evidence — Spring `application*.yml` and Docker Compose.

Only `src/main/resources` is read. Test configuration (`src/test/resources`)
describes a test harness, not the architecture, and including it would invent
dependencies that no deployment has.
"""

from __future__ import annotations

import os
import re

import yaml

_LB_URI_RE = re.compile(r"^lb://(?P<service>[A-Za-z0-9_-]+)")
_CONFIGSERVER_IMPORT_RE = re.compile(r"configserver:(?P<uri>\S+)")


def load_yaml_documents(path: str) -> list[dict]:
    """All documents of a possibly multi-document YAML file, dicts only.

    Spring profile blocks are separate documents in one file, so a single-doc
    load silently drops the `docker` profile.
    """
    with open(path, encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if isinstance(doc, dict)]


def _walk(node, path: tuple[str, ...] = ()):
    """Depth-first walk yielding (dotted-path, node) for every mapping node."""
    if isinstance(node, dict):
        yield path, node
        for key in sorted(node, key=str):
            yield from _walk(node[key], path + (str(key),))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk(item, path + (str(index),))


def _flat_get(document: dict, dotted: str):
    """Read a dotted property, tolerating both nested and flattened YAML.

    `server.port: 8888` and a nested `server:\\n  port: 8888` are the same
    property to Spring but different trees to a YAML parser.
    """
    if dotted in document:
        return document[dotted]
    node = document
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        # A flattened prefix may absorb several segments.
        if part in node:
            node = node[part]
            continue
        return None
    return node


def gateway_routes(documents: list[dict]) -> list[dict[str, str]]:
    """Spring Cloud Gateway routes, wherever the version of the day nests them.

    Between Spring Cloud releases the key moved
    (`spring.cloud.gateway.routes` -> `spring.cloud.gateway.server.webflux.routes`),
    so this matches on shape — a `routes` list whose items carry a `uri` — rather
    than on a fixed path.
    """
    found: list[dict[str, str]] = []
    for document in documents:
        for _path, node in _walk(document):
            routes = node.get("routes")
            if not isinstance(routes, list):
                continue
            for route in routes:
                if not isinstance(route, dict) or "uri" not in route:
                    continue
                match = _LB_URI_RE.match(str(route["uri"]))
                if not match:
                    continue
                found.append(
                    {
                        "route_id": str(route.get("id", match.group("service"))),
                        "target": match.group("service"),
                        "uri": str(route["uri"]),
                    }
                )
    return sorted(found, key=lambda r: (r["target"], r["route_id"]))


def config_server_imports(documents: list[dict]) -> bool:
    """Whether the module imports its configuration from a config server."""
    for document in documents:
        imports = _flat_get(document, "spring.config.import")
        if imports and _CONFIGSERVER_IMPORT_RE.search(str(imports)):
            return True
    return False


def application_name(documents: list[dict]) -> str | None:
    for document in documents:
        name = _flat_get(document, "spring.application.name")
        if isinstance(name, str):
            return name
    return None


def read_module_config(module_dir: str) -> list[dict]:
    path = os.path.join(module_dir, "src", "main", "resources", "application.yml")
    if not os.path.exists(path):
        path = os.path.join(module_dir, "src", "main", "resources", "application.yaml")
    if not os.path.exists(path):
        return []
    return load_yaml_documents(path)


def read_compose(repo_root: str) -> list[dict]:
    """Docker Compose services, as deployment-unit facts.

    `depends_on` is recorded as declared configuration evidence. It is a
    start-ordering constraint, not a call — kept distinct from code-derived
    calls by its `mechanism`, so the model layer can decide what it means.
    """
    path = os.path.join(repo_root, "docker-compose.yml")
    if not os.path.exists(path):
        return []
    documents = load_yaml_documents(path)
    if not documents:
        return []
    services = documents[0].get("services") or {}
    units: list[dict] = []
    for name in sorted(services):
        spec = services[name] or {}
        depends = spec.get("depends_on") or {}
        if isinstance(depends, dict):
            depends_on = sorted(depends)
        else:
            depends_on = sorted(str(d) for d in depends)
        units.append(
            {
                "container_name": str(spec.get("container_name", name)),
                "compose_service": name,
                "image": str(spec["image"]) if "image" in spec else None,
                "build": str(spec["build"]) if "build" in spec else None,
                "ports": sorted(str(p) for p in (spec.get("ports") or [])),
                "depends_on": depends_on,
            }
        )
    return units
