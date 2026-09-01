import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `base: './'` so a production build opens from the filesystem or from any
// subdirectory, not only from a server root. The dashboard is something a
// supervisor should be able to open by double-clicking `dist/index.html`.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { port: 5173, open: true },
})
