"""Pattern-matching Java analyser — the throwaway implementation of `StaticAnalyser`.

This reads Java source as text. It has no symbol table, no type resolution and
no understanding of inheritance, so it is only trustworthy on code that spells
its Spring mappings out literally, which PetClinic does. It exists to make the
vertical slice run end to end; it is expected to be replaced by a JVM analyser
behind the same SPI.

Known and accepted limitations, all of which a real AST analyser fixes:

- A route built by string concatenation from a non-literal is missed.
- Constants (`private static final String BASE = "/owners"`) are not resolved.
- Meta-annotations and inherited controller base classes are invisible.
- A target host held in a field is only found because the field initialiser is
  itself a literal (`VisitsServiceClient.hostname`); a host injected via
  `@Value` would be missed.
"""

from __future__ import annotations

import os
import re

from .spi import CallFact, EndpointFact, EntityFact, StaticFacts, TypeAnnotationFact

# Annotation -> HTTP method. `@RequestMapping` is handled separately because it
# is both the class-level prefix carrier and a method-level mapping.
_METHOD_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}

_CONTROLLER_ANNOTATIONS = {"RestController", "Controller"}

_ANNOTATION_RE = re.compile(r"^\s*@(\w+)\s*(\((.*)\))?\s*$")
_TYPE_DECL_RE = re.compile(
    r"^\s*(?:public\s+|final\s+|abstract\s+)*(?:class|interface|record|enum)\s+(\w+)"
)
_STRING_LITERAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_NAMED_ATTR_RE = re.compile(r'\b(?:value|path)\s*=\s*"((?:[^"\\]|\\.)*)"')
_REQUEST_METHOD_RE = re.compile(r"RequestMethod\.(\w+)")

# Inter-service call mechanisms.
_HTTP_URL_RE = re.compile(r'"https?://([A-Za-z0-9_.-]+)(?::\d+)?(/[^"]*)?"')
_DISCOVERY_RE = re.compile(r'getInstances\(\s*"([^"]+)"\s*\)')
_FEIGN_RE = re.compile(r'@FeignClient\s*\(([^)]*)\)')
_FEIGN_NAME_RE = re.compile(r'\b(?:name|value)\s*=\s*"([^"]+)"')

# Hosts that are never a service of the system under analysis.
_NON_SERVICE_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"})


def _annotation_path(args: str | None) -> str:
    """The route fragment a mapping annotation declares, '' if it declares none."""
    if not args:
        return ""
    named = _NAMED_ATTR_RE.search(args)
    if named:
        return named.group(1)
    # `@GetMapping("/x")` — a bare literal is the path only when no other
    # attribute claimed it. Anything with an `=` before the first literal is a
    # different attribute (produces, consumes, ...).
    stripped = args.strip()
    literal = _STRING_LITERAL_RE.search(stripped)
    if literal and "=" not in stripped[: literal.start()]:
        return literal.group(1)
    return ""


def join_route(prefix: str, suffix: str) -> str:
    """Join a class-level prefix and a method-level path into a route template.

    Always returns a leading slash and no trailing slash (except for the root
    route, which stays "/").
    """
    parts = [p.strip("/") for p in (prefix, suffix)]
    joined = "/".join(p for p in parts if p)
    return "/" + joined if joined else "/"


def _iter_java_files(module_root: str):
    main_java = os.path.join(module_root, "src", "main", "java")
    for dirpath, dirnames, filenames in os.walk(main_java):
        dirnames.sort()
        for filename in sorted(filenames):
            if filename.endswith(".java"):
                yield os.path.join(dirpath, filename)


def _leading_annotations(lines: list[str], type_decl_index: int) -> list[tuple[str, str | None, int]]:
    """Annotations in the contiguous block directly above a type declaration."""
    found: list[tuple[str, str | None, int]] = []
    i = type_decl_index - 1
    while i >= 0:
        line = lines[i]
        if not line.strip():
            i -= 1
            continue
        match = _ANNOTATION_RE.match(line)
        if not match:
            break
        found.append((match.group(1), match.group(3), i + 1))
        i -= 1
    found.reverse()
    return found


