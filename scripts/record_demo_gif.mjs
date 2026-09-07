/**
 * Record the login-free demo walkthrough to docs/screenshots/clipder-demo.gif
 *
 *   1. Start the frontend:  cd frontend && npm run dev
 *   2. node scripts/record_demo_gif.mjs
 *
 * Playwright is installed to ~/.cache/clipder-playwright (not a repo dep).
 * GIF encode uses a full ffmpeg via `uv run --with imageio-ffmpeg`.
 *
 * Uses Chrome DevTools screencast (JPEG q=96, sRGB) instead of Playwright
 * webm. VP8 is 4:2:0 and washes Clipder's purple/pink UI plus clip thumbs.
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

const CURSOR_CSS = `
#clipder-demo-cursor {
  position: fixed;
  left: 48%;
  top: 52%;
  width: 22px;
  height: 22px;
  border: 2.5px solid #fff;
  border-radius: 14px 14px 14px 3px;
  background: linear-gradient(135deg, #f5d0fe, #8b5cf6);
  box-shadow: 0 6px 16px rgba(0,0,0,0.5), 0 0 0 3px rgba(139,92,246,0.28);
  z-index: 2147483647;
  pointer-events: none;
  transition: left 0.8s cubic-bezier(0.22, 1, 0.36, 1),
              top 0.8s cubic-bezier(0.22, 1, 0.36, 1),
              transform 0.14s ease;
  transform: translate(-3px, -3px) rotate(-18deg);
}
#clipder-demo-cursor.is-click {
  transform: translate(-3px, -3px) rotate(-18deg) scale(0.78);
}
`;

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

function densify(frames, fps) {
  if (frames.length === 0) return [];
  const step = 1 / fps;
  const out = [];
  const start = frames[0].t;
  const end = frames[frames.length - 1].t;
  let i = 0;
  for (let t = start; t <= end + 1e-6; t += step) {
    while (i + 1 < frames.length && frames[i + 1].t <= t) i += 1;
    out.push(frames[i]);
  }
  const hold = Math.round(fps * 2.2);
  for (let k = 0; k < hold; k += 1) out.push(frames[frames.length - 1]);
  return out;
}

async function installCursor(page) {
  await page.addStyleTag({ content: CURSOR_CSS });
  await page.evaluate(() => {
    const el = document.createElement('div');
    el.id = 'clipder-demo-cursor';
    document.body.appendChild(el);
  });
}

async function moveCursorTo(page, locator, ms = 800) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('target has no bounding box');
  const x = Math.round(box.x + box.width / 2);
  const y = Math.round(box.y + box.height / 2);
  await page.evaluate(
    ({ x, y, ms }) => {
      const el = document.getElementById('clipder-demo-cursor');
      if (!el) return;
      el.style.transitionDuration = `${ms}ms`;
      el.style.left = `${x}px`;
      el.style.top = `${y}px`;
    },
    { x, y, ms },
  );
  await sleep(ms + 100);
}

async function clickWithCursor(page, locator) {
  await page.evaluate(() => {
    document.getElementById('clipder-demo-cursor')?.classList.add('is-click');
  });
  await sleep(140);
  await locator.click();
  await sleep(120);
  await page.evaluate(() => {
    document.getElementById('clipder-demo-cursor')?.classList.remove('is-click');
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
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 2,
    colorScheme: 'dark',
  });
  const page = await context.newPage();
  await page.emulateMedia({ colorScheme: 'dark' });

  await page.goto(`${BASE}/?demo=1`, { waitUntil: 'load' });
  await page.getByText('Clip for Anna').waitFor({ timeout: 15000 });
  await waitForHdThumbnails(page);
  await installCursor(page);
  await sleep(250);

  const likeBtn = page.getByTestId('btn-like');
  const playgroundTab = page.getByTestId('nav-playground');

  const raw = [];
  const session = await context.newCDPSession(page);
  session.on('Page.screencastFrame', async ({ data, sessionId, metadata }) => {
    raw.push({ t: metadata.timestamp, buf: Buffer.from(data, 'base64') });
    try {
      await session.send('Page.screencastFrameAck', { sessionId });
    } catch {
      /* session closed */
    }
  });
  await session.send('Page.startScreencast', {
    format: 'jpeg',
    quality: 100,
    maxWidth: WIDTH * 2,
    maxHeight: HEIGHT * 2,
    everyNthFrame: 1,
  });

  // 1. Let people read the first swipe card
  await sleep(2600);

  // 2. First like
  await moveCursorTo(page, likeBtn, 900);
  await likeBtn.hover();
  await sleep(700);
  await clickWithCursor(page, likeBtn);
  await page.getByText('Emperor failed charisma check').waitFor({ timeout: 10000 });
  await waitForHdThumbnails(page);
  await sleep(2200);

  // 3. Second like — Playground waits until this one so both swipes are visible
  await sleep(400);
  await clickWithCursor(page, likeBtn);
  await page.getByText('Stax + Zest INSTANT 2v4 vs FPX').waitFor({ timeout: 10000 });
  await waitForHdThumbnails(page);
  await sleep(1800);

  // 4. Open Playground and show the queued clips
  await moveCursorTo(page, playgroundTab, 850);
  await sleep(400);
  await clickWithCursor(page, playgroundTab);
  await page.getByRole('heading', { name: 'Your queue' }).waitFor({ timeout: 10000 });
  await page.getByText('Emperor failed charisma check').waitFor({ timeout: 10000 });
  await page.getByText('Clip for Anna').waitFor({ timeout: 10000 });
  await sleep(2600);

  // 5. Analyze and leave the transcript on screen
  const analyzeBtn = page.getByRole('button', { name: 'Analyze' }).first();
  const uploadBtn = page.getByRole('button', { name: /Upload YouTube Shorts/ }).first();
  await moveCursorTo(page, analyzeBtn, 700);
  await sleep(400);
  await clickWithCursor(page, analyzeBtn);
  await page.getByText('Transcript ready').waitFor({ timeout: 10000 });
  await sleep(2800);

  // 6. Queue YouTube Shorts + TikTok and hold the success state
  await moveCursorTo(page, uploadBtn, 650);
  await sleep(400);
  await clickWithCursor(page, uploadBtn);
  await page.getByText('Queued for YouTube Shorts + TikTok.').waitFor({ timeout: 10000 });
  await sleep(2800);

  await session.send('Page.stopScreencast');
  await sleep(80);
  await browser.close();

  const span = raw.length ? raw[raw.length - 1].t - raw[0].t : 0;
  const frames = densify(raw, FPS);
  if (frames.length < 16) {
    throw new Error(`too few frames: raw=${raw.length} span=${span.toFixed(3)}s picked=${frames.length}`);
  }
  await Promise.all(
    frames.map((frame, i) =>
      writeFile(path.join(FRAME_DIR, `${String(i).padStart(4, '0')}.jpg`), frame.buf),
    ),
  );

  const ffmpeg = findFfmpeg();
  const palette = path.join(FRAME_DIR, '_palette.png');
  const seq = path.join(FRAME_DIR, '%04d.jpg');
  const vf = `scale=${WIDTH}:${HEIGHT}:flags=lanczos,setsar=1,unsharp=3:3:0.6:3:3:0.0`;

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
      `${vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle`,
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
  console.log(
    OUT_GIF,
    'bytes',
    info.size,
    'raw',
    raw.length,
    'span',
    `${span.toFixed(2)}s`,
    'frames',
    frames.length,
    'fps',
    FPS,
    `${WIDTH}x${HEIGHT}`,
  );
  await rm(FRAME_DIR, { recursive: true, force: true });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
