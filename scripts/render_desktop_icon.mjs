// Re-export the existing vector mark using the locked developer browser tools.
import { readFile, writeFile, mkdir, mkdtemp, copyFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { chromium } from '../tests/browser/node_modules/playwright/index.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const destination = path.join(root, 'packaging/desktop');
const temporary = await mkdtemp(path.join(tmpdir(), 'opent1d-icon-'));
const iconset = path.join(temporary, 'OpenT1D.iconset');
await mkdir(iconset);
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  const svg = await readFile(path.join(destination, 'icon.svg'), 'utf8');
  const sizes = [16, 32, 64, 128, 256, 512, 1024];
  const images = new Map();
  for (const size of sizes) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent('<style>html,body{margin:0;background:transparent}svg{display:block;width:100vw;height:100vh}</style>' + svg);
    const png = await page.screenshot({ omitBackground: true });
    images.set(size, png);
    await writeFile(path.join(temporary, size + '.png'), png);
  }
  for (const size of [16, 32, 128, 256, 512]) {
    await copyFile(path.join(temporary, size + '.png'), path.join(iconset, `icon_${size}x${size}.png`));
    await copyFile(path.join(temporary, (size * 2) + '.png'), path.join(iconset, `icon_${size}x${size}@2x.png`));
  }
  execFileSync('/usr/bin/iconutil', ['-c', 'icns', '-o', path.join(destination, 'icon.icns'), iconset]);
  await writeFile(path.join(destination, 'icon.png'), images.get(256));
} finally { await browser.close(); await rm(temporary, { recursive: true }); }
