#!/usr/bin/env node
/**
 * Fold the production build into one self-contained HTML file.
 *
 * `npm run build` emits an external `<script type="module">` and an external
 * stylesheet. Opened over `file://`, Chrome refuses both: a document loaded
 * from a file has the opaque origin `null`, and cross-origin module and
 * stylesheet loads from that origin are blocked outright. The page then renders
 * nothing, with a CORS error that looks alarming and means only "this needs a
 * server".
 *
 * Inlining removes the fetches rather than working around the rule. An inline
 * module executes from `file://` because nothing is fetched, and the data goes
 * in the same way: `fetch()` on a `file://` URL is blocked by the same policy,
 * so the dashboard JSON is embedded as `window.__AAM4J_DATA__` and the data
 * layer prefers it when present.
 *
 * The result is one file, around 800 KB, that opens by double-click on any
 * machine with a browser and no toolchain at all. That is the form to hand a
 * supervisor or attach to an email.
 */

import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const dist = resolve(here, process.argv[2] || 'dist')
const outDir = resolve(here, process.argv[3] || 'dist-standalone')
const dataPath = resolve(here, 'public', 'dashboard.json')

/** `</script>` inside a JS string would end the inline block early. */
const guard = (text) => text.replaceAll('</script', '<\\/script')

const html = readFileSync(join(dist, 'index.html'), 'utf8')
const assets = readdirSync(join(dist, 'assets'))
const cssName = assets.find((name) => name.endsWith('.css'))
const jsName = assets.find((name) => name.endsWith('.js'))
if (!cssName || !jsName) {
  console.error(`no built assets in ${dist}. Run \`npm run build\` first.`)
  process.exit(1)
}

const css = readFileSync(join(dist, 'assets', cssName), 'utf8')
const js = readFileSync(join(dist, 'assets', jsName), 'utf8')

let data
try {
  data = readFileSync(dataPath, 'utf8')
} catch {
  console.error(
    'public/dashboard.json is missing. Run `python build_dashboard_data.py` first:\n' +
      'a standalone file with no data in it would be worse than no file.',
  )
  process.exit(1)
}
// Embed as a string parsed at runtime rather than as an object literal: JSON.parse
// on a 500 KB payload is measurably faster than having the JS engine parse the
// same bytes as source, and it keeps the escaping to one well-defined rule.
const embedded = JSON.stringify(data).replaceAll('<', '\\u003c')

// Every replacement is a function, never a string. A string replacement runs
// `$&`, `$'` and friends as substitution patterns, and minified JavaScript is
// full of those sequences: passing the bundle as a string silently corrupts it
// and leaves the original external <script> in place. This cost one debugging
// round; the comment is here so it does not cost a second.
const out = html
  .replace(/<link[^>]+rel="stylesheet"[^>]*>/, () => `<style>\n${css}\n</style>`)
  .replace(
    /<script type="module"[^>]*?><\/script>/,
    () =>
      `<script>window.__AAM4J_DATA__ = JSON.parse(${embedded});</script>\n` +
      `<script type="module">\n${guard(js)}\n</script>`,
  )

// Check for a surviving *tag*, not for a string. The bundle itself contains
// `rel="stylesheet"` inside Vite's preload helper, so a substring check reports
// a failure that is not there.
for (const [what, pattern] of [
  ['stylesheet', /<link[^>]+rel="stylesheet"[^>]+href=/],
  ['module script', /<script[^>]+type="module"[^>]+src=/],
]) {
  if (pattern.test(out)) {
    console.error(`the ${what} was not inlined: the page would still need a server.`)
    process.exit(1)
  }
}

mkdirSync(outDir, { recursive: true })
const target = join(outDir, 'aam4j-dashboard.html')
writeFileSync(target, out)

const kb = (n) => `${Math.round(n / 1024)} KB`
console.log(`inlined  ${cssName}  ${kb(css.length)}`)
console.log(`inlined  ${jsName}  ${kb(js.length)}`)
console.log(`inlined  dashboard.json  ${kb(data.length)}`)
console.log(`\nwrote    ${target}  ${kb(out.length)}`)
console.log('Opens by double-click. No server, no toolchain.')
