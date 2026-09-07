/**
 * Record the login-free demo walkthrough to docs/screenshots/clipder-demo.gif
 *
 *   1. Start the frontend:  cd frontend && npm run dev
 *   2. node scripts/record_demo_gif.mjs
 *
 * Playwright is installed to ~/.cache/clipder-playwright (not a repo dep).
 * GIF encode uses a full ffmpeg via `uv run --with imageio-ffmpeg`.
 *
 * Frames are lossless PNG (sRGB) so purple/pink UI and clip thumbnails keep
 * their color. Playwright's webm path is VP8 yuv420 and washes the palette.
 */
import { mkdir, rm, writeFile, stat } from 'node:fs/promises';
import { existsSync, mkdirSync } from 'node:fs';
import { spawnSync, execSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const FRAME_DIR = path.join(ROOT, 'docs', 'screenshots', '_frames');
const OUT_GIF = path.join(ROOT, 'docs', 'screenshots', 'clipder-demo.gif');
const BASE = process.env.CLIPDER_DEMO_URL || 'http://localhost:3000';
const WIDTH = 1280;
const HEIGHT = 720;
const FPS = 16;
const PLAYWRIGHT_CACHE = path.join(os.homedir(), '.cache', 'clipder-playwright');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitForServer(url, attempts = 40) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { redirect: 'manual' });
      if (res.status < 500) return;
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error(`Frontend not reachable at ${url}`);
}

function ensurePlaywrightInstalled() {
  const marker = path.join(PLAYWRIGHT_CACHE, 'node_modules', 'playwright', 'package.json');
  if (existsSync(marker)) return;
  mkdirSync(PLAYWRIGHT_CACHE, { recursive: true });
  execSync('npm install --no-save --no-package-lock playwright', {
    cwd: PLAYWRIGHT_CACHE,
    stdio: 'inherit',
  });
}

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    /* fall through */
  }
  const dirs = [
    ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean),
    path.join(PLAYWRIGHT_CACHE, 'node_modules'),
  ];
  for (const dir of dirs) {
    try {
      return await import(pathToFileURL(path.join(dir, 'playwright', 'index.mjs')).href);
    } catch {
      /* try next */
    }
  }
  ensurePlaywrightInstalled();
  return await import(
    pathToFileURL(path.join(PLAYWRIGHT_CACHE, 'node_modules', 'playwright', 'index.mjs')).href
  );
}

function findFfmpeg() {
  const envBin = process.env.FFMPEG;
  if (envBin && existsSync(envBin)) return envBin;

  const which = spawnSync('which', ['ffmpeg'], { encoding: 'utf8' });
  if (which.status === 0 && which.stdout.trim()) return which.stdout.trim();

  const py = spawnSync(
    'uv',
    [
      'run',
      '--with',
      'imageio-ffmpeg',
      'python',
      '-c',
      'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())',
    ],
    { encoding: 'utf8', cwd: ROOT },
  );
  if (py.status === 0 && py.stdout.trim()) return py.stdout.trim();

  throw new Error(`ffmpeg not found: ${py.stderr || py.stdout}`);
}

async function waitForHdThumbnails(page, minWidth = 1280) {
  await page.waitForFunction(
    (min) => {
      const imgs = [...document.querySelectorAll('img.clip-thumbnail')];
      return imgs.length > 0 && imgs.every((img) => img.complete && img.naturalWidth >= min);
    },
    minWidth,
    { timeout: 20000 },
  );
  await page.evaluate(async () => {
    await (document.fonts?.ready ?? Promise.resolve());
    const urls = [...document.querySelectorAll('img.clip-thumbnail, .blur-bg-container img')]
      .map((img) => img.src)
      .filter(Boolean);
    await Promise.all(
      urls.map(
        (src) =>
          new Promise((resolve) => {
            const probe = new Image();
            probe.onload = resolve;
            probe.onerror = resolve;
            probe.src = src;
          }),
      ),
    );
  });
}

async function main() {
  await waitForServer(BASE);
  await rm(FRAME_DIR, { recursive: true, force: true });
  await mkdir(FRAME_DIR, { recursive: true });

  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({
    headless: true,
    args: ['--force-color-profile=srgb', '--disable-lcd-text', '--hide-scrollbars'],
  });
  const page = await browser.newPage({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 2,
    colorScheme: 'dark',
  });
  await page.emulateMedia({ colorScheme: 'dark' });

  let n = 0;
  const shot = async () => {
    const buf = await page.screenshot({ type: 'png', animations: 'allow' });
    await writeFile(path.join(FRAME_DIR, `${String(n).padStart(4, '0')}.png`), buf);
    n += 1;
  };

  const burst = async (ms) => {
    const interval = 1000 / FPS;
    const end = Date.now() + ms;
    while (Date.now() < end) {
      const t = Date.now();
      await shot();
      const wait = interval - (Date.now() - t);
      if (wait > 0) await sleep(wait);
    }
  };

  await page.goto(`${BASE}/?demo=1`, { waitUntil: 'networkidle' });
  await page.getByText('Clip for Anna').waitFor({ timeout: 15000 });
  await waitForHdThumbnails(page);
  await sleep(250);
  await burst(1100);

  await page.getByTestId('btn-like').hover();
  await burst(280);
  await page.getByTestId('btn-like').click();
  await burst(700);

  await page.getByTestId('nav-playground').click();
  await page.getByRole('heading', { name: 'Your queue' }).waitFor({ timeout: 10000 });
  await page.getByText('Clip for Anna').waitFor({ timeout: 10000 });
  await burst(1000);

  await page.getByRole('button', { name: 'Analyze' }).first().click();
  await burst(400);
  await page.getByText('Transcript ready').waitFor({ timeout: 10000 });
  await burst(1300);

  await page.getByRole('button', { name: /Upload YouTube Shorts/ }).first().click();
  await burst(400);
  await page.getByText('Queued for YouTube Shorts + TikTok.').waitFor({ timeout: 10000 });
  await burst(1500);

  await browser.close();
  if (n < 8) throw new Error(`too few frames: ${n}`);

  const ffmpeg = findFfmpeg();
  const palette = path.join(FRAME_DIR, '_palette.png');
  const seq = path.join(FRAME_DIR, '%04d.png');
  const vf = `scale=${WIDTH}:${HEIGHT}:flags=lanczos,setsar=1`;

  const gen = spawnSync(
    ffmpeg,
    [
      '-y',
      '-framerate',
      String(FPS),
      '-i',
      seq,
      '-vf',
      `${vf},palettegen=max_colors=256:reserve_transparent=0:stats_mode=full`,
      palette,
    ],
    { encoding: 'utf8' },
  );
  if (gen.status !== 0) {
    console.error(gen.stdout, gen.stderr);
    throw new Error('palettegen failed');
  }

  const use = spawnSync(
    ffmpeg,
    [
      '-y',
      '-framerate',
      String(FPS),
      '-i',
      seq,
      '-i',
      palette,
      '-lavfi',
      `${vf}[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle`,
      '-loop',
      '0',
      OUT_GIF,
    ],
    { encoding: 'utf8' },
  );
  if (use.status !== 0) {
    console.error(use.stdout, use.stderr);
    throw new Error('paletteuse failed');
  }

  const info = await stat(OUT_GIF);
  console.log(OUT_GIF, 'bytes', info.size, 'frames', n, 'fps', FPS, `${WIDTH}x${HEIGHT}`);
  await rm(FRAME_DIR, { recursive: true, force: true });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
