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
import { mkdir, rm, writeFile, stat, readFile } from 'node:fs/promises';
import { existsSync, mkdirSync } from 'node:fs';
import { spawnSync, execSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
// Per-run directory: two recorders running at once must not delete each other's frames.
const FRAME_DIR = path.join(ROOT, 'docs', 'screenshots', `_frames-${process.pid}`);
const OUT_GIF = path.join(ROOT, 'docs', 'screenshots', 'clipder-demo.gif');
const BASE = process.env.CLIPDER_DEMO_URL || 'http://localhost:3000';
/** Capture size — kept at desktop width so the app renders its full three-column layout. */
const WIDTH = 1280;
const HEIGHT = 720;
/**
 * Encode size — GitHub renders README images at ~890px wide, so encoding at 896 avoids
 * paying for pixels the browser would only throw away again.
 */
const OUT_WIDTH = 896;
const OUT_HEIGHT = 504;
const FPS = 25;
/** Playback speed multiplier applied when resampling the capture. See `densify`. */
const SPEED = 1.35;
const PLAYWRIGHT_CACHE = path.join(os.homedir(), '.cache', 'clipder-playwright');
/** Downloaded demo clip MP4s, cached across runs (signed source URLs expire within a day). */
const VIDEO_CACHE = path.join(os.homedir(), '.cache', 'clipder-demo-videos');
/** Same-origin path so the demo canvas can copy video frames without tainting. */
const VIDEO_PATH = '/__clipder_demo';

/**
 * macOS arrow shape (straight left edge, notch, trailing tail). Filled white rather than
 * the system black so it stays readable on Clipder's near-black UI. The path's tip sits at
 * the element's origin, so `left`/`top` can be set straight from clientX/clientY.
 */
const MAC_ARROW_SVG =
  "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 23'>" +
  "<path d='M1.4 1.3 L1.4 19.7 L6.3 14.9 L9.5 21.6 L12.4 20.2 L9.2 13.7 L15 13.7 Z' " +
  "fill='%23ffffff' stroke='%23111111' stroke-width='1.2' stroke-linejoin='round'/></svg>";

/**
 * The pointer is a real Chromium mouse; these elements only mirror it so viewers can
 * see where the input is happening. They are driven by mouse events, never animated,
 * so the drawn cursor and the app's hover/drag state can never drift apart.
 */
const CURSOR_CSS = `
#clipder-demo-cursor {
  position: fixed;
  left: 50%;
  top: 55%;
  width: 17px;
  height: 24px;
  background: no-repeat left top / contain url("data:image/svg+xml,${MAC_ARROW_SVG}");
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.6));
  transform: translate(-1px, -1px);
  z-index: 2147483647;
  pointer-events: none;
}
/* Press feedback: a ring around the hotspot, so the arrow itself never distorts. */
#clipder-demo-cursor-ring {
  position: fixed;
  left: 50%;
  top: 55%;
  width: 34px;
  height: 34px;
  margin: -17px 0 0 -17px;
  border: 3px solid rgba(249, 138, 197, 1);
  border-radius: 50%;
  box-shadow: 0 0 16px rgba(236, 72, 153, 0.7);
  opacity: 0;
  transform: scale(0.35);
  transition: opacity 0.16s ease-out, transform 0.16s ease-out;
  z-index: 2147483646;
  pointer-events: none;
}
#clipder-demo-cursor-ring.is-down {
  opacity: 1;
  transform: scale(1);
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

/** Clip ids listed in the frontend demo module, so the two never drift apart. */
async function readDemoClipIds() {
  const src = await readFile(path.join(ROOT, 'frontend', 'src', 'demo', 'demoClips.ts'), 'utf8');
  const ids = [...src.matchAll(/^\s{4}id: '([^']+)',$/gm)].map((m) => m[1]);
  if (ids.length === 0) throw new Error('no demo clip ids found in demoClips.ts');
  return ids;
}

/**
 * Twitch clip MP4s live behind short-lived signed CloudFront URLs, so they cannot be committed.
 * Resolve them with yt-dlp and cache the files on disk: playing from a local file keeps the
 * recording deterministic, where streaming from the CDN could stall and look like a dropped frame.
 */
async function ensureDemoVideos(ids) {
  await mkdir(VIDEO_CACHE, { recursive: true });
  const files = {};

  for (const id of ids) {
    const dest = path.join(VIDEO_CACHE, `${id}.mp4`);
    if (existsSync(dest)) {
      files[id] = dest;
      continue;
    }
    console.log(`resolving demo video for ${id}`);
    const res = spawnSync(
      'uv',
      [
        'run',
        'yt-dlp',
        '-f',
        'best[ext=mp4][height<=720]/best[ext=mp4]/best',
        '-o',
        dest,
        `https://clips.twitch.tv/${id}`,
      ],
      { encoding: 'utf8', cwd: ROOT },
    );
    if (res.status !== 0 || !existsSync(dest)) {
      throw new Error(`yt-dlp failed for ${id}: ${res.stderr || res.stdout}`);
    }
    files[id] = dest;
  }
  return files;
}

