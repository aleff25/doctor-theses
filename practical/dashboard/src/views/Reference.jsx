import { useData } from '../data/DataContext'

/**
 * One bibliography entry.
 *
 * Every reference in `content/references.json` was checked against Crossref or
 * the publisher before it was written down, and each carries a note saying what
 * it is being cited *for*. A citation that only proves a sentence was written
 * by someone else is not worth the line.
 */
export default function Reference({ id }) {
  const { refs } = useData()
  const entry = refs[id]
  if (!entry) return <div className="ref">Unknown reference: {id}</div>

  return (
    <div className="ref">
      <div>
        {entry.authors} ({entry.year}). <span className="t">{entry.title}</span>. {entry.venue}.
        {entry.doi ? (
          <>
            {' '}
            <a href={entry.url} target="_blank" rel="noreferrer" className="mono">
              doi:{entry.doi}
            </a>
          </>
        ) : entry.url ? (
          <>
            {' '}
            <a href={entry.url} target="_blank" rel="noreferrer">
              link
            </a>
          </>
        ) : null}
      </div>
      {entry.note ? <div className="muted small">{entry.note}</div> : null}
    </div>
  )
}