class RegexStaticAnalyser:
    """Reference `StaticAnalyser` for Spring Boot sources."""

    name = "python-regex/0.1.0"

    def analyse(self, module_name: str, module_root: str, repo_root: str) -> StaticFacts:
        endpoints: list[EndpointFact] = []
        calls: list[CallFact] = []
        entities: list[EntityFact] = []
        type_annotations: list[TypeAnnotationFact] = []

        for path in _iter_java_files(module_root):
            rel = os.path.relpath(path, repo_root)
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()

            self._scan_types(module_name, rel, lines, endpoints, entities, type_annotations)
            self._scan_calls(module_name, rel, lines, calls)

        return {
            "endpoints": sorted(
                endpoints, key=lambda e: (e["route_template"], e["http_method"], e["declaring_type"])
            ),
            "calls": sorted(calls, key=lambda c: (c["target_hint"], c["mechanism"], c["source"]["file"])),
            "entities": sorted(entities, key=lambda e: (e["table"], e["java_type"])),
            "type_annotations": sorted(type_annotations, key=lambda a: (a["java_type"], a["annotation"])),
        }

    def _scan_types(
        self,
        module_name: str,
        rel: str,
        lines: list[str],
        endpoints: list[EndpointFact],
        entities: list[EntityFact],
        type_annotations: list[TypeAnnotationFact],
    ) -> None:
        for index, line in enumerate(lines):
            decl = _TYPE_DECL_RE.match(line)
            if not decl:
                continue
            java_type = decl.group(1)
            annotations = _leading_annotations(lines, index)
            names = {name for name, _, _ in annotations}

            for name, args, line_no in annotations:
                type_annotations.append(
                    {
                        "module": module_name,
                        "java_type": java_type,
                        "annotation": name,
                        "source": {"file": rel, "line": line_no},
                    }
                )

            if "Entity" in names:
                table = java_type.lower()
                for name, args, _ in annotations:
                    if name == "Table":
                        named = _NAMED_ATTR_RE.search(args or "") or re.search(
                            r'\bname\s*=\s*"([^"]+)"', args or ""
                        )
                        if named:
                            table = named.group(1)
                entities.append(
                    {
                        "module": module_name,
                        "java_type": java_type,
                        "table": table,
                        "source": {"file": rel, "line": index + 1},
                    }
                )

            if names & _CONTROLLER_ANNOTATIONS:
                prefix = ""
                for name, args, _ in annotations:
                    if name == "RequestMapping":
                        prefix = _annotation_path(args)
                endpoints.extend(
                    self._scan_endpoints(module_name, rel, lines, index, java_type, prefix)
                )

    def _scan_endpoints(
        self,
        module_name: str,
        rel: str,
        lines: list[str],
        type_decl_index: int,
        java_type: str,
        prefix: str,
    ) -> list[EndpointFact]:
        """Method-level mappings inside a controller type.

        Scans from the type declaration to end of file. With one top-level type
        per file — the convention PetClinic follows — that is the type's body.
        """
        found: list[EndpointFact] = []
        for offset, line in enumerate(lines[type_decl_index + 1 :], start=type_decl_index + 2):
            match = _ANNOTATION_RE.match(line)
            if not match:
                continue
            name, args = match.group(1), match.group(3)
            if name in _METHOD_ANNOTATIONS:
                http_methods = [_METHOD_ANNOTATIONS[name]]
            elif name == "RequestMapping":
                verbs = _REQUEST_METHOD_RE.findall(args or "")
                http_methods = verbs or ["GET"]
            else:
                continue
            route = join_route(prefix, _annotation_path(args))
            for http_method in http_methods:
                found.append(
                    {
                        "module": module_name,
                        "http_method": http_method,
                        "route_template": route,
                        "declaring_type": java_type,
                        "source": {"file": rel, "line": offset},
                    }
                )
        return found

    def _scan_calls(
        self, module_name: str, rel: str, lines: list[str], calls: list[CallFact]
    ) -> None:
        for index, line in enumerate(lines, start=1):
            for host, _path in _HTTP_URL_RE.findall(line):
                if host in _NON_SERVICE_HOSTS or "." in host:
                    # A dotted host is an external endpoint (api.openai.com),
                    # not an in-system service name.
                    continue
                calls.append(
                    {
                        "module": module_name,
                        "target_hint": host,
                        "kind": "sync",
                        "mechanism": "http-client-literal-uri",
                        "source": {"file": rel, "line": index},
                    }
                )
            for target in _DISCOVERY_RE.findall(line):
                calls.append(
                    {
                        "module": module_name,
                        "target_hint": target,
                        "kind": "sync",
                        "mechanism": "discovery-client-lookup",
                        "source": {"file": rel, "line": index},
                    }
                )
            feign = _FEIGN_RE.search(line)
            if feign:
                named = _FEIGN_NAME_RE.search(feign.group(1)) or _STRING_LITERAL_RE.search(
                    feign.group(1)
                )
                if named:
                    calls.append(
                        {
                            "module": module_name,
                            "target_hint": named.group(1),
                            "kind": "sync",
                            "mechanism": "feign-client",
                            "source": {"file": rel, "line": index},
                        }
                    )
