import { createContext, useCallback, useContext, useState } from 'react'

const TooltipContext = createContext(null)

/**
 * One fixed-position tooltip for the whole page.
 *
 * A CSS-only tooltip nested inside the element that triggers it gets clipped by
 * any ancestor with `overflow: hidden`, which every expandable card here has.
 * Rendering a single tooltip at the root and positioning it from the trigger's
 * bounding box avoids that entirely, and keeps one node in the DOM instead of
 * one per badge (there are several hundred badges on the Systems view).
 */
export function TooltipProvider({ children }) {
  const [tip, setTip] = useState(null)

  const show = useCallback((element, content) => {
    const rect = element.getBoundingClientRect()
    setTip({ content, rect })
  }, [])

  const hide = useCallback(() => setTip(null), [])

  return (
    <TooltipContext.Provider value={{ show, hide }}>
      {children}
      {tip ? <TooltipLayer tip={tip} /> : null}
    </TooltipContext.Provider>
  )
}

function TooltipLayer({ tip }) {
  const width = 380
  const margin = 12
  const left = Math.min(
    Math.max(margin, tip.rect.left),
    Math.max(margin, window.innerWidth - width - margin),
  )
  // Prefer above the trigger; flip below when there is not enough room, so a
  // badge near the top of the viewport does not open a tooltip off-screen.
  const above = tip.rect.top > 260
  const style = above
    ? { left, bottom: window.innerHeight - tip.rect.top + 8, width }
    : { left, top: tip.rect.bottom + 8, width }

  return (
    <div className="tooltip" style={style} role="tooltip">
      {tip.content}
    </div>
  )
}

export function useTooltip() {
  const context = useContext(TooltipContext)
  if (!context) throw new Error('useTooltip must be used inside a TooltipProvider')
  return context
}
