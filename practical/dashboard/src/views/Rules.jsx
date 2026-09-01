import { useState } from 'react'
import Expandable from '../ui/Expandable'
import Reference from './Reference'
import { useData } from '../data/DataContext'

const KINDS = [
  { id: 'all', label: 'Everything' },
  { id: 'design-decision', label: 'Design decisions' },
  { id: 'practice', label: 'Standing practices' },
]

/**
 * Why the pipeline does what it does, and what would have to change for it to
 * stop.
 *
 * Each card answers four questions in the same order, because a decision
 * recorded without its cost is advocacy rather than a record: what was decided,
 * why, what it costs, and when it should be revisited.
 */
export default function Rules() {
  const { data } = useData()
  const [kind, setKind] = useState('all')
  const rules = data.rules.filter((rule) => kind === 'all' || rule.kind === kind)

  return (
    <>
      <h1>Rules, and why they should change</h1>
      <p className="lede">
        Every rule below is enforced in code, not by convention, and every one of them costs
        something. Reversing a numbered design decision is a versioned change to the metamodel or
        the catalogue, never an edit, which is why each card carries the condition under which it
        should be reopened.
      </p>

      <div className="toolbar">
        <div className="seg">
          {KINDS.map((entry) => (
            <button key={entry.id} aria-pressed={kind === entry.id} onClick={() => setKind(entry.id)}>
              {entry.label}
            </button>
          ))}
        </div>
      </div>

      {rules.map((rule) => (
        <Expandable
          key={rule.id}
          title={<span className="mono">{rule.id}</span>}
          subtitle={rule.title}
          badges={
            <span className="badges">
              <span className="chip">{rule.kind}</span>
              <span className="chip mono">{rule.date}</span>
            </span>
          }
        >
          <div className="section-label">Decision</div>
          <p className="small">{rule.decision}</p>

          <div className="section-label">Why it exists</div>
          <p className="small">{rule.why}</p>

          <div className="section-label">What it costs</div>
          <div className="note warn small">{rule.cost}</div>

          <div className="section-label">When it should change</div>
          <div className="note accent small">{rule.revisit}</div>

          {rule.refs.length > 0 ? (
            <>
              <div className="section-label">References</div>
              {rule.refs.map((key) => (
                <Reference key={key} id={key} />
              ))}
            </>
          ) : null}

          <div className="section-label">Enforced in</div>
          <p className="small mono wrap-anywhere">{rule.source}</p>
        </Expandable>
      ))}

      <h2>Role classification (DD-002), rule by rule</h2>
      <p className="small muted">
        Read from <span className="mono">metamodel/catalogue/roles.yaml</span>, in evaluation order,
        first match wins. Every classified service records the id of the rule that fired, so any
        figure can be audited back to the evidence that produced it. This is catalogue data rather
        than code precisely so it can be revised without touching the metric layer.
      </p>
      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>Assigns</th>
              <th>Fires when</th>
              <th>Rationale</th>
              <th className="num">Services</th>
            </tr>
          </thead>
          <tbody>
            {data.role_rules.map((rule) => {
              const count = data.systems.reduce(
                (total, system) =>
                  total + system.services.filter((s) => s.role_rule === rule.id).length,
                0,
              )
              return (
                <tr key={rule.id}>
                  <td className="mono">{rule.id}</td>
                  <td>
                    <span className={`chip ${rule.role === 'functional' ? 'accent' : ''}`}>
                      {rule.role}
                    </span>
                  </td>
                  <td className="mono small wrap-anywhere">
                    {rule.condition ? JSON.stringify(rule.condition) : '—'}
                  </td>
                  <td className="small">{rule.rationale}</td>
                  <td className="num">{count}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <h2>Thresholds in force</h2>
      <p className="small muted">
        Threshold set <span className="mono">{data.thresholds.version}</span>. Method:{' '}
        {data.thresholds.method || 'not recorded'}. Derived from{' '}
        {data.thresholds.derived_from.map((d) => d.system).join(', ')}.
      </p>
      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th>Smell</th>
              <th>Input</th>
              <th className="num">Threshold</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.thresholds.by_smell).flatMap(([smell, entries]) =>
              Object.entries(entries).map(([metric, entry]) => (
                <tr key={`${smell}.${metric}`}>
                  <td className="mono">{smell}</td>
                  <td className="mono">{metric}</td>
                  <td className="num">{entry.determined ? entry.value : 'refused'}</td>
                  <td className="small">
                    {entry.determined ? (
                      <span className="chip accent">derived</span>
                    ) : (
                      <>
                        <span className="chip stop">refused</span> {entry.reason}
                      </>
                    )}
                  </td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>

      <h2>All references</h2>
      {Object.keys(data.references)
        .sort((a, b) => data.references[a].year - data.references[b].year)
        .map((key) => (
          <Reference key={key} id={key} />
        ))}
    </>
  )
}
