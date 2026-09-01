import { useState } from 'react'

/** A card whose head is always visible and whose body is one click away. */
export default function Expandable({ title, subtitle, badges, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={`exp${open ? ' open' : ''}`}>
      <button className="exp-head" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="caret">▶</span>
        <span className="title">{title}</span>
        {subtitle ? <span className="sub">{subtitle}</span> : null}
        <span className="spacer" />
        {badges}
      </button>
      {open ? <div className="exp-body">{children}</div> : null}
    </div>
  )
}