/**
 * Serve the cached MP4s from a synthetic origin. Chromium's media stack asks for byte ranges,
 * so honour Range requests or playback never starts.
 */
async function serveDemoVideos(context, files) {
  const bodies = Object.fromEntries(
    await Promise.all(Object.entries(files).map(async ([id, f]) => [id, await readFile(f)])),
  );

  await context.route(`**${VIDEO_PATH}/*.mp4`, async (route, request) => {
    const id = path.basename(new URL(request.url()).pathname, '.mp4');
    const body = bodies[id];
    if (!body) return route.fulfill({ status: 404, body: '' });

    const range = /bytes=(\d*)-(\d*)/.exec(request.headers().range || '');
    if (!range) {
      return route.fulfill({
        status: 200,
        headers: {
          'content-type': 'video/mp4',
          'content-length': String(body.length),
          'accept-ranges': 'bytes',
          'access-control-allow-origin': '*',
        },
        body,
      });
    }

    const start = range[1] ? Number(range[1]) : 0;
    const end = range[2] ? Number(range[2]) : body.length - 1;
    const slice = body.subarray(start, end + 1);
    return route.fulfill({
      status: 206,
        headers: {
          'content-type': 'video/mp4',
          'content-length': String(slice.length),
          'content-range': `bytes ${start}-${end}/${body.length}`,
          'accept-ranges': 'bytes',
          'access-control-allow-origin': '*',
        },
      body: slice,
    });
  });
}

