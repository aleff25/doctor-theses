import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const DataContext = createContext(null)

/**
 * The dashboard reads one file, `public/dashboard.json`, produced by
 * `dashboard/build_dashboard_data.py`. It is fetched rather than imported so a
 * missing file is a message the user can act on instead of a build failure:
 * the generator needs the pipeline to have run first, and telling someone that
 * is more useful than a stack trace.
 */
export function DataProvider({ children }) {
  const [state, setState] = useState({ status: 'loading' })

  useEffect(() => {
    // The standalone single-file build embeds the payload, because `fetch()` on
    // a `file://` URL is blocked by the same origin policy that blocks module
    // and stylesheet loads there. When it is present there is nothing to fetch.
    if (typeof window !== 'undefined' && window.__AAM4J_DATA__) {
      setState({ status: 'ready', data: window.__AAM4J_DATA__ })
      return undefined
    }

    let cancelled = false
    fetch(`${import.meta.env.BASE_URL}dashboard.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
        return response.json()
      })
      .then((data) => !cancelled && setState({ status: 'ready', data }))
      .catch((error) => !cancelled && setState({ status: 'error', error: String(error) }))
    return () => {
      cancelled = true
    }
  }, [])

  const value = useMemo(() => {
    if (state.status !== 'ready') return state
    const { data } = state
    const byId = Object.fromEntries(data.catalogue.metrics.map((m) => [m.id, m]))
    const refs = data.references
    return { ...state, metricById: byId, refs }
  }, [state])

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

export function useData() {
  const context = useContext(DataContext)
  if (!context) throw new Error('useData must be used inside a DataProvider')
  return context
}

/** Metric values are counts and ratios; neither wants six decimal places. */
export function formatValue(value) {
  if (value === null || value === undefined) return 'n/d'
  if (Number.isInteger(value)) return String(value)
  return String(Number(value.toFixed(3)))
}
