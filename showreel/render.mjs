// Renders reel.html frame by frame in headless Chromium, in parallel.
//   node render.mjs --out frames [--workers 4] [--frames 0-899 | 10,200,450] [--sub 6]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const { chromium } = await import('playwright').catch(() => import('/opt/node-tools/node_modules/playwright/index.mjs'));
const here = path.dirname(fileURLToPath(import.meta.url));
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const out = path.resolve(arg('out', 'frames'));
const workers = +arg('workers', 4);
const sub = +arg('sub', 6);
const spec = arg('frames', '0-899');
const frames = spec.split(',').flatMap(s => {
  const [a, b] = s.split('-').map(Number);
  return b === undefined ? [a] : Array.from({ length: b - a + 1 }, (_, i) => a + i);
});
fs.mkdirSync(out, { recursive: true });

const url = 'file://' + path.join(here, 'reel.html') + '?sub=' + sub;
const t0 = Date.now();
let done = 0;

async function worker(w) {
  const browser = await chromium.launch({
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error(`[w${w}]`, e.message));
  await page.goto(url);
  await page.waitForFunction('window.READY === true', null, { timeout: 120000 });
  for (let i = w; i < frames.length; i += workers) {
    const f = frames[i];
    await page.evaluate(n => window.renderFrame(n), f);
    const buf = await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1920, height: 1080 } });
    fs.writeFileSync(path.join(out, `f_${String(f).padStart(4, '0')}.png`), buf);
    if (++done % 60 === 0) console.log(`${done}/${frames.length}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  await browser.close();
}
await Promise.all(Array.from({ length: Math.min(workers, frames.length) }, (_, w) => worker(w)));
console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
