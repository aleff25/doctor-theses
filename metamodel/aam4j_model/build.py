"""Extraction bundle -> architecture model instance.

This is where DD-002 role assignment happens and where declared dependency
facts from different evidence classes are merged into edge *elements* — merged
by identity, never by provenance: `declared` and `observed` stay apart.
"""

from __future__ import annotations

import json
import os

from . import ids
from .model import (
    DECLARED,
    METAMODEL_VERSION,
    ArchitectureModel,
    Dependency,
    DeploymentUnit,
    DomainEntity,
    Endpoint,
    EvidenceGap,
    PersistenceLink,
    Service,
    Store,
)
from .roles import RoleCatalogue, RoleEvidence


def load_bundle(bundle_dir: str) -> dict[str, dict]:
    bundle = {}
    for name in ("manifest", "static", "configuration"):
        with open(os.path.join(bundle_dir, f"{name}.json"), encoding="utf-8") as handle:
            bundle[name] = json.load(handle)
    return bundle


def _service_evidence(bundle: dict) -> dict[str, RoleEvidence]:
    """One `RoleEvidence` per candidate service, from every evidence class."""
    manifest, static, config = bundle["manifest"], bundle["static"], bundle["configuration"]

    annotations_by_service: dict[str, set[str]] = {}
    for annotation in static["type_annotations"]:
        annotations_by_service.setdefault(annotation["module"], set()).add(annotation["annotation"])

    routes_by_service = {m["service_name"]: bool(m["gateway_routes"]) for m in config["modules"]}

    evidence: dict[str, RoleEvidence] = {}
    for module in manifest["modules"]:
        name = module["service_name"]
        evidence[name] = RoleEvidence(
            name=name,
            has_source_module=True,
            maven_dependencies=frozenset(d["artifact_id"] for d in module["dependencies"]),
            type_annotations=frozenset(annotations_by_service.get(name, set())),
            declares_gateway_routes=routes_by_service.get(name, False),
        )

    # Deployment units with no reactor module are still services of the running
    # system. DD-002 says model everything and filter at metric time, so they
    # are modelled — rule R5 will classify them infrastructure.
    for unit in config["deployment_units"]:
        name = unit["container_name"]
        if name in evidence:
            continue
        evidence[name] = RoleEvidence(
            name=name,
            has_source_module=False,
            maven_dependencies=frozenset(),
            type_annotations=frozenset(),
            declares_gateway_routes=False,
        )
    return evidence


