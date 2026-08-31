"""The service graph `G = (S, D)` the metric catalogue is defined over.

DD-002: `G` contains **functional services only**, and the filter is applied
here, at metric time, never during extraction. Filtering a node also removes
every edge incident to it — an edge whose endpoint is not in `S` is not in
`D ⊆ S × S`.

By default only `declared` dependencies are in `G`, because that is the only
provenance this evidence configuration produces. `provenance` is a parameter
rather than an assumption so that adding telemetry does not change this module.
"""

from __future__ import annotations

from dataclasses import dataclass

from aam4j_model.model import DECLARED, FUNCTIONAL, ArchitectureModel


@dataclass(frozen=True)
class ServiceGraph:
    """`S` as service IDs, `D` as (source-id, target-id, kind) triples."""

    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]
    roles_included: tuple[str, ...]
    provenance_included: tuple[str, ...]

    def in_degree(self, node: str) -> int:
        return len({(s, t) for s, t, _ in self.edges if t == node})

    def out_degree(self, node: str) -> int:
        return len({(s, t) for s, t, _ in self.edges if s == node})


def build_graph(
    model: ArchitectureModel,
    roles: tuple[str, ...] = (FUNCTIONAL,),
    provenance: tuple[str, ...] = (DECLARED,),
) -> ServiceGraph:
    """`G` over `model`, restricted to `roles` and `provenance`.

    Note on degree counting: `AIS` and `ADS` are defined in the catalogue as
    `|{t : (t,s) in D}|` — a set of *services*, not of edges. A sync and an
    async edge between the same pair are two elements of `D` (DD-001) but one
    neighbour, so the degree helpers deduplicate on the pair. This distinction
    has no effect on PetClinic, which declares no async edges, and it will have
    one on any system that does.
    """
    included = {s.id for s in model.services if s.role in roles}
    edges = sorted(
        {
            (d.source, d.target, d.kind)
            for d in model.dependencies
            if d.provenance in provenance and d.source in included and d.target in included
        }
    )
    return ServiceGraph(
        nodes=tuple(sorted(included)),
        edges=tuple(edges),
        roles_included=tuple(sorted(roles)),
        provenance_included=tuple(sorted(provenance)),
    )


def _pairs(graph: "ServiceGraph") -> set[tuple[str, str]]:
    """`D` as distinct ordered service pairs.

    The catalogue defines `D` as a set of edges, and DD-001 makes a sync and an
    async edge between the same pair two elements. Every metric here that
    counts *relationships between services* (`SCF`, `DEG`, `BTW`, `CYC`)
    therefore deduplicates on the pair, exactly as `in_degree`/`out_degree`
    already do. `ASYNC%` is the one metric that must not, since its whole
    subject is the kind, and it counts edge elements instead.
    """
    return {(source, target) for source, target, _ in graph.edges}


def successors(graph: "ServiceGraph") -> dict[str, set[str]]:
    out: dict[str, set[str]] = {node: set() for node in graph.nodes}
    for source, target in _pairs(graph):
        out[source].add(target)
    return out


def neighbours(graph: "ServiceGraph") -> dict[str, set[str]]:
    """Undirected neighbourhood, for degree centrality."""
    out: dict[str, set[str]] = {node: set() for node in graph.nodes}
    for source, target in _pairs(graph):
        out[source].add(target)
        out[target].add(source)
    return out


def betweenness(graph: "ServiceGraph") -> dict[str, float]:
    """Brandes' algorithm on the unweighted directed graph.

    Unweighted because `docs/03-metric-catalogue.md` weights `PR` by observed
    call volume and this evidence configuration has no observed volume at all.
    Weighting is a parameter of a later version of this function, not a
    silent default: a betweenness that claims to be volume-weighted while
    running on declared edges would be a fabricated number.

    Normalised by `(n-1)(n-2)`, the number of ordered source/target pairs a
    node can sit between, so values are comparable across systems of different
    size. Undefined for `n < 3`; the caller reports that as undetermined.
    """
    nodes = list(graph.nodes)
    succ = successors(graph)
    score = {node: 0.0 for node in nodes}
    for start in nodes:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {node: [] for node in nodes}
        sigma = {node: 0.0 for node in nodes}
        distance = {node: -1 for node in nodes}
        sigma[start] = 1.0
        distance[start] = 0
        queue = [start]
        head = 0
        while head < len(queue):
            node = queue[head]
            head += 1
            stack.append(node)
            for neighbour in sorted(succ[node]):
                if distance[neighbour] < 0:
                    distance[neighbour] = distance[node] + 1
                    queue.append(neighbour)
                if distance[neighbour] == distance[node] + 1:
                    sigma[neighbour] += sigma[node]
                    predecessors[neighbour].append(node)
        delta = {node: 0.0 for node in nodes}
        while stack:
            node = stack.pop()
            for predecessor in predecessors[node]:
                delta[predecessor] += (sigma[predecessor] / sigma[node]) * (1.0 + delta[node])
            if node != start:
                score[node] += delta[node]
    size = len(nodes)
    if size < 3:
        return {node: 0.0 for node in nodes}
    scale = float((size - 1) * (size - 2))
    return {node: score[node] / scale for node in nodes}


def strongly_connected_components(graph: "ServiceGraph") -> list[tuple[str, ...]]:
    """Tarjan, iterative. Components are sorted so the output is deterministic."""
    succ = successors(graph)
    index_of: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    counter = 0
    components: list[tuple[str, ...]] = []

    for root in graph.nodes:
        if root in index_of:
            continue
        work: list[tuple[str, list[str]]] = [(root, sorted(succ[root]))]
        index_of[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack[root] = True
        while work:
            node, pending = work[-1]
            if pending:
                child = pending.pop()
                if child not in index_of:
                    index_of[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack[child] = True
                    work.append((child, sorted(succ[child])))
                elif on_stack.get(child):
                    low[node] = min(low[node], index_of[child])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index_of[node]:
                    component = []
                    while True:
                        member = stack.pop()
                        on_stack[member] = False
                        component.append(member)
                        if member == node:
                            break
                    components.append(tuple(sorted(component)))
    return sorted(components)


def cycle_members(graph: "ServiceGraph") -> dict[str, tuple[str, ...]]:
    """Every node that participates in a directed cycle, mapped to its cycle.

    A component of size > 1 is a cycle by definition; a single node is one only
    if it has a self-loop. `build()` drops self-dependencies, so self-loops can
    only reach here from a hand-built model, which is exactly where the case
    needs to be covered.
    """
    pairs = _pairs(graph)
    members: dict[str, tuple[str, ...]] = {}
    for component in strongly_connected_components(graph):
        if len(component) > 1:
            for node in component:
                members[node] = component
        elif (component[0], component[0]) in pairs:
            members[component[0]] = component
    return members
