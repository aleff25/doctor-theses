# metamodel/ — Obj. 1 / T2 · gap G1 · RQ1

The technology-agnostic architectural metamodel for Java-based distributed systems.

**In:** extraction bundles from `extractor/` (JSON, one file per evidence class)
**Out:** `.xmi` model instances, one per (system, snapshot), conforming to the Ecore metamodel here

## Scope

Must represent, per SLR §5.3.1 of the proposal and RQ1:

- Services — identity, domain responsibility, implementation technology
- Interfaces and endpoints — REST controllers, messaging channels
- Communication — synchronous calls, asynchronous exchange, event subscriptions; declared vs observed
- Persistence — stores and which service owns them (needed for `SHARED_DB`)
- Deployment — containers, hosts, clusters, replication

## Acceptance criteria

1. All three subject systems can be represented without extending the metamodel per system. If
   TeaStore (Tomcat/WAR) needs concepts that PetClinic (Spring Boot) does not, the metamodel is not
   yet technology-agnostic — that is the point of including TeaStore.
2. Every metric in `docs/03-metric-catalogue.md` is expressible as OCL over it.
3. `element_id` is stable across snapshots of the same system.

## Open decision — settle before writing the extractor

The `element_id` scheme. Everything downstream references it, and changing it later invalidates
every stored model instance, metric profile and label set.
