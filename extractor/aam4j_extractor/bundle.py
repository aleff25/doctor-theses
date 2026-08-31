"""Assembly of the ①→② extraction bundle.

Emits one JSON file per evidence class, per the data contract in
`docs/01-pipeline.md`:

    static.json         POMs, Java annotations, schema DDL
    configuration.json  application.yml, docker-compose.yml
    manifest.json       what was extracted, from which snapshot, by which analyser

Two rules the extractor README makes non-negotiable and that are enforced here:

1. **Declared and observed dependencies never merge.** They are separate arrays.
   This pass produces no observed dependencies at all — the array is present and
   empty, so a consumer can tell "no telemetry was supplied" apart from "the key
   does not exist in this schema version".
2. **Nothing is filtered at extraction time.** DD-002 puts the infrastructure
   filter at the metric layer. The extractor records everything it sees,
   including Zipkin, Prometheus and Grafana containers that have no Maven module.
"""

from __future__ import annotations

import json
import os

from . import configuration as cfg
from . import maven, persistence
from .spi import StaticAnalyser

BUNDLE_SCHEMA_VERSION = "0.1.0"

_PROJECT_PREFIX = "spring-petclinic-"


def _short_name(module: maven.MavenModule, documents: list[dict], compose_by_module: dict) -> tuple[str, str]:
    """The module's stable service name, and the evidence that produced it.

    DD-001 requires the name to come from the deployment/module name. Three
    sources agree in PetClinic; the order below prefers the one that survives
    a module directory rename.
    """
    declared = cfg.application_name(documents)
    if declared:
        return declared, "spring.application.name"
    unit = compose_by_module.get(module.artifact_id)
    if unit and unit["container_name"]:
        return unit["container_name"], "docker-compose container_name"
    name = module.artifact_id
    if name.startswith(_PROJECT_PREFIX):
        name = name[len(_PROJECT_PREFIX) :]
    return name, "maven artifactId"


def _configserver_hosts(documents: list[dict]) -> list[str]:
    """Hosts named in `spring.config.import: configserver:...`, excluding local."""
    hosts = set()
    for document in documents:
        imports = cfg._flat_get(document, "spring.config.import")
        if not imports:
            continue
        for match in cfg._CONFIGSERVER_IMPORT_RE.finditer(str(imports)):
            uri = match.group("uri")
            host = uri.split("//")[-1].split("/")[0].split(":")[0]
            if host and host not in ("localhost", "127.0.0.1") and not host.startswith("$"):
                hosts.add(host)
    return sorted(hosts)


