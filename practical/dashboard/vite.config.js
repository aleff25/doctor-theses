import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `base: './'` so a production build can be served from any subdirectory, not
// only from a server root.
//
// It does NOT make `dist/index.html` openable by double-click: a page loaded
// over `file://` has the opaque origin `null`, and Chrome blocks the external
// module script, the stylesheet and the `fetch()` of the data from there. Use
// `npm run preview` for a local server, or `npm run standalone` for a single
// self-contained file that genuinely does open by double-click.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { port: 5173, open: true },
})
