"""Maven POM parsing — module discovery and declared library dependencies.

Module names come from `<artifactId>`, which DD-001 names as the source of
`stable-name`.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_POM_NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def _text(element, path: str) -> str | None:
    found = element.find(path, _POM_NS)
    return found.text.strip() if found is not None and found.text else None


@dataclass
class MavenModule:
    """One reactor module."""

    artifact_id: str
    path: str
    """Repo-relative directory of the module."""
    packaging: str
    dependencies: list[dict[str, str]] = field(default_factory=list)

    def has_dependency(self, artifact_id: str) -> bool:
        return any(d["artifact_id"] == artifact_id for d in self.dependencies)


def _parse_dependencies(root) -> list[dict[str, str]]:
    """Direct `<dependencies>` of the project, excluding `<dependencyManagement>`."""
    deps: list[dict[str, str]] = []
    block = root.find("m:dependencies", _POM_NS)
    if block is None:
        return deps
    for dep in block.findall("m:dependency", _POM_NS):
        artifact_id = _text(dep, "m:artifactId")
        if not artifact_id:
            continue
        deps.append(
            {
                "group_id": _text(dep, "m:groupId") or "",
                "artifact_id": artifact_id,
                "scope": _text(dep, "m:scope") or "compile",
            }
        )
    return sorted(deps, key=lambda d: (d["group_id"], d["artifact_id"]))


def read_module(module_dir: str, repo_root: str) -> MavenModule:
    root = ET.parse(os.path.join(module_dir, "pom.xml")).getroot()
    return MavenModule(
        artifact_id=_text(root, "m:artifactId") or os.path.basename(module_dir),
        path=os.path.relpath(module_dir, repo_root),
        packaging=_text(root, "m:packaging") or "jar",
        dependencies=_parse_dependencies(root),
    )


def discover_modules(repo_root: str) -> list[MavenModule]:
    """Reactor modules named by the root POM, in declaration-independent order.

    Only first-level `<modules>` are followed; PetClinic has no nested reactors.
    A nested reactor would need this to recurse, and Train Ticket will force
    that — flagged rather than pre-emptively built.
    """
    root = ET.parse(os.path.join(repo_root, "pom.xml")).getroot()
    modules_element = root.find("m:modules", _POM_NS)
    if modules_element is None:
        return []
    names = sorted(m.text.strip() for m in modules_element.findall("m:module", _POM_NS) if m.text)
    return [read_module(os.path.join(repo_root, name), repo_root) for name in names]
