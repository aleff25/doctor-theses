/**
 * A snippet lifted from the pinned clone of a subject system.
 *
 * The evidence line is highlighted, because the point of showing code here is
 * to answer "which statement produced this number", not to browse a file. When
 * the generator could not read the clone, the file and line are still shown:
 * that is enough to find the code by hand, and pretending there is no evidence
 * would be worse than showing where it lives.
 */
export default function Code({ snippet, caption }) {
  if (!snippet) return null
  const { file, line, start_line: start, lines } = snippet

  return (
    <div className="code">
      <div className="code-head">
        {caption ? <span>{caption}</span> : null}
        <span className="path" title={file}>
          {file}
        </span>
        <span className="right">{line > 0 ? `line ${line}` : 'file-level evidence'}</span>
      </div>
      {lines ? (
        <pre>
          {lines.map((text, index) => {
            const number = start + index
            return (
              <div key={number} className={`ln${number === line ? ' hit' : ''}`}>
                <span className="n">{number}</span>
                <span className="c">{text || ' '}</span>
              </div>
            )
          })}
        </pre>
      ) : (
        <div className="missing">
          Source not read. Run <span className="mono">./subjects/fetch_subjects.sh</span> and
          regenerate to see the lines here.
        </div>
      )}
    </div>
  )
}
