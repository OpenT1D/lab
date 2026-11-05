import { defineConfig } from '@playwright/test';
import common from './playwright.config.mjs';
import { applicationFiles, presentApplicationFiles } from './application-shards.mjs';

const present = presentApplicationFiles(new URL('.', import.meta.url));

// Balance measured long flows across isolated jobs; every file/case is retained.
export default defineConfig({
  ...common,
  testMatch: applicationFiles(common.testMatch, process.env.OPENT1D_BROWSER_SHARD, present),
  globalTimeout: 480_000,
});
