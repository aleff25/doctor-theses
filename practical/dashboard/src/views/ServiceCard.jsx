import Code from '../ui/Code'
import Expandable from '../ui/Expandable'
import MetricBadge from '../ui/MetricBadge'
import { formatValue, useData } from '../data/DataContext'

function shortName(id) {
  return id.split('/').pop()
}

/**
 * One service, with every number traced back to the code that produced it.
 *
 * The order of the sections is the order of the argument: what this service is
 * (role, and the rule that decided it), what it measures, and then the evidence
 * behind each measurement. A dependency is not listed as an arrow; it is listed
 * with the Java statement that declared it.
 */
export default function ServiceCard({ service }) {
  const { data } = useData()
  const roleRule = data.role_rules.find((rule) => rule.id === service.role_rule)
  const undetermined = service.metrics.filter((m) => !m.determined)

  const badges = (
    <span className="badges">
      {service.metrics.map((m) => (
        <MetricBadge key={m.metric} {...m} />
      ))}
    </span>
  )

  return (
    <Expandable
      title={<span className="mono">{service.name}</span>}
      subtitle={
        <>
          <span className={`chip ${service.in_graph ? 'accent' : ''}`}>{service.role}</span>{' '}
          {undetermined.length > 0 ? (
            <span className="chip warn">{undetermined.length} undetermined</span>
          ) : null}
          {service.gaps.length > 0 ? (
            <span className="chip stop">{service.gaps.length} evidence gap</span>
          ) : null}
        </>
      }
      badges={service.in_graph ? badges : <span className="chip">not in G</span>}
    >
      <div className="section-label">Role, and the rule that assigned it</div>
      <p className="small">
        <span className="chip mono">{service.role_rule}</span>{' '}
        {roleRule ? roleRule.rationale : 'No rule record.'}
      </p>
      {!service.in_graph ? (
        <div className="note warn small">
          <strong>Excluded from the metric graph by DD-002.</strong> Its edges are extracted and
          modelled, but every metric here is computed over functional services only. Including
          discovery and config servers would put them top of the AIS and betweenness rankings of
          every system, which is true and useless.
        </div>
      ) : null}
      {service.evidence.role_annotations.map((annotation) => (
        <Code
          key={annotation.annotation + annotation.java_type}
          snippet={annotation.snippet}
          caption={`@${annotation.annotation}`}
        />
      ))}

      {service.in_graph ? (
        <>
          <div className="section-label">Metric profile</div>
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th className="num">Value</th>
                  <th>What the pipeline recorded</th>
                </tr>
              </thead>
              <tbody>
                {service.metrics.map((m) => (
                  <tr key={m.metric}>
                    <td>
                      <MetricBadge {...m} />
                    </td>
                    <td className="num">{formatValue(m.value)}</td>
                    <td className="muted small">
                      {m.determined ? m.note || '—' : <span className="mono">{m.note}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {service.evidence.outbound.length > 0 ? (
        <>
          <div className="section-label">Calls out ({service.evidence.outbound.length}) · this is ADS</div>
          {service.evidence.outbound.map((edge) => (
            <EdgeBlock key={edge.other + edge.kind} edge={edge} direction="to" />
          ))}
        </>
      ) : null}

      {service.evidence.inbound.length > 0 ? (
        <>
          <div className="section-label">Called by ({service.evidence.inbound.length}) · this is AIS</div>
          {service.evidence.inbound.map((edge) => (
            <EdgeBlock key={edge.other + edge.kind} edge={edge} direction="from" />
          ))}
        </>
      ) : null}

      {service.evidence.endpoints.length > 0 ? (
        <>
          <div className="section-label">
            Endpoints ({service.evidence.endpoints.length}) · this is NOE
          </div>
          {service.evidence.endpoints.map((endpoint) => (
            <Expandable
              key={endpoint.http_method + endpoint.route_template}
              title={
                <span className="mono small">
                  {endpoint.http_method} {endpoint.route_template}
                </span>
              }
              subtitle={<span className="mono">{endpoint.declaring_type}</span>}
            >
              <Code snippet={endpoint.snippet} />
            </Expandable>
          ))}
        </>
      ) : null}

      {service.evidence.entities.length > 0 ? (
        <>
          <div className="section-label">
            Domain entities ({service.evidence.entities.length}) · this is NOD
          </div>
          {service.evidence.entities.map((entity) => (
            <Expandable
              key={entity.java_type}
              title={<span className="mono small">{entity.java_type}</span>}
              subtitle={<>table {entity.table}</>}
            >
              <Code snippet={entity.snippet} />
            </Expandable>
          ))}
        </>
      ) : null}

      {service.evidence.schemas.length > 0 ? (
        <>
          <div className="section-label">Persistence · this is SHARED_DB</div>
          {service.evidence.schemas.map((schema) => (
            <Expandable
              key={schema.vendor + schema.store_name}
              title={
                <span className="mono small">
                  {schema.store_name}@{schema.vendor}
                </span>
              }
              subtitle={`${schema.tables.length} tables${
                schema.foreign_tables.length
                  ? `, references ${schema.foreign_tables.join(', ')} it does not create`
                  : ''
              }`}
            >
              <p className="small muted mono wrap-anywhere">{schema.tables.join(', ')}</p>
              <Code snippet={schema.snippet} />
            </Expandable>
          ))}
        </>
      ) : null}

      {service.gaps.length > 0 ? (
        <>
          <div className="section-label">Evidence gaps</div>
          {service.gaps.map((gap) => (
            <div key={gap.concern + gap.reason} className="note stop small">
              <span className="chip mono">{gap.concern}</span> {gap.reason}
            </div>
          ))}
        </>
      ) : null}
    </Expandable>
  )
}

function EdgeBlock({ edge, direction }) {
  return (
    <div className="card" style={{ marginTop: 8 }}>
      <div className="badges">
        <span className="chip mono">
          {direction} {shortName(edge.other)}
        </span>
        <span className="chip">{edge.kind}</span>
        <span className="chip">{edge.provenance}</span>
        {edge.mechanisms.map((mechanism) => (
          <span key={mechanism} className="chip mono">
            {mechanism}
          </span>
        ))}
      </div>
      {edge.facts.length === 0 ? (
        <p className="small muted">
          No source fact recorded for this edge in the extraction bundle.
        </p>
      ) : (
        edge.facts.map((fact, index) => (
          <Code
            key={index}
            snippet={fact.snippet}
            caption={`${fact.evidence_class}${fact.detail ? ` · ${fact.detail}` : ''}`}
          />
        ))
      )}
    </div>
  )
}