def extract(repo_root: str, system: str, snapshot: str, analyser: StaticAnalyser) -> dict[str, dict]:
    """Extract `system` at `snapshot` from `repo_root` into bundle documents."""
    modules = maven.discover_modules(repo_root)
    compose_units = cfg.read_compose(repo_root)

    # A compose unit belongs to a module when its image basename is the
    # module's artifactId. Units with no match are infrastructure containers
    # that have no source in this repository (Zipkin, Prometheus, Grafana).
    compose_by_module: dict[str, dict] = {}
    for unit in compose_units:
        image = unit.get("image") or ""
        basename = image.split("/")[-1].split(":")[0]
        if any(basename == m.artifact_id for m in modules):
            compose_by_module[basename] = unit

    module_docs = {m.artifact_id: cfg.read_module_config(os.path.join(repo_root, m.path)) for m in modules}
    names: dict[str, str] = {}
    module_records: list[dict] = []

    for module in modules:
        documents = module_docs[module.artifact_id]
        short, name_evidence = _short_name(module, documents, compose_by_module)
        names[module.artifact_id] = short
        module_records.append(
            {
                "artifact_id": module.artifact_id,
                "service_name": short,
                "service_name_evidence": name_evidence,
                "path": module.path,
                "packaging": module.packaging,
                "dependencies": module.dependencies,
            }
        )

    # The service that *is* the discovery server, found by its starter rather
    # than by name, so the edge below is evidence-derived and not hardcoded.
    eureka_servers = sorted(
        names[m.artifact_id]
        for m in modules
        if m.has_dependency("spring-cloud-starter-netflix-eureka-server")
    )

    static_facts: dict[str, list] = {
        "endpoints": [],
        "calls": [],
        "entities": [],
        "type_annotations": [],
        "schema_declarations": [],
        "schema_unresolved": [],
    }
    config_declared: list[dict] = []
    module_config_records: list[dict] = []

    for module in modules:
        module_dir = os.path.join(repo_root, module.path)
        short = names[module.artifact_id]
        facts = analyser.analyse(short, module_dir, repo_root)
        for key in ("endpoints", "calls", "entities", "type_annotations"):
            static_facts[key].extend(facts[key])

        schemas = persistence.read_module_schemas(short, module_dir, repo_root)
        static_facts["schema_declarations"].extend(schemas["declarations"])
        static_facts["schema_unresolved"].extend(schemas["unresolved"])

        documents = module_docs[module.artifact_id]
        routes = cfg.gateway_routes(documents)
        module_config_records.append(
            {
                "service_name": short,
                "application_name": cfg.application_name(documents),
                "gateway_routes": routes,
                "imports_config_server": cfg.config_server_imports(documents),
                "profiles_declared": sorted(
                    {
                        str(cfg._flat_get(d, "spring.config.activate.on-profile"))
                        for d in documents
                        if cfg._flat_get(d, "spring.config.activate.on-profile")
                    }
                ),
            }
        )

        source_ref = {"file": os.path.join(module.path, "src/main/resources/application.yml"), "line": 0}
        for route in routes:
            config_declared.append(
                {
                    "source": short,
                    "target_hint": route["target"],
                    "kind": "sync",
                    "mechanism": "gateway-route",
                    "detail": route["route_id"],
                    "evidence": source_ref,
                }
            )
        for host in _configserver_hosts(documents):
            config_declared.append(
                {
                    "source": short,
                    "target_hint": host,
                    "kind": "sync",
                    "mechanism": "config-server-import",
                    "detail": "spring.config.import",
                    "evidence": source_ref,
                }
            )
        if module.has_dependency("spring-cloud-starter-netflix-eureka-client"):
            for server in eureka_servers:
                config_declared.append(
                    {
                        "source": short,
                        "target_hint": server,
                        "kind": "sync",
                        "mechanism": "eureka-registration",
                        "detail": "spring-cloud-starter-netflix-eureka-client",
                        "evidence": {"file": os.path.join(module.path, "pom.xml"), "line": 0},
                    }
                )

    # Compose `depends_on` is a start-ordering constraint. It is recorded with a
    # mechanism of its own so the model layer can weigh it differently from a
    # code-derived call rather than having to guess what it was.
    for unit in compose_units:
        for target in unit["depends_on"]:
            config_declared.append(
                {
                    "source": unit["container_name"],
                    "target_hint": target,
                    "kind": "sync",
                    "mechanism": "compose-depends-on",
                    "detail": "start ordering, not a call",
                    "evidence": {"file": "docker-compose.yml", "line": 0},
                }
            )

    static_declared = [
        {
            "source": call["module"],
            "target_hint": call["target_hint"],
            "kind": call["kind"],
            "mechanism": call["mechanism"],
            "detail": None,
            "evidence": call["source"],
        }
        for call in static_facts["calls"]
    ]

    def _dep_key(d):
        return (d["source"], d["target_hint"], d["kind"], d["mechanism"], d["evidence"]["file"], d["evidence"]["line"])

    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "system": system,
        "snapshot": snapshot,
        "evidence_classes_present": ["configuration", "static"],
        "evidence_classes_absent": ["metrics", "traces"],
        "static_analyser": analyser.name,
        "modules": sorted(module_records, key=lambda m: m["artifact_id"]),
    }

    static_document = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "system": system,
        "snapshot": snapshot,
        "evidence_class": "static",
        "endpoints": sorted(
            static_facts["endpoints"], key=lambda e: (e["module"], e["route_template"], e["http_method"])
        ),
        "entities": sorted(static_facts["entities"], key=lambda e: (e["module"], e["table"])),
        "type_annotations": sorted(
            static_facts["type_annotations"], key=lambda a: (a["module"], a["java_type"], a["annotation"])
        ),
        "schema_declarations": sorted(
            static_facts["schema_declarations"], key=lambda s: (s["module"], s["vendor"])
        ),
        "schema_unresolved": sorted(
            static_facts["schema_unresolved"], key=lambda s: (s["module"], s["vendor"])
        ),
        "declared_dependencies": sorted(static_declared, key=_dep_key),
        "observed_dependencies": [],
    }

    configuration_document = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "system": system,
        "snapshot": snapshot,
        "evidence_class": "configuration",
        "modules": sorted(module_config_records, key=lambda m: m["service_name"]),
        "deployment_units": compose_units,
        "declared_dependencies": sorted(config_declared, key=_dep_key),
        "observed_dependencies": [],
    }

    return {
        "manifest": manifest,
        "static": static_document,
        "configuration": configuration_document,
    }


def write_bundle(bundle: dict[str, dict], out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name in sorted(bundle):
        path = os.path.join(out_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(bundle[name], handle, indent=2, sort_keys=True)
            handle.write("\n")
        written.append(path)
    return written
