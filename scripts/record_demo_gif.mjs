/**
 * Record the login-free demo walkthrough to docs/screenshots/clipder-demo.gif
 *
 *   1. Start the frontend:  cd frontend && npm run dev
 *   2. node scripts/record_demo_gif.mjs
 *
 * Uses Playwright (npx) + Pillow (uv) so the repo does not take a Playwright dep.
 */
import { mkdir, writeFile, rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const FRAME_DIR = path.join(ROOT, 'docs', 'screenshots', '_frames');
const OUT_GIF = path.join(ROOT, 'docs', 'screenshots', 'clipder-demo.gif');
const BASE = process.env.CLIPDER_DEMO_URL || 'http://localhost:3000';

async function waitForServer(url, attempts = 40) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { redirect: 'manual' });
      if (res.status < 500) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Frontend not reachable at ${url}`);
}

async function main() {
  await waitForServer(BASE);
  await rm(FRAME_DIR, { recursive: true, force: true });
  await mkdir(FRAME_DIR, { recursive: true });

  // ESM ignores NODE_PATH; resolve playwright from NODE_PATH so a temp install works.
  const { chromium } = await (async () => {
    try {
      return await import('playwright');
    } catch (firstErr) {
      const dirs = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean);
      for (const dir of dirs) {
        try {
          return await import(pathToFileURL(path.join(dir, 'playwright', 'index.mjs')).href);
        } catch {
          /* try next NODE_PATH entry */
        }
      }
      throw firstErr;
    }
  })();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
  });

  let n = 0;
  const shot = async (hold = 1) => {
    const buf = await page.screenshot({ type: 'png' });
    for (let i = 0; i < hold; i++) {
      await writeFile(path.join(FRAME_DIR, `${String(n).padStart(3, '0')}.png`), buf);
      n += 1;
    }
  };

  await page.goto(`${BASE}/?demo=1`, { waitUntil: 'load' });
  await page.getByText('Clip for Anna').waitFor({ timeout: 15000 });
  await page.waitForFunction(
    () => {
      const imgs = [...document.querySelectorAll('img.clip-thumbnail')];
      return imgs.length > 0 && imgs.every((img) => img.complete && img.naturalWidth > 0);
    },
    { timeout: 12000 },
  ).catch(() => {});
  await page.waitForTimeout(400);
  await shot(4);

  await page.getByTestId('btn-like').click();
  await page.waitForTimeout(120);
  await shot(2);
  await page.waitForTimeout(200);
  await shot(2);
  await page.waitForTimeout(200);
  await shot(3);

  await page.getByTestId('nav-playground').click();
  await page.getByRole('heading', { name: 'Your queue' }).waitFor({ timeout: 10000 });
  await page.getByText('Clip for Anna').waitFor({ timeout: 10000 });
  await shot(3);

  const analyze = page.getByRole('button', { name: 'Analyze' }).first();
  await analyze.click();
  await shot(2);
  await page.getByText('Transcript ready').waitFor({ timeout: 10000 });
  await shot(4);

  const upload = page.getByRole('button', { name: /Upload YouTube Shorts/ }).first();
  await upload.click();
  await shot(2);
  await page.getByText('Queued for YouTube Shorts + TikTok.').waitFor({ timeout: 10000 });
  await shot(5);

  await browser.close();

  const py = `
from pathlib import Path
from PIL import Image

frame_dir = Path(${JSON.stringify(FRAME_DIR)})
out = Path(${JSON.stringify(OUT_GIF)})
files = sorted(frame_dir.glob("*.png"))
if not files:
    raise SystemExit("no frames")
images_rgb = []
for f in files:
    images_rgb.append(Image.open(f).convert("RGB").resize((960, 540), Image.Resampling.LANCZOS))
palette = images_rgb[0].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
images = [im.quantize(palette=palette) for im in images_rgb]
images[0].save(
    out,
    save_all=True,
    append_images=images[1:],
    duration=280,
    loop=0,
    optimize=True,
)
print(out, "bytes", out.stat().st_size)
`;
  const result = spawnSync('uv', ['run', '--with', 'pillow', 'python', '-c', py], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    console.error(result.stdout, result.stderr);
    throw new Error('GIF stitch failed');
  }
  console.log(result.stdout.trim());
  await rm(FRAME_DIR, { recursive: true, force: true });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
