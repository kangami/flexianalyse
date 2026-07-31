// Post-build prerender: snapshot les routes publiques du SPA en HTML statique.
// Sert dist/ localement, ouvre chaque route dans Chrome headless et écrit le
// HTML rendu dans dist/<route>/index.html. Vercel sert ces fichiers avant le
// rewrite SPA → les crawlers reçoivent le vrai contenu dès le premier octet.
// En cas d'échec (Chrome indisponible…), on log et on sort en 0 : le déploiement
// SPA classique reste intact.

import { createServer } from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const ROUTES = ['/', '/pricing', '/get-started', '/schema-explorer', '/privacy-policy', '/terms-of-use'];

const MIME = {
  '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript',
  '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.ico': 'image/x-icon', '.txt': 'text/plain',
  '.xml': 'application/xml', '.woff2': 'font/woff2', '.mp4': 'video/mp4',
};

async function main() {
  const { default: puppeteer } = await import('puppeteer');

  const server = createServer(async (req, res) => {
    const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    let file = join(DIST, path);
    if (!extname(file) || !existsSync(file)) file = join(DIST, 'index.html');
    try {
      const body = await readFile(file);
      res.writeHead(200, { 'Content-Type': MIME[extname(file)] || 'application/octet-stream' });
      res.end(body);
    } catch {
      res.writeHead(404).end();
    }
  });
  await new Promise((r) => server.listen(0, r));
  const base = `http://localhost:${server.address().port}`;

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const snapshots = {};
  const page = await browser.newPage();
  // Les vidéos de fond sont inutiles au rendu et ralentissent le chargement.
  await page.setRequestInterception(true);
  page.on('request', (req) => (req.url().endsWith('.mp4') ? req.abort() : req.continue()));

  for (const route of ROUTES) {
    await page.goto(base + route, { waitUntil: 'load', timeout: 60000 });
    // Attend la fin du check auth Firebase (spinner) et le rendu du contenu réel.
    await page.waitForSelector('h1, h2', { timeout: 30000 }).catch(() => {
      console.warn(`[prerender] ${route}: pas de h1/h2 après 30s, snapshot quand même`);
    });
    await new Promise((r) => setTimeout(r, 1000));
    snapshots[route] = '<!doctype html>' + (await page.evaluate(() => document.documentElement.outerHTML));
    console.log(`[prerender] ${route} ok (${Math.round(snapshots[route].length / 1024)} kB)`);
  }

  await browser.close();
  server.close();

  for (const [route, html] of Object.entries(snapshots)) {
    const out = route === '/' ? join(DIST, 'index.html') : join(DIST, route.slice(1), 'index.html');
    await mkdir(dirname(out), { recursive: true });
    await writeFile(out, html);
  }
  console.log(`[prerender] ${ROUTES.length} routes écrites dans dist/`);
}

main().catch((err) => {
  console.warn('[prerender] échec, déploiement SPA sans prerender :', err.message);
  process.exit(0);
});
