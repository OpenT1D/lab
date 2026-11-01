import { defineConfig } from '@playwright/test';
import common from './playwright.config.mjs';

// Every case owns its app/workspace. Enable Playwright's case-level sharding;
// each isolated CI job still runs exactly one worker and never retries.
export default defineConfig({ ...common, fullyParallel: true });