def build(bundle: dict[str, dict], catalogue: RoleCatalogue | None = None) -> ArchitectureModel:
    manifest, static, config = bundle["manifest"], bundle["static"], bundle["configuration"]
    catalogue = catalogue or RoleCatalogue.load()
    system, snapshot = manifest["system"], manifest["snapshot"]

    model = ArchitectureModel(
        system=system,
        snapshot=snapshot,
        metamodel_version=METAMODEL_VERSION,
        provenance={
            "bundle_schema_version": manifest["schema_version"],
            "static_analyser": manifest["static_analyser"],
            "role_catalogue_version": catalogue.version,
            "evidence_classes_present": manifest["evidence_classes_present"],
            "evidence_classes_absent": manifest["evidence_classes_absent"],
        },
    )

    modules_by_service = {m["service_name"]: m for m in manifest["modules"]}
    evidence = _service_evidence(bundle)

    for name in sorted(evidence):
        assignment = catalogue.classify(evidence[name])
        module = modules_by_service.get(name)
        model.services.append(
            Service(
                id=ids.service_id(system, name),
                name=name,
                role=assignment.role,
                role_rule=assignment.rule_id,
                technology="spring-boot" if module else "external-container",
                source_module=module["path"] if module else None,
                has_source_module=module is not None,
            )
        )

    known = {s.name for s in model.services}

    for endpoint in static["endpoints"]:
        service = endpoint["module"]
        model.endpoints.append(
            Endpoint(
                id=ids.endpoint_id(system, service, endpoint["http_method"], endpoint["route_template"]),
                service=ids.service_id(system, service),
                http_method=endpoint["http_method"],
                route_template=endpoint["route_template"],
            )
        )
    model.endpoints.sort(key=lambda e: e.id)

    # --- domain entities --------------------------------------------------
    # Metamodel 0.2.0-json. The declaring module owns the entity; an entity
    # declared by a module that is not a service in this model is dropped with
    # a gap rather than attributed to a guess.
    for entity in static["entities"]:
        service = entity["module"]
        if service not in known:
            model.evidence_gaps.append(
                EvidenceGap(
                    subject=entity["java_type"],
                    concern="entity-owner-resolution",
                    reason=f"declaring module {service!r} matches no service in the model",
                )
            )
            continue
        model.entities.append(
            DomainEntity(
                id=ids.entity_id(system, service, entity["java_type"]),
                service=ids.service_id(system, service),
                java_type=entity["java_type"],
                table=entity["table"],
            )
        )
    model.entities.sort(key=lambda e: e.id)

    # --- dependency edges -------------------------------------------------
    grouped: dict[tuple[str, str, str, str], dict] = {}
    for document in (static, config):
        for provenance, key in ((DECLARED, "declared_dependencies"),):
            for fact in document[key]:
                source, target = fact["source"], fact["target_hint"]
                if source not in known or target not in known:
                    model.evidence_gaps.append(
                        EvidenceGap(
                            subject=f"{source}->{target}",
                            concern="dependency-target-resolution",
                            reason=f"target hint {target!r} matches no service in the model",
                        )
                    )
                    continue
                if source == target:
                    continue
                slot = grouped.setdefault(
                    (source, target, fact["kind"], provenance),
                    {"mechanisms": set(), "evidence": []},
                )
                slot["mechanisms"].add(fact["mechanism"])
                slot["evidence"].append(
                    {
                        "evidence_class": document["evidence_class"],
                        "mechanism": fact["mechanism"],
                        "file": fact["evidence"]["file"],
                        "line": fact["evidence"]["line"],
                    }
                )

    for (source, target, kind, provenance), slot in sorted(grouped.items()):
        model.dependencies.append(
            Dependency(
                id=ids.edge_id(system, source, target, kind),
                source=ids.service_id(system, source),
                target=ids.service_id(system, target),
                kind=kind,
                provenance=provenance,
                mechanisms=sorted(slot["mechanisms"]),
                evidence=sorted(
                    slot["evidence"], key=lambda e: (e["evidence_class"], e["file"], e["line"], e["mechanism"])
                ),
            )
        )

    # --- persistence ------------------------------------------------------
    stores: dict[str, dict] = {}
    for declaration in static["schema_declarations"]:
        slot = stores.setdefault(declaration["store_name"], {"vendors": set(), "tables": set()})
        slot["vendors"].add(declaration["vendor"])
        slot["tables"].update(declaration["tables"])
        model.persistence_links.append(
            PersistenceLink(
                service=ids.service_id(system, declaration["module"]),
                store=ids.store_id(system, declaration["store_name"]),
                vendor=declaration["vendor"],
                access="owns-tables",
            )
        )
        if declaration["foreign_tables"]:
            model.evidence_gaps.append(
                EvidenceGap(
                    subject=ids.service_id(system, declaration["module"]),
                    concern="cross-schema-foreign-key",
                    reason=(
                        f"{declaration['vendor']} DDL references table(s) "
                        f"{', '.join(declaration['foreign_tables'])} it does not create"
                    ),
                )
            )
    for name in sorted(stores):
        model.stores.append(
            Store(
                id=ids.store_id(system, name),
                name=name,
                vendors=sorted(stores[name]["vendors"]),
                tables=sorted(stores[name]["tables"]),
            )
        )
    model.persistence_links.sort(key=lambda p: (p.vendor, p.service, p.store))

    for unresolved in static["schema_unresolved"]:
        model.evidence_gaps.append(
            EvidenceGap(
                subject=ids.service_id(system, unresolved["module"]),
                concern=f"store-identity:{unresolved['vendor']}",
                reason=unresolved["reason"],
            )
        )

    # --- deployment -------------------------------------------------------
    for unit in config["deployment_units"]:
        container = unit["container_name"]
        model.deployment_units.append(
            DeploymentUnit(
                id=ids.deployment_id(system, container),
                service=ids.service_id(system, container) if container in known else None,
                container=container,
                image=unit["image"],
                ports=unit["ports"],
            )
        )
    model.deployment_units.sort(key=lambda d: d.id)
    model.evidence_gaps.sort(key=lambda g: (g.concern, g.subject, g.reason))
    return model


def write_model(model: ArchitectureModel, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(model.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path
