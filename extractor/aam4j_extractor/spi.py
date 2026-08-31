"""Service-provider interface for the static-analysis step.

The static evidence class is the only part of extraction that genuinely needs a
Java front end. Everything else (POM XML, YAML, compose, DDL) is format parsing
that Python does as well as anything.

`StaticAnalyser` is therefore the seam. The Python implementation in
`static_regex.py` satisfies it with pattern matching over source text; a JVM
implementation (Spoon / JavaParser / JDT) can satisfy it by emitting the same
JSON over a subprocess boundary. Nothing downstream of `analyse()` may import
anything from a concrete analyser.

The return type is deliberately plain dicts rather than rich objects: the
boundary has to survive being serialised to JSON and handed to another process.
"""

from __future__ import annotations

from typing import Protocol, TypedDict


class SourceRef(TypedDict):
    """Where a fact was observed. Paths are repo-relative — never absolute."""

    file: str
    line: int


class EndpointFact(TypedDict):
    """One HTTP endpoint declared by a module.

    `route_template` is the route as written (`/owners/{ownerId}`), never a
    concrete instantiation — DD-001 requires template form in endpoint IDs.
    """

    module: str
    http_method: str
    route_template: str
    declaring_type: str
    source: SourceRef


class CallFact(TypedDict):
    """One outbound service call declared in code.

    `target_hint` is the logical service name as it appears in the source
    (`customers-service`), not a URL and not a host:port.
    """

    module: str
    target_hint: str
    kind: str  # "sync" | "async"
    mechanism: str  # e.g. "webclient", "restclient", "discovery-client", "feign"
    source: SourceRef


class EntityFact(TypedDict):
    """One persisted JPA entity, and the table it maps to."""

    module: str
    java_type: str
    table: str
    source: SourceRef


class TypeAnnotationFact(TypedDict):
    """A class-level annotation, used by the role-classification rules."""

    module: str
    java_type: str
    annotation: str
    source: SourceRef


class StaticFacts(TypedDict):
    endpoints: list[EndpointFact]
    calls: list[CallFact]
    entities: list[EntityFact]
    type_annotations: list[TypeAnnotationFact]


class StaticAnalyser(Protocol):
    """Anything that can turn a module's Java sources into static facts.

    Implementations must be deterministic: the same checkout must yield the
    same facts in the same order.
    """

    name: str
    """Identifier recorded in the bundle so a profile can be traced to the
    analyser that produced it."""

    def analyse(self, module_name: str, module_root: str, repo_root: str) -> StaticFacts:
        """Analyse one Maven module.

        `module_root` and `repo_root` are absolute filesystem paths; every path
        appearing in the returned facts must be relative to `repo_root`.
        """
        ...
