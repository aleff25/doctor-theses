import { formatValue, useData } from '../data/DataContext'
import { useTooltip } from './Tooltip'

/**
 * A metric value with its definition one hover away.
 *
 * The badge carries the three states the catalogue distinguishes, because a
 * reader who cannot tell them apart will read the third as the second:
 *
 *   determined value   plain badge
 *   fired predicate    highlighted (a smell that holds on this element)
 *   undetermined       dashed border and `n/d`, never 0
 */
export default function MetricBadge({ metric, value, determined = true, note = '' }) {
  const { metricById } = useData()
  const { show, hide } = useTooltip()
  const definition = metricById[metric]
  const fires = determined && definition?.group?.startsWith('E.') && value === 1

  const className = ['mbadge', determined ? '' : 'nd', fires ? 'fires' : ''].filter(Boolean).join(' ')

  const content = (
    <>
      <div className="t-head">
        <b>{metric}</b>
        <span>{definition ? definition.name : 'unknown metric'}</span>
      </div>
      {definition ? (
        <>
          <div className="t-formula">{definition.formula}</div>
          <p>{definition.plain}</p>
          <p>
            <strong>High means:</strong> {definition.high_means}
          </p>
          {note ? (
            <p>
              <strong>This element:</strong> {note}
            </p>
          ) : null}
          <div className="t-foot">
            {definition.group} · reads {definition.reads.join(', ')} · click through to Metrics for
            the limitations
          </div>
        </>
      ) : (
        <p>No catalogue entry. The dashboard generator should have refused to build.</p>
      )}
    </>
  )

  return (
    <span
      className={className}
      tabIndex={0}
      onMouseEnter={(event) => show(event.currentTarget, content)}
      onMouseLeave={hide}
      onFocus={(event) => show(event.currentTarget, content)}
      onBlur={hide}
    >
      <b>{metric}</b>
      <span className="v">{formatValue(value)}</span>
    </span>
  )
}