/** Block until the active card is actually rendering video, not still showing its poster. */
async function waitForCardPlayback(page) {
  await page.waitForFunction(
    () => {
      const v = document.querySelector('.clip-card.top-card video');
      return Boolean(
        v &&
          v.classList.contains('playing') &&
          v.readyState >= 3 &&
          !v.paused &&
          v.currentTime > 0.15,
      );
    },
    undefined,
    { timeout: 25000 },
  );
  const started = await page.evaluate(
    () => document.querySelector('.clip-card.top-card video')?.currentTime ?? 0,
  );
  await page.waitForFunction(
    (t0) => {
      const v = document.querySelector('.clip-card.top-card video');
      return Boolean(v && !v.paused && v.currentTime > t0 + 0.4);
    },
    started,
    { timeout: 10000 },
  );
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

/**
 * Resample the screencast onto a fixed grid and play it back at SPEED.
 * Native timing left sparse captures looking stuck; densify keeps motion regular.
 */
function densify(frames, fps, speed = SPEED) {
  if (frames.length === 0) return [];
  const step = speed / fps;
  const out = [];
  const start = frames[0].t;
  const end = frames[frames.length - 1].t;
  let i = 0;
  for (let t = start; t <= end + 1e-6; t += step) {
    while (i + 1 < frames.length && frames[i + 1].t <= t) i += 1;
    out.push(frames[i]);
  }
  const hold = Math.round(fps * 1.0);
  for (let k = 0; k < hold; k += 1) out.push(frames[frames.length - 1]);
  return out;
}

async function installCursor(page) {
  await page.addStyleTag({ content: CURSOR_CSS });
  await page.evaluate(() => {
    const el = document.createElement('div');
    el.id = 'clipder-demo-cursor';
    const ring = document.createElement('div');
    ring.id = 'clipder-demo-cursor-ring';
    document.body.append(ring, el);
    const opts = { capture: true, passive: true };
    window.addEventListener(
      'mousemove',
      (e) => {
        el.style.left = `${e.clientX}px`;
        el.style.top = `${e.clientY}px`;
        ring.style.left = `${e.clientX}px`;
        ring.style.top = `${e.clientY}px`;
      },
      opts,
    );
    window.addEventListener('mousedown', () => ring.classList.add('is-down'), opts);
    window.addEventListener('mouseup', () => ring.classList.remove('is-down'), opts);
  });
}

/**
 * Last known pointer position, so every move starts where the previous one ended. Starts clear
 * of the card so the opening frames show the feed at rest, not its hover controls.
 */
let pointer = { x: WIDTH * 0.76, y: HEIGHT * 0.82 };

const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

/** Move the real mouse along an eased path at ~40Hz so the recording captures the travel. */
async function glideTo(page, x, y, ms = 700) {
  const from = pointer;
  const steps = Math.max(2, Math.round(ms / 25));
  for (let i = 1; i <= steps; i += 1) {
    const e = easeInOut(i / steps);
    await page.mouse.move(from.x + (x - from.x) * e, from.y + (y - from.y) * e);
    await sleep(ms / steps);
  }
  pointer = { x, y };
}

async function centerOf(locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('target has no bounding box');
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

async function glideToLocator(page, locator, ms = 700) {
  const { x, y } = await centerOf(locator);
  await glideTo(page, x, y, ms);
}

async function clickHere(page) {
  await page.mouse.down();
  await sleep(110);
  await page.mouse.up();
  await sleep(110);
}

/**
 * Press, pull far enough for LIKE/NOPE to read, then flick. The extra samples are
 * what make the card track the cursor in the GIF instead of teleporting.
 */
async function dragSwipe(page, direction = 'right') {
  const card = page.locator('#card-stack .clip-card.top-card');
  const box = await card.boundingBox();
  if (!box) throw new Error('no top card to swipe');

  const grabX = box.x + box.width / 2;
  const grabY = box.y + box.height * 0.42;
  await glideTo(page, grabX, grabY, 480);
  await sleep(140);

  await page.mouse.down();
  await sleep(80);

  const sign = direction === 'right' ? 1 : -1;
  const pull = sign * Math.max(64, box.width * 0.22);
  const flick = sign * box.width * 0.7;

  const pullSteps = 11;
  for (let i = 1; i <= pullSteps; i += 1) {
    const t = i / pullSteps;
    const x = grabX + pull * t;
    const y = grabY - 8 * t;
    await page.mouse.move(x, y);
    pointer = { x, y };
    await sleep(26);
  }
  await sleep(70);

  const flickSteps = 14;
  for (let i = 1; i <= flickSteps; i += 1) {
    const t = i / flickSteps;
    const eased = t * t;
    const x = grabX + pull + (flick - pull) * eased;
    const y = grabY - 8 - 20 * Math.sin(Math.PI * t);
    await page.mouse.move(x, y);
    pointer = { x, y };
    await sleep(16);
  }

  await sleep(40);
  await page.mouse.up();
  await sleep(460);
}

async function main() {
  await waitForServer(BASE);
  await rm(FRAME_DIR, { recursive: true, force: true });
  await mkdir(FRAME_DIR, { recursive: true });

  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--force-color-profile=srgb',
      '--disable-lcd-text',
      '--hide-scrollbars',
      // Gesture-free muted playback, and software decode so CDP screencast sees video frames
      // instead of a compositor hole where the GPU overlay sat.
      '--autoplay-policy=no-user-gesture-required',
      '--disable-accelerated-video-decode',
      '--disable-accelerated-video-encode',
      '--use-gl=angle',
      '--use-angle=swiftshader',
    ],
  });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
    colorScheme: 'dark',
  });
  const demoIds = await readDemoClipIds();
  const videoFiles = await ensureDemoVideos(demoIds);
  await serveDemoVideos(context, videoFiles);

  const page = await context.newPage();
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.addInitScript(
    (map) => {
      window.__clipderDemoVideos = map;
    },
    Object.fromEntries(demoIds.map((id) => [id, `${VIDEO_PATH}/${id}.mp4`])),
  );

  await page.goto(`${BASE}/?demo=1`, { waitUntil: 'load' });
  await page.getByText('Clip for Anna').waitFor({ timeout: 15000 });
  await waitForHdThumbnails(page);
  await waitForCardPlayback(page);
  await installCursor(page);
  await page.mouse.move(pointer.x, pointer.y);
  await sleep(250);

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
    quality: 55,
    maxWidth: WIDTH,
    maxHeight: HEIGHT,
    everyNthFrame: 1,
  });

  // 1. Let people read the first swipe card
  await sleep(900);

  // 2. Swipe the first clip right by dragging it off the stack
  await dragSwipe(page, 'right');
  await page.getByText('holy aim').waitFor({ timeout: 10000 });
  await waitForHdThumbnails(page);
  await waitForCardPlayback(page);
  await sleep(700);

  // 3. Second swipe — Playground waits until this one so both clips are in the queue
  await dragSwipe(page, 'right');
  await page.getByText('Stax + Zest INSTANT 2v4 vs FPX').waitFor({ timeout: 10000 });
  await waitForHdThumbnails(page);
  await waitForCardPlayback(page);
  await sleep(550);

  // 4. Open Playground and show the queued clips as a list
  await glideToLocator(page, playgroundTab, 560);
  await sleep(160);
  await clickHere(page);
  await page.getByRole('heading', { name: 'Your queue' }).waitFor({ timeout: 10000 });
  await page.getByText('holy aim').waitFor({ timeout: 10000 });
  await page.getByText('Clip for Anna').waitFor({ timeout: 10000 });
  await sleep(1100);

  // 5. Analyze and leave the transcript on screen
  const analyzeBtn = page.getByRole('button', { name: 'Analyze' }).first();
  const uploadBtn = page.getByRole('button', { name: /Upload Shorts/ }).first();
  await glideToLocator(page, analyzeBtn, 480);
  await sleep(160);
  await clickHere(page);
  await page.getByText('Transcript ready').waitFor({ timeout: 10000 });
  await sleep(1300);

  // 6. Queue YouTube Shorts + TikTok and hold the success state
  await uploadBtn.scrollIntoViewIfNeeded();
  await glideToLocator(page, uploadBtn, 420);
  await sleep(160);
  await uploadBtn.click();
  await page.getByText('Queued for YouTube Shorts + TikTok.').waitFor({ timeout: 10000 });
  await sleep(1400);

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
  const vf = `scale=${OUT_WIDTH}:${OUT_HEIGHT}:flags=lanczos,setsar=1,unsharp=3:3:0.5:3:3:0.0`;

  const gen = spawnSync(
    ffmpeg,
    [
      '-y',
      '-framerate',
      String(FPS),
      '-i',
      seq,
      '-vf',
      `${vf},palettegen=max_colors=192:reserve_transparent=0:stats_mode=diff`,
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
    `speed=${SPEED}`,
    `${OUT_WIDTH}x${OUT_HEIGHT}`,
  );
  // CLIPDER_KEEP_FRAMES=1 leaves the JPEGs in place for re-encoding experiments.
  if (process.env.CLIPDER_KEEP_FRAMES !== '1') {
    await rm(FRAME_DIR, { recursive: true, force: true });
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
